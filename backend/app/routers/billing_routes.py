import os
import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..db import db
from ..auth import get_current_user
from ..billing import (PLANS, PRICE_MAP, TRIAL_DAYS, get_state,
                       sync_subscription_to_org)

logger = logging.getLogger("churnguard.billing")
router = APIRouter(prefix="/api", tags=["billing"])

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


async def _require_org_doc(user: dict) -> dict:
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization for user")
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


class PlanBody(BaseModel):
    plan_id: str


class CheckoutBody(BaseModel):
    plan_id: str
    origin_url: str


@router.get("/billing/plans")
async def list_plans():
    return {"plans": list(PLANS.values())}


@router.get("/billing/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    return await get_state(org)


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutBody, user: dict = Depends(get_current_user)):
    """Start a real Stripe subscription Checkout with a 14-day trial (card required)."""
    if body.plan_id not in PRICE_MAP or not PRICE_MAP[body.plan_id]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    org = await _require_org_doc(user)
    origin = body.origin_url.rstrip("/")

    existing_customer = (org.get("subscription") or {}).get("stripe_customer_id")
    session_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": PRICE_MAP[body.plan_id], "quantity": 1}],
        "success_url": f"{origin}/dashboard/billing?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{origin}/dashboard/billing",
        "subscription_data": {
            "trial_period_days": TRIAL_DAYS,
            "metadata": {"org_id": org["id"], "plan_id": body.plan_id},
        },
        "metadata": {"org_id": org["id"], "plan_id": body.plan_id},
        "allow_promotion_codes": True,
    }
    if existing_customer:
        session_kwargs["customer"] = existing_customer
    else:
        session_kwargs["customer_email"] = user["email"]

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except Exception as e:
        logger.exception("Stripe checkout create failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "org_id": org["id"],
        "user_id": user["user_id"],
        "plan_id": body.plan_id,
        "amount": PLANS[body.plan_id]["price"],
        "currency": "usd",
        "purpose": "vendor_subscription",
        "payment_status": "initiated",
        "status": "initiated",
        "processed": False,
    })
    return {"url": session.url, "session_id": session.id}


@router.get("/billing/checkout/status/{session_id}")
async def checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    complete = session.get("status") == "complete" or session.get("payment_status") in ("paid", "no_payment_required")
    if complete and session.get("subscription"):
        org_id = (session.get("metadata") or {}).get("org_id")
        await sync_subscription_to_org(session["subscription"], org_id)
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"processed": True, "payment_status": session.get("payment_status"),
                      "status": session.get("status")}})

    return {
        "payment_status": session.get("payment_status"),
        "status": session.get("status"),
    }


@router.post("/billing/change-plan")
async def change_plan(body: PlanBody, user: dict = Depends(get_current_user)):
    if body.plan_id not in PRICE_MAP or not PRICE_MAP[body.plan_id]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    org = await _require_org_doc(user)
    sub = org.get("subscription") or {}
    sub_id = sub.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription. Start a plan first.")
    try:
        stripe_sub = stripe.Subscription.retrieve(sub_id)
        item_id = stripe_sub["items"]["data"][0]["id"]
        updated = stripe.Subscription.modify(
            sub_id,
            cancel_at_period_end=False,
            items=[{"id": item_id, "price": PRICE_MAP[body.plan_id]}],
            proration_behavior="create_prorations",
        )
        await sync_subscription_to_org(updated, org["id"])
    except Exception as e:
        logger.exception("change-plan failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")
    fresh = await db.organizations.find_one({"id": org["id"]}, {"_id": 0})
    return await get_state(fresh)


@router.post("/billing/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    sub = org.get("subscription") or {}
    sub_id = sub.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No subscription to cancel")
    try:
        updated = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        await sync_subscription_to_org(updated, org["id"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")
    fresh = await db.organizations.find_one({"id": org["id"]}, {"_id": 0})
    return await get_state(fresh)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature")
    if not sig or not WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Missing signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency: dedupe by event id.
    if await db.webhook_events.find_one({"_id": event["id"]}):
        return JSONResponse({"received": True, "deduped": True})
    await db.webhook_events.insert_one({"_id": event["id"], "type": event["type"]})

    etype = event["type"]
    obj = event["data"]["object"]

    try:
        if etype == "checkout.session.completed":
            org_id = (obj.get("metadata") or {}).get("org_id")
            if obj.get("subscription"):
                sub = stripe.Subscription.retrieve(obj["subscription"])
                await sync_subscription_to_org(sub, org_id)
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted",
                       "customer.subscription.trial_will_end", "invoice.paid",
                       "invoice.payment_failed"):
            sub_obj = obj if obj.get("object") == "subscription" else None
            if sub_obj is None and obj.get("subscription"):
                sub_obj = stripe.Subscription.retrieve(obj["subscription"])
            if sub_obj:
                await sync_subscription_to_org(sub_obj)
    except Exception:
        logger.exception("webhook handling error for %s", etype)

    return {"received": True}
