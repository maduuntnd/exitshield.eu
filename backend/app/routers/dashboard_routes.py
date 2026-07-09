from collections import Counter
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ..db import db
from ..models import OfferCreate, OfferUpdate, FlowUpdate, gen_id, now_iso
from ..auth import get_current_user
from ..stripe_service import create_coupon

router = APIRouter(prefix="/api", tags=["dashboard"])


async def _require_org(user: dict) -> str:
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization for user")
    return org_id


def _parse_dt(v):
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


@router.get("/dashboard/kpis")
async def kpis(user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    sessions = await db.cancel_sessions.find(
        {"org_id": org_id, "final_outcome": {"$ne": None}}, {"_id": 0}).to_list(5000)

    total = len(sessions)
    retained = [s for s in sessions if s.get("final_outcome", "").startswith("retained")]
    canceled = [s for s in sessions if s.get("final_outcome") == "canceled"]
    churn_saved_pct = round((len(retained) / total) * 100, 1) if total else 0.0
    mrr_recovered = sum(s.get("mrr", 0) for s in retained)
    mrr_lost = sum(s.get("mrr", 0) for s in canceled)

    reason_counts = Counter(s.get("selected_reason", "Unknown") for s in sessions)
    top_reasons = [{"reason": r, "count": c} for r, c in reason_counts.most_common(6)]

    # MRR recovered trend (last 8 weeks)
    trend = []
    now = datetime.now(timezone.utc)
    for w in range(7, -1, -1):
        start = now - timedelta(weeks=w + 1)
        end = now - timedelta(weeks=w)
        week_mrr = sum(s.get("mrr", 0) for s in retained
                       if start <= _parse_dt(s["created_at"]) < end)
        trend.append({"week": f"W{8 - w}", "mrr": week_mrr})

    outcome_counts = Counter(s.get("final_outcome") for s in sessions)
    return {
        "churn_saved_pct": churn_saved_pct,
        "mrr_recovered": mrr_recovered,
        "mrr_lost": mrr_lost,
        "total_sessions": total,
        "retained_count": len(retained),
        "canceled_count": len(canceled),
        "top_reasons": top_reasons,
        "mrr_trend": trend,
        "outcome_breakdown": [
            {"name": "Discount", "value": outcome_counts.get("retained_discount", 0)},
            {"name": "Pause", "value": outcome_counts.get("retained_pause", 0)},
            {"name": "Canceled", "value": outcome_counts.get("canceled", 0)},
        ],
    }


# ---------------- Offers CRUD ----------------
@router.get("/offers")
async def list_offers(user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    offers = await db.retention_offers.find({"org_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return offers


@router.post("/offers")
async def create_offer(body: OfferCreate, user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    doc = body.model_dump()
    stripe_coupon_id = None
    if body.type == "discount" and body.discount_percent:
        coupon = create_coupon(body.discount_percent, body.value)
        stripe_coupon_id = coupon["stripe_coupon_id"]
    doc.update({
        "id": gen_id("offer_"),
        "org_id": org_id,
        "stripe_coupon_id": stripe_coupon_id,
        "claim_count": 0,
        "created_at": now_iso(),
    })
    await db.retention_offers.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/offers/{offer_id}")
async def update_offer(offer_id: str, body: OfferUpdate, user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    offer = await db.retention_offers.find_one({"id": offer_id, "org_id": org_id}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates.get("discount_percent") and updates.get("type", offer["type"]) == "discount":
        coupon = create_coupon(updates["discount_percent"], updates.get("value", offer["value"]))
        updates["stripe_coupon_id"] = coupon["stripe_coupon_id"]
    await db.retention_offers.update_one({"id": offer_id}, {"$set": updates})
    return await db.retention_offers.find_one({"id": offer_id}, {"_id": 0})


@router.delete("/offers/{offer_id}")
async def delete_offer(offer_id: str, user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    res = await db.retention_offers.delete_one({"id": offer_id, "org_id": org_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"ok": True}


# ---------------- Flow ----------------
@router.get("/flow")
async def get_flow(user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    flow = await db.cancellation_flows.find_one({"org_id": org_id}, {"_id": 0})
    return flow


@router.put("/flow")
async def update_flow(body: FlowUpdate, user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    updates = {"steps_json": body.steps_json}
    if body.active is not None:
        updates["active"] = body.active
    await db.cancellation_flows.update_one({"org_id": org_id}, {"$set": updates}, upsert=True)
    return await db.cancellation_flows.find_one({"org_id": org_id}, {"_id": 0})


# ---------------- Analytics ----------------
@router.get("/analytics/sessions")
async def analytics_sessions(user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    sessions = await db.cancel_sessions.find(
        {"org_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(300)
    return sessions


@router.get("/organization")
async def get_organization(user: dict = Depends(get_current_user)):
    org_id = await _require_org(user)
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    cust_count = await db.customers.count_documents({"org_id": org_id})
    org["customer_count"] = cust_count
    return org
