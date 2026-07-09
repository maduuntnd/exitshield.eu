import os
import random
from datetime import datetime, timezone, timedelta
from .db import db
from .auth import hash_password, verify_password
from .models import gen_id, now_iso

DEMO_API_KEY = "cg_live_demo_9f3a7c21b8e4"

CANCEL_REASONS = [
    "Too expensive",
    "Missing features",
    "Not using it enough",
    "Switching to a competitor",
    "Technical issues",
]

DEFAULT_FLOW_STEPS = {
    "title": "We're sad to see you go",
    "reasons": CANCEL_REASONS,
}


async def _write_credentials(admin_email: str, admin_password: str):
    content = f"""# Test Credentials

## Vendor Dashboard (JWT email/password)
- Email: {admin_email}
- Password: {admin_password}
- Role: admin / vendor (owns the demo organization "Acme Analytics")

## Google Social Login
- Emergent-managed Google OAuth is enabled on /login ("Continue with Google").
- No app-managed password; use any Google account. New Google users get their own org.

## Demo Organization
- Name: Acme Analytics
- API Key (vendor api_key): {DEMO_API_KEY}

## Public Cancellation Portal (no auth, URL-token based)
- Example: {{FRONTEND_URL}}/cancel?user_id=ext_1001&subscription_id=sub_demo_1001&api_key={DEMO_API_KEY}
- Valid demo external_user_ids: ext_1001, ext_1002, ext_1003, ext_1004, ext_1005

## Key Endpoints
- POST /api/auth/register, /api/auth/login, /api/auth/logout, GET /api/auth/me
- POST /api/auth/google/session (Emergent OAuth session exchange)
- GET /api/dashboard/kpis, /api/offers, /api/analytics/sessions
- POST /api/v1/session/init, /api/v1/session/respond, /api/v1/stripe/apply-offer
"""
    os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(content)


async def seed():
    admin_email = os.environ.get("ADMIN_EMAIL", "demo@churnguard.io")
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChurnGuard2026!")

    # 1) Admin user
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        user_id = gen_id("user_")
        await db.users.insert_one({
            "user_id": user_id,
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Demo Vendor",
            "role": "admin",
            "auth_provider": "password",
            "org_id": None,
            "created_at": now_iso(),
        })
    else:
        user_id = existing["user_id"]
        if not existing.get("password_hash") or not verify_password(admin_password, existing["password_hash"]):
            await db.users.update_one({"email": admin_email},
                                      {"$set": {"password_hash": hash_password(admin_password)}})

    # 2) Demo organization
    org = await db.organizations.find_one({"api_key": DEMO_API_KEY}, {"_id": 0})
    if org is None:
        org_id = gen_id("org_")
        org = {
            "id": org_id,
            "name": "Acme Analytics",
            "api_key": DEMO_API_KEY,
            "owner_id": user_id,
            "created_at": now_iso(),
        }
        await db.organizations.insert_one(org)
    else:
        org_id = org["id"]
    await db.users.update_one({"user_id": user_id}, {"$set": {"org_id": org_id}})

    # 3) Cancellation flow
    if await db.cancellation_flows.find_one({"org_id": org_id}) is None:
        await db.cancellation_flows.insert_one({
            "id": gen_id("flow_"),
            "org_id": org_id,
            "steps_json": DEFAULT_FLOW_STEPS,
            "active": True,
            "created_at": now_iso(),
        })

    # 4) Retention offers
    if await db.retention_offers.count_documents({"org_id": org_id}) == 0:
        offers = [
            {"type": "discount", "value": "50% off for 2 months", "description": "Half price for the next two billing cycles.",
             "trigger_reason": "Too expensive", "discount_percent": 50, "pause_days": None,
             "stripe_coupon_id": "sim_coupon_50off", "claim_count": 0, "active": True},
            {"type": "pause", "value": "Pause for 30 days", "description": "Take a break — keep your data, pay nothing for 30 days.",
             "trigger_reason": "Not using it enough", "discount_percent": None, "pause_days": 30,
             "stripe_coupon_id": None, "claim_count": 0, "active": True},
            {"type": "discount", "value": "30% off for 2 months", "description": "A little something to keep you around.",
             "trigger_reason": "Switching to a competitor", "discount_percent": 30, "pause_days": None,
             "stripe_coupon_id": "sim_coupon_30off", "claim_count": 0, "active": True},
            {"type": "bonus", "value": "Free onboarding call", "description": "A 1:1 session to unlock the features you're missing.",
             "trigger_reason": "Missing features", "discount_percent": None, "pause_days": None,
             "stripe_coupon_id": None, "claim_count": 0, "active": True},
        ]
        for o in offers:
            o.update({"id": gen_id("offer_"), "org_id": org_id, "created_at": now_iso()})
            await db.retention_offers.insert_one(o)

    # 5) Demo customers
    if await db.customers.count_documents({"org_id": org_id}) == 0:
        for i in range(1, 6):
            await db.customers.insert_one({
                "id": gen_id("cust_"),
                "org_id": org_id,
                "external_user_id": f"ext_100{i}",
                "email": f"customer{i}@acmeclient.com",
                "stripe_customer_id": f"cus_demo_100{i}",
                "stripe_subscription_id": f"sub_demo_100{i}",
                "mrr": random.choice([29, 49, 99, 149]),
                "current_status": "active",
                "created_at": now_iso(),
            })

    # 6) Historical sessions for analytics/KPIs
    if await db.cancel_sessions.count_documents({"org_id": org_id, "seed": True}) == 0:
        outcomes = ["canceled", "retained_discount", "retained_pause"]
        weights = [0.42, 0.4, 0.18]
        for d in range(40):
            created = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 45),
                                                              hours=random.randint(0, 23))
            outcome = random.choices(outcomes, weights=weights)[0]
            reason = random.choice(CANCEL_REASONS)
            mrr = random.choice([29, 49, 99, 149])
            await db.cancel_sessions.insert_one({
                "id": gen_id("sess_"),
                "token": gen_id("tok_"),
                "org_id": org_id,
                "customer_id": None,
                "external_user_id": f"ext_100{random.randint(1,5)}",
                "flow_id": None,
                "current_step": 3,
                "selected_reason": reason,
                "final_outcome": outcome,
                "offer_id": None,
                "mrr": mrr,
                "seed": True,
                "created_at": created.isoformat(),
            })

    await _write_credentials(admin_email, admin_password)
