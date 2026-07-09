"""ChurnGuard vendor billing: plan definitions, entitlements, and the trial/renewal
lifecycle engine.

NOTE: The pre-configured `sk_test_emergent` key is an Emergent checkout proxy that
cannot create real recurring Stripe subscriptions or save cards for auto-charge.
So the trial -> auto-charge -> renewal lifecycle is driven by this in-app engine
(evaluate_lifecycle), while the actual "pay / add payment method" step uses a real
Emergent Stripe checkout session. Supplying a real Stripe key + subscription-mode
prices later makes billing fully live without rearchitecting.
"""
from datetime import datetime, timezone, timedelta
from .db import db

TRIAL_DAYS = 14
GRACE_DAYS = 2          # days past due before hard suspension
PERIOD_DAYS = 30
SESSION_WINDOW_DAYS = 30

PLANS = {
    "starter": {
        "id": "starter",
        "name": "Starter",
        "price": 49.0,
        "session_limit": 250,
        "offer_limit": 3,
        "seats": 1,
        "badge_removal": False,
        "advanced_analytics": False,
        "custom_branding": False,
        "api_access": False,
        "tagline": "For indie SaaS testing the waters.",
        "features": [
            "Up to 250 save-sessions / mo",
            "3 active retention offers",
            "Core dashboard & analytics",
            "1 team seat",
        ],
    },
    "growth": {
        "id": "growth",
        "name": "Growth",
        "price": 99.0,
        "session_limit": 1500,
        "offer_limit": 15,
        "seats": 3,
        "badge_removal": True,
        "advanced_analytics": True,
        "custom_branding": False,
        "api_access": False,
        "tagline": "For scaling teams recovering real MRR.",
        "features": [
            "Up to 1,500 save-sessions / mo",
            "15 active retention offers",
            "Advanced analytics & exports",
            "Remove ChurnGuard badge",
            "3 team seats",
        ],
    },
    "scale": {
        "id": "scale",
        "name": "Scale",
        "price": 149.0,
        "session_limit": 10000,
        "offer_limit": 100,
        "seats": 10,
        "badge_removal": True,
        "advanced_analytics": True,
        "custom_branding": True,
        "api_access": True,
        "tagline": "For high-volume products that live on retention.",
        "features": [
            "Up to 10,000 save-sessions / mo",
            "Unlimited retention offers",
            "Advanced analytics, exports & API",
            "Custom branding + white-label",
            "10 team seats",
        ],
    },
}

DEFAULT_TRIAL_PLAN = "growth"


def _dt(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


def new_trial_subscription(plan_id: str = DEFAULT_TRIAL_PLAN) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "plan_id": plan_id if plan_id in PLANS else DEFAULT_TRIAL_PLAN,
        "status": "trialing",
        "trial_ends_at": (now + timedelta(days=TRIAL_DAYS)).isoformat(),
        "current_period_end": None,
        "grace_until": None,
        "payment_method_on_file": False,
        "cancel_at_period_end": False,
        "started_at": now.isoformat(),
    }


async def evaluate_lifecycle(org: dict) -> dict:
    """Advance the subscription state machine based on elapsed time and persist it.
    Returns the (possibly updated) subscription dict."""
    sub = org.get("subscription")
    if not sub:
        sub = new_trial_subscription()
        await db.organizations.update_one({"id": org["id"]}, {"$set": {"subscription": sub}})
        return sub

    now = datetime.now(timezone.utc)
    changed = False
    status = sub.get("status")

    if status == "trialing":
        trial_end = _dt(sub.get("trial_ends_at"))
        if trial_end and now >= trial_end:
            if sub.get("payment_method_on_file"):
                # Simulated auto-charge at trial end.
                sub["status"] = "active"
                sub["current_period_end"] = (trial_end + timedelta(days=PERIOD_DAYS)).isoformat()
                changed = True
            else:
                sub["status"] = "past_due"
                sub["grace_until"] = (trial_end + timedelta(days=GRACE_DAYS)).isoformat()
                changed = True

    if sub.get("status") == "past_due":
        grace = _dt(sub.get("grace_until"))
        if grace and now >= grace:
            sub["status"] = "suspended"
            changed = True

    if sub.get("status") == "active":
        period_end = _dt(sub.get("current_period_end"))
        if period_end and now >= period_end:
            if sub.get("cancel_at_period_end"):
                sub["status"] = "canceled"
                changed = True
            elif sub.get("payment_method_on_file"):
                # Simulated renewal charge.
                sub["current_period_end"] = (period_end + timedelta(days=PERIOD_DAYS)).isoformat()
                changed = True
            else:
                sub["status"] = "past_due"
                sub["grace_until"] = (period_end + timedelta(days=GRACE_DAYS)).isoformat()
                changed = True

    if changed:
        await db.organizations.update_one({"id": org["id"]}, {"$set": {"subscription": sub}})
    return sub


async def get_state(org: dict) -> dict:
    """Full entitlement + usage snapshot for an organization."""
    sub = await evaluate_lifecycle(org)
    plan = PLANS.get(sub["plan_id"], PLANS[DEFAULT_TRIAL_PLAN])
    org_id = org["id"]

    since = (datetime.now(timezone.utc) - timedelta(days=SESSION_WINDOW_DAYS)).isoformat()
    session_usage = await db.cancel_sessions.count_documents(
        {"org_id": org_id, "seed": {"$ne": True}, "created_at": {"$gte": since}})
    offer_usage = await db.retention_offers.count_documents({"org_id": org_id})

    status = sub["status"]
    over_sessions = session_usage >= plan["session_limit"]
    over_offers = offer_usage >= plan["offer_limit"]

    # Access model: trialing/active have full access. past_due = soft (grace) access.
    # suspended/canceled = hard limited.
    hard_limited = status in ("suspended", "canceled")
    soft_limited = status == "past_due" or (not hard_limited and (over_sessions or over_offers))

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
        "trial_days_left": trial_days_left,
    }
