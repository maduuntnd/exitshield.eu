from fastapi import APIRouter, HTTPException
from ..db import db
from ..models import (SessionInitRequest, SessionRespondRequest, ApplyOfferRequest,
                      gen_id, now_iso)
from ..stripe_service import apply_discount, pause_subscription, cancel_at_period_end

router = APIRouter(prefix="/api/v1", tags=["public-session"])


async def _org_by_api_key(api_key: str):
    org = await db.organizations.find_one({"api_key": api_key}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return org


@router.post("/session/init")
async def session_init(body: SessionInitRequest):
    """Validate vendor API key, resolve customer, create a secure cancellation session."""
    org = await _org_by_api_key(body.api_key)
    org_id = org["id"]

    customer = await db.customers.find_one(
        {"org_id": org_id, "external_user_id": body.external_user_id}, {"_id": 0})
    if customer is None:
        # Create an ephemeral customer record for unknown external users.
        customer = {
            "id": gen_id("cust_"),
            "org_id": org_id,
            "external_user_id": body.external_user_id,
            "email": body.email or f"{body.external_user_id}@unknown.com",
            "stripe_customer_id": None,
            "stripe_subscription_id": body.subscription_id,
            "mrr": 49,
            "current_status": "active",
            "created_at": now_iso(),
        }
        await db.customers.insert_one(dict(customer))
    elif body.subscription_id and not customer.get("stripe_subscription_id"):
        await db.customers.update_one({"id": customer["id"]},
                                      {"$set": {"stripe_subscription_id": body.subscription_id}})
        customer["stripe_subscription_id"] = body.subscription_id

    flow = await db.cancellation_flows.find_one({"org_id": org_id, "active": True}, {"_id": 0})
    if not flow:
        flow = await db.cancellation_flows.find_one({"org_id": org_id}, {"_id": 0})
    if not flow:
        raise HTTPException(status_code=404, detail="No cancellation flow configured")

    token = gen_id("tok_")
    session = {
        "id": gen_id("sess_"),
        "token": token,
        "org_id": org_id,
        "customer_id": customer["id"],
        "external_user_id": body.external_user_id,
        "flow_id": flow["id"],
        "current_step": 1,
        "selected_reason": None,
        "final_outcome": None,
        "offer_id": None,
        "mrr": customer.get("mrr", 49),
        "seed": False,
        "created_at": now_iso(),
    }
    await db.cancel_sessions.insert_one(dict(session))

    return {
        "token": token,
        "org_name": org["name"],
        "customer_email": customer.get("email"),
        "flow": {
            "title": flow["steps_json"].get("title", "We're sad to see you go"),
            "reasons": flow["steps_json"].get("reasons", []),
        },
    }


@router.post("/session/respond")
async def session_respond(body: SessionRespondRequest):
    """Store the user's reason and return the best-matching retention offer."""
    session = await db.cancel_sessions.find_one({"token": body.token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.cancel_sessions.update_one(
        {"token": body.token},
        {"$set": {"selected_reason": body.selected_reason, "feedback": body.feedback,
                  "current_step": 2}})

    org_id = session["org_id"]
    # Match an active offer to the selected reason, else fall back to any active offer.
    offer = await db.retention_offers.find_one(
        {"org_id": org_id, "active": True, "trigger_reason": body.selected_reason}, {"_id": 0})
    if not offer:
        offer = await db.retention_offers.find_one(
            {"org_id": org_id, "active": True, "type": "discount"}, {"_id": 0})
    if not offer:
        offer = await db.retention_offers.find_one({"org_id": org_id, "active": True}, {"_id": 0})

    if offer:
        await db.cancel_sessions.update_one({"token": body.token},
                                            {"$set": {"offer_id": offer["id"]}})

    return {"offer": offer}


@router.post("/stripe/apply-offer")
async def apply_offer(body: ApplyOfferRequest):
    """Communicate with Stripe to modify the subscription based on the user's choice."""
    session = await db.cancel_sessions.find_one({"token": body.token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    customer = await db.customers.find_one({"id": session["customer_id"]}, {"_id": 0})
    sub_id = customer.get("stripe_subscription_id") if customer else None
    org = await db.organizations.find_one({"id": session["org_id"]}, {"_id": 0})

    result = {}
    final_outcome = None
    new_status = "active"

    if body.action == "accept_discount":
        offer = await db.retention_offers.find_one(
            {"id": body.offer_id or session.get("offer_id")}, {"_id": 0})
        if not offer:
            raise HTTPException(status_code=400, detail="Offer not found")
        coupon_id = offer.get("stripe_coupon_id") or "sim_coupon"
        result = apply_discount(sub_id, coupon_id)
        final_outcome = "retained_discount"
        await db.retention_offers.update_one({"id": offer["id"]}, {"$inc": {"claim_count": 1}})

    elif body.action == "accept_pause":
        offer = await db.retention_offers.find_one(
            {"id": body.offer_id or session.get("offer_id")}, {"_id": 0})
        days = (offer.get("pause_days") if offer else None) or 30
        result = pause_subscription(sub_id, days)
        final_outcome = "retained_pause"
        new_status = "paused"
        if offer:
            await db.retention_offers.update_one({"id": offer["id"]}, {"$inc": {"claim_count": 1}})

    elif body.action == "cancel":
        result = cancel_at_period_end(sub_id)
        final_outcome = "canceled"
        new_status = "canceled"

    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    await db.cancel_sessions.update_one(
        {"token": body.token},
        {"$set": {"final_outcome": final_outcome, "current_step": 3}})
    if customer:
        await db.customers.update_one({"id": customer["id"]},
                                      {"$set": {"current_status": new_status}})

    return {
        "outcome": final_outcome,
        "stripe": result,
        "return_url": org.get("return_url") if org else None,
        "org_name": org.get("name") if org else None,
    }
