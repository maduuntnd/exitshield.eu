"""Vendor settings: real Stripe Connect (Standard, OAuth) + integration snippet.

The vendor authorizes ChurnGuard via Stripe Connect OAuth; we store their connected
`acct_...` id and scope every subscription mutation with `stripe_account=<acct>`.
"""
import os
import secrets
import logging
from datetime import datetime, timezone
import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from ..db import db
from ..auth import get_current_user

logger = logging.getLogger("churnguard.settings")
router = APIRouter(prefix="/api/settings", tags=["settings"])

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
CONNECT_CLIENT_ID = os.environ.get("STRIPE_CONNECT_CLIENT_ID", "")
CONNECT_REDIRECT_URI = os.environ.get("STRIPE_CONNECT_REDIRECT_URI", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")


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
        "live_platform": bool(CONNECT_CLIENT_ID),
    }


@router.post("/stripe/connect")
async def stripe_connect(user: dict = Depends(get_current_user)):
    """Return the Stripe Connect OAuth authorize URL for the vendor."""
    org = await _require_org_doc(user)
    if not CONNECT_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Stripe Connect is not configured")

    state = secrets.token_urlsafe(24)
    await db.oauth_states.insert_one({
        "state": state, "org_id": org["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": CONNECT_CLIENT_ID,
        "scope": "read_write",
        "redirect_uri": CONNECT_REDIRECT_URI,
        "state": state,
    }
    url = "https://connect.stripe.com/oauth/authorize?" + urlencode(params)
    return {"mode": "oauth", "url": url}


@router.get("/stripe/connect/callback")
async def stripe_connect_callback(code: str = None, state: str = None, error: str = None):
    """Stripe redirects the vendor's browser here after they authorize."""
    dest = f"{FRONTEND_URL}/dashboard/settings"
    if error or not code or not state:
        return RedirectResponse(f"{dest}?stripe=error")

    rec = await db.oauth_states.find_one({"state": state})
    if not rec:
        return RedirectResponse(f"{dest}?stripe=error")
    org_id = rec["org_id"]
    await db.oauth_states.delete_one({"state": state})

    try:
        token = stripe.OAuth.token(grant_type="authorization_code", code=code)
    except Exception:
        logger.exception("Stripe OAuth token exchange failed")
        return RedirectResponse(f"{dest}?stripe=error")

    connect = {
        "connected": True,
        "account_id": token["stripe_user_id"],
        "simulated": False,
        "livemode": token.get("livemode", True),
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.organizations.update_one({"id": org_id}, {"$set": {"stripe_connect": connect}})
    return RedirectResponse(f"{dest}?stripe=connected")


@router.post("/stripe/disconnect")
async def stripe_disconnect(user: dict = Depends(get_current_user)):
    org = await _require_org_doc(user)
    acct = (org.get("stripe_connect") or {}).get("account_id")
    if acct and CONNECT_CLIENT_ID:
        try:
            stripe.OAuth.deauthorize(client_id=CONNECT_CLIENT_ID, stripe_user_id=acct)
        except Exception:
            logger.warning("Stripe deauthorize failed for %s", acct)
    await db.organizations.update_one(
        {"id": org["id"]}, {"$set": {"stripe_connect": {"connected": False}}})
    return {"ok": True}
