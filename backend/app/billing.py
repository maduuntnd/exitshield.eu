"""ChurnGuard vendor billing: plan definitions, entitlements, and Stripe sync.

Stripe (live) is the source of truth for subscription status: a vendor's plan is a
real recurring subscription created via Checkout with a 14-day trial. Webhooks keep
`org.subscription.status` in sync. This module owns the plan catalog, price mapping,
and the usage/entitlement snapshot used to gate features.
"""
import os
from datetime import datetime, timezone, timedelta
from .db import db

TRIAL_DAYS = 14
SESSION_WINDOW_DAYS = 30

PLANS = {
    "starter": {
        "id": "starter", "name": "Starter", "price": 49.0,
        "session_limit": 250, "offer_limit": 3, "seats": 1,
        "badge_removal": False, "advanced_analytics": False,
        "custom_branding": False, "api_access": False,
        "tagline": "For indie SaaS testing the waters.",
        "features": ["Up to 250 save-sessions / mo", "3 active retention offers",
                     "Core dashboard & analytics", "1 team seat"],
    },
    "growth": {
        "id": "growth", "name": "Growth", "price": 99.0,
        "session_limit": 1500, "offer_limit": 15, "seats": 3,
        "badge_removal": True, "advanced_analytics": True,
        "custom_branding": False, "api_access": False,
        "tagline": "For scaling teams recovering real MRR.",
        "features": ["Up to 1,500 save-sessions / mo", "15 active retention offers",
                     "Advanced analytics & exports", "Remove ChurnGuard badge", "3 team seats"],
    },
    "scale": {
        "id": "scale", "name": "Scale", "price": 149.0,
        "session_limit": 10000, "offer_limit": 100, "seats": 10,
        "badge_removal": True, "advanced_analytics": True,
        "custom_branding": True, "api_access": True,
        "tagline": "For high-volume products that live on retention.",
        "features": ["Up to 10,000 save-sessions / mo", "Unlimited retention offers",
                     "Advanced analytics, exports & API", "Custom branding + white-label", "10 team seats"],
    },
}

DEFAULT_TRIAL_PLAN = "growth"

PRICE_MAP = {
    "starter": os.environ.get("STRIPE_PRICE_STARTER", ""),
    "growth": os.environ.get("STRIPE_PRICE_GROWTH", ""),
    "scale": os.environ.get("STRIPE_PRICE_SCALE", ""),
}
PLAN_BY_PRICE = {v: k for k, v in PRICE_MAP.items() if v}

# Stripe statuses that grant full product access.
ACTIVE_STATES = ("trialing", "active")


def _dt(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


def empty_subscription() -> dict:
    return {
        "plan_id": DEFAULT_TRIAL_PLAN,
        "status": None,
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "trial_ends_at": None,
        "current_period_end": None,
        "payment_method_on_file": False,
        "cancel_at_period_end": False,
    }


async def get_state(org: dict) -> dict:
    """Entitlement + usage snapshot for an organization (status driven by Stripe)."""
    sub = org.get("subscription") or empty_subscription()
    status = sub.get("status")
    plan = PLANS.get(sub.get("plan_id") or DEFAULT_TRIAL_PLAN, PLANS[DEFAULT_TRIAL_PLAN])
    org_id = org["id"]

    since = (datetime.now(timezone.utc) - timedelta(days=SESSION_WINDOW_DAYS)).isoformat()
    session_usage = await db.cancel_sessions.count_documents(
        {"org_id": org_id, "seed": {"$ne": True}, "created_at": {"$gte": since}})
    offer_usage = await db.retention_offers.count_documents({"org_id": org_id})

    over_sessions = session_usage >= plan["session_limit"]
    over_offers = offer_usage >= plan["offer_limit"]

    active_access = status in ACTIVE_STATES
    needs_subscription = status is None
    hard_limited = (not active_access) and status != "past_due"
    soft_limited = status == "past_due" or (active_access and (over_sessions or over_offers))

    trial_days_left = None
    if status == "trialing":
        te = _dt(sub.get("trial_ends_at"))
        if te:
            trial_days_left = max(0, (te - datetime.now(timezone.utc)).days)

    return {
        "subscription": sub,
        "plan": plan,
        "usage": {"sessions": session_usage, "offers": offer_usage},
        "limits": {"sessions": plan["session_limit"], "offers": plan["offer_limit"]},
        "over_sessions": over_sessions,
        "over_offers": over_offers,
        "soft_limited": soft_limited,
        "hard_limited": hard_limited,
        "needs_subscription": needs_subscription,
        "trial_days_left": trial_days_left,
    }


def subscription_from_stripe(stripe_sub) -> dict:
    """Map a Stripe Subscription object to our stored subscription dict."""
    price_id = None
    try:
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    except Exception:
        pass
    plan_id = PLAN_BY_PRICE.get(price_id, DEFAULT_TRIAL_PLAN)

    def iso(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None

    return {
        "plan_id": plan_id,
        "status": stripe_sub.get("status"),
        "stripe_customer_id": stripe_sub.get("customer"),
        "stripe_subscription_id": stripe_sub.get("id"),
        "trial_ends_at": iso(stripe_sub.get("trial_end")),
        "current_period_end": iso(stripe_sub.get("current_period_end")),
        "payment_method_on_file": True,
        "cancel_at_period_end": stripe_sub.get("cancel_at_period_end", False),
    }


async def sync_subscription_to_org(stripe_sub, org_id: str = None):
    """Persist a Stripe subscription snapshot onto the owning org."""
    mapped = subscription_from_stripe(stripe_sub)
    if not org_id:
        existing = await db.organizations.find_one(
            {"subscription.stripe_subscription_id": mapped["stripe_subscription_id"]}, {"_id": 0})
        if existing:
            org_id = existing["id"]
    if not org_id:
        return None
    await db.organizations.update_one({"id": org_id}, {"$set": {"subscription": mapped}})
    return org_id
