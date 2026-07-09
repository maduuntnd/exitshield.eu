import os
import secrets
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from ..db import db
from ..models import (RegisterRequest, LoginRequest, ForgotPasswordRequest,
                      ResetPasswordRequest, gen_id, now_iso)
from ..auth import (hash_password, verify_password, create_access_token,
                    create_refresh_token, set_auth_cookies, clear_auth_cookies,
                    get_current_user, GOOGLE_SESSION_TTL_DAYS)

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCKOUT_MIN = 15


async def _check_lockout(identifier: str):
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if rec and rec.get("count", 0) >= MAX_ATTEMPTS:
        locked_until = rec.get("locked_until")
        if locked_until:
            if isinstance(locked_until, str):
                locked_until = datetime.fromisoformat(locked_until)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > datetime.now(timezone.utc):
                raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")


async def _record_fail(identifier: str):
    rec = await db.login_attempts.find_one({"identifier": identifier})
    count = (rec.get("count", 0) if rec else 0) + 1
    update = {"count": count}
    if count >= MAX_ATTEMPTS:
        update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MIN)).isoformat()
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)


async def _clear_fail(identifier: str):
    await db.login_attempts.delete_one({"identifier": identifier})


async def _create_org_for_user(user_id: str, name: str) -> str:
    org_id = gen_id("org_")
    await db.organizations.insert_one({
        "id": org_id,
        "name": name,
        "api_key": f"cg_live_{secrets.token_hex(10)}",
        "owner_id": user_id,
        "created_at": now_iso(),
    })
    await db.cancellation_flows.insert_one({
        "id": gen_id("flow_"),
        "org_id": org_id,
        "steps_json": {"title": "We're sad to see you go",
                       "reasons": ["Too expensive", "Missing features",
                                   "Not using it enough", "Switching to a competitor",
                                   "Technical issues"]},
        "active": True,
        "created_at": now_iso(),
    })
    return org_id


@router.post("/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = gen_id("user_")
    org_id = await _create_org_for_user(user_id, body.organization_name or f"{body.name}'s Workspace")
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "role": "vendor",
        "auth_provider": "password",
        "org_id": org_id,
        "created_at": now_iso(),
    })
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return {"user_id": user_id, "email": email, "name": body.name,
            "role": "vendor", "org_id": org_id, "auth_provider": "password"}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    await _check_lockout(identifier)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        await _record_fail(identifier)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await _clear_fail(identifier)
    access = create_access_token(user["user_id"], email)
    refresh = create_refresh_token(user["user_id"])
    set_auth_cookies(response, access, refresh)
    return {"user_id": user["user_id"], "email": email, "name": user.get("name", ""),
            "role": user.get("role", "vendor"), "org_id": user.get("org_id"),
            "auth_provider": "password"}


@router.post("/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    import jwt as pyjwt
    from ..auth import _secret, JWT_ALGORITHM
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["user_id"], user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=True,
                            samesite="none", max_age=86400, path="/")
        return {"ok": True}
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    user = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
        })
        print(f"[PASSWORD RESET] Reset link token for {body.email}: {token}")
    return {"ok": True, "message": "If the email exists, a reset link was sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    rec = await db.password_reset_tokens.find_one({"token": body.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    await db.users.update_one({"user_id": rec["user_id"]},
                              {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    return {"ok": True}


# ---------------- Emergent Google OAuth ----------------
class GoogleSessionRequest(BaseModel):
    session_id: str


@router.post("/google/session")
async def google_session(body: GoogleSessionRequest, response: Response):
    session_url = os.environ["EMERGENT_AUTH_SESSION_URL"]
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(session_url, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = data["email"].lower()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user is None:
        user_id = gen_id("user_")
        org_id = await _create_org_for_user(user_id, f"{data.get('name', 'My')} Workspace")
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name", ""),
            "picture": data.get("picture"),
            "role": "vendor",
            "auth_provider": "google",
            "org_id": org_id,
            "created_at": now_iso(),
        })
    else:
        user_id = user["user_id"]
        await db.users.update_one({"user_id": user_id},
                                  {"$set": {"picture": data.get("picture"), "name": data.get("name", user.get("name", ""))}})

    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=GOOGLE_SESSION_TTL_DAYS),
        "created_at": now_iso(),
    })
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=GOOGLE_SESSION_TTL_DAYS * 86400, path="/")
    fresh = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user_id": user_id, "email": email, "name": fresh.get("name", ""),
            "picture": fresh.get("picture"), "role": "vendor",
            "org_id": fresh.get("org_id"), "auth_provider": "google"}
