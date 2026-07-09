import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex
    return f"{prefix}{raw}" if prefix else raw


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    organization_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=6)


class PublicUser(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "vendor"
    org_id: Optional[str] = None
    auth_provider: str = "password"


# ---------- Offers ----------
class OfferCreate(BaseModel):
    type: str  # discount | pause | bonus
    value: str  # e.g. "50% off", "1 month free"
    description: Optional[str] = None
    trigger_reason: Optional[str] = None  # cancellation reason that triggers this offer
    discount_percent: Optional[int] = None
    pause_days: Optional[int] = None
    active: bool = True


class OfferUpdate(BaseModel):
    type: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    trigger_reason: Optional[str] = None
    discount_percent: Optional[int] = None
    pause_days: Optional[int] = None
    active: Optional[bool] = None


# ---------- Flow ----------
class FlowUpdate(BaseModel):
    steps_json: Dict[str, Any]
    active: Optional[bool] = None


# ---------- Public session ----------
class SessionInitRequest(BaseModel):
    api_key: str
    external_user_id: str
    subscription_id: Optional[str] = None
    email: Optional[str] = None


class SessionRespondRequest(BaseModel):
    token: str
    selected_reason: str
    feedback: Optional[str] = None


class ApplyOfferRequest(BaseModel):
    token: str
    action: str  # accept_discount | accept_pause | cancel
    offer_id: Optional[str] = None
