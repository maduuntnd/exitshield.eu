import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)
from ..db import db
from ..models import gen_id, now_iso
from ..auth import get_current_user
from ..billing import PLANS, get_state, evaluate_lifecycle, PERIOD_DAYS, new_trial_subscription

logger = logging.getLogger("churnguard.billing")
router = APIRouter(prefix="/api", tags=["billing"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")


def _stripe(request: Request) -> StripeCheckout:
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


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


@router.post("/billing/start-trial")
async def start_trial(body: PlanBody, user: dict = Depends(get_current_user)):
    if body.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    org = await _require_org_doc(user)
    sub = org.get("subscription")
    if sub and sub.get("status") in ("trialing", "active"):
        raise HTTPException(status_code=400, detail="An active subscription already exists")
    new_sub = new_trial_subscription(body.plan_id)
    await db.organizations.update_one({"id": org["id"]}, {"$set": {"subscription": new_sub}})
    org["subscription"] = new_sub
    return await get_state(org)


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutBody, request: Request, user: dict = Depends(get_current_user)):
    """Real Emergent Stripe checkout for paying / adding a payment method for a plan."""
    if body.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    org = await _require_org_doc(user)
    plan = PLANS[body.plan_id]
    amount = float(plan["price"])  # server-side price only

    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/dashboard/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/dashboard/billing"

    stripe = _stripe(request)
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "org_id": org["id"],
            "plan_id": body.plan_id,
            "purpose": "vendor_subscription",
            "user_id": user["user_id"],
        },
    )
    session = await stripe.create_checkout_session(checkout_request)

    await db.payment_transactions.insert_one({
        "id": gen_id("txn_"),
        "session_id": session.session_id,
        "org_id": org["id"],
        "user_id": user["user_id"],
        "plan_id": body.plan_id,
        "amount": amount,
        "currency": "usd",
        "purpose": "vendor_subscription",
        "payment_status": "initiated",
        "status": "initiated",
        "processed": False,
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


async def _activate_plan(org_id: str, plan_id: str):
    now = datetime.now(timezone.utc)
    sub = {
        "plan_id": plan_id,
        "status": "active",
        "trial_ends_at": None,
        "current_period_end": (now + timedelta(days=PERIOD_DAYS)).isoformat(),
        "grace_until": None,
        "payment_method_on_file": True,
        "cancel_at_period_end": False,
        "started_at": now.isoformat(),
    }
    await db.organizations.update_one({"id": org_id}, {"$set": {"subscription": sub}})


@router.get("/billing/checkout/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    stripe = _stripe(request)
    status = await stripe.get_checkout_status(session_id)

    update = {"payment_status": status.payment_status, "status": status.status}
    if status.payment_status == "paid" and not txn.get("processed"):
        update["processed"] = True
        await _activate_plan(txn["org_id"], txn["plan_id"])
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    return {
        "payment_status": status.payment_status,
        "status": status.status,
        "plan_id": txn["plan_id"],
        "amount": status.amount_total / 100.0 if status.amount_total else txn["amount"],
    }


@router.post("/billing/change-plan")
async def change_plan(body: PlanBody, user: dict = Depends(get_current_user)):
    if body.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    org = await _require_org_doc(user)
    sub = org.get("subscription") or new_trial_subscription(body.plan_id)
    sub["plan_id"] = body.plan_id
    sub["cancel_at_period_end"] = False
    await db.organizations.update_one({"id": org["id"]}, {"$set": {"subscription": sub}})
    org["subscription"] = sub
    return await get_state(org)


@router.post("/billing/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    sub = org.get("subscription")
    if not sub:
        raise HTTPException(status_code=400, detail="No subscription to cancel")
    sub["cancel_at_period_end"] = True
    await db.organizations.update_one({"id": org["id"]}, {"$set": {"subscription": sub}})
    org["subscription"] = sub
    return await get_state(org)


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    stripe = _stripe(request)
    try:
        event = await stripe.handle_webhook(body, sig)
    except Exception as e:
        logger.warning("Webhook parse failed: %s", e)
        return {"received": True}

    if event.session_id and event.payment_status == "paid":
        txn = await db.payment_transactions.find_one({"session_id": event.session_id}, {"_id": 0})
        if txn and not txn.get("processed"):
            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {"processed": True, "payment_status": "paid", "status": "complete"}})
            await _activate_plan(txn["org_id"], txn["plan_id"])
    return {"received": True}
