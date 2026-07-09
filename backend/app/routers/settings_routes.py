"""Vendor settings: Stripe Connect + integration snippet.

PRODUCTION NOTE: Real Stripe Connect requires a live Stripe *platform* account with
Connect enabled. The vendor would be redirected to Stripe's OAuth screen and we'd store
the returned connected `account_id`; every subscription call is then scoped with
`stripe_account=<account_id>`. The `sk_test_emergent` proxy cannot perform Connect OAuth,
so `connect` here performs a clearly-labelled SIMULATED connection that stores a test
account id and exercises the exact same downstream code path.
"""
import os
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from ..db import db
from ..auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _live_platform_key() -> bool:
    key = os.environ.get("STRIPE_API_KEY", "")
    return key.startswith("sk_") and key != "sk_test_emergent"


async def _require_org_doc(user: dict) -> dict:
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization for user")
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/integration")
async def integration_info(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    connect = org.get("stripe_connect") or {"connected": False}
    return {
        "org_name": org["name"],
        "api_key": org["api_key"],
        "stripe_connect": {
            "connected": connect.get("connected", False),
            "account_id": connect.get("account_id"),
            "simulated": connect.get("simulated", False),
            "connected_at": connect.get("connected_at"),
        },
        "live_platform": _live_platform_key(),
    }


@router.post("/stripe/connect")
async def stripe_connect(user: dict = Depends(get_current_user)):
    """Begin Stripe Connect. With a live platform key this returns an OAuth URL; with the
    demo proxy it performs a simulated connection so the flow is demonstrable end-to-end."""
    org = await _require_org_doc(user)

    if _live_platform_key():
        client_id = os.environ.get("STRIPE_CONNECT_CLIENT_ID")
        if client_id:
            oauth_url = (
                "https://connect.stripe.com/oauth/authorize"
                f"?response_type=code&client_id={client_id}&scope=read_write"
            )
            return {"mode": "oauth", "url": oauth_url}

    # Simulated connection (demo proxy).
    account_id = f"acct_test_{secrets.token_hex(8)}"
    connect = {
        "connected": True,
        "account_id": account_id,
        "simulated": True,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.organizations.update_one({"id": org["id"]}, {"$set": {"stripe_connect": connect}})
    return {"mode": "simulated", "stripe_connect": connect}


@router.post("/stripe/disconnect")
async def stripe_disconnect(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    await db.organizations.update_one(
        {"id": org["id"]}, {"$set": {"stripe_connect": {"connected": False}}})
    return {"ok": True}
