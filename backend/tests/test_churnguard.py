"""ChurnGuard backend API tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://churn-guard-14.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "demo@churnguard.io"
ADMIN_PASSWORD = "ChurnGuard2026!"
DEMO_API_KEY = "cg_live_demo_9f3a7c21b8e4"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data.get("org_id")
    return s


# ---------- Health ----------
def test_health():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------- Auth ----------
class TestAuth:
    def test_invalid_login_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_login_success_and_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_register_creates_org(self):
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass123!", "name": "Test User",
            "organization_name": "TEST_Org"
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == email
        assert data["org_id"]
        # /me should succeed with returned cookies
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200

    def test_logout_clears_session(self):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # After logout, /me should be 401
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 401


# ---------- Dashboard ----------
class TestDashboard:
    def test_kpis(self, admin_session):
        r = admin_session.get(f"{API}/dashboard/kpis")
        assert r.status_code == 200
        d = r.json()
        for k in ["churn_saved_pct", "mrr_recovered", "mrr_lost", "total_sessions",
                  "top_reasons", "mrr_trend", "outcome_breakdown"]:
            assert k in d
        assert d["total_sessions"] > 0, "expected seeded sessions"
        assert isinstance(d["top_reasons"], list) and len(d["top_reasons"]) > 0
        assert len(d["mrr_trend"]) == 8

    def test_organization(self, admin_session):
        r = admin_session.get(f"{API}/organization")
        assert r.status_code == 200
        d = r.json()
        assert d["name"] == "Acme Analytics"
        assert d["api_key"] == DEMO_API_KEY

    def test_analytics_sessions(self, admin_session):
        r = admin_session.get(f"{API}/analytics/sessions")
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) > 0

    def test_kpis_unauth_401(self):
        r = requests.get(f"{API}/dashboard/kpis")
        assert r.status_code == 401


# ---------- Offers CRUD ----------
class TestOffers:
    def test_list_offers_seeded(self, admin_session):
        r = admin_session.get(f"{API}/offers")
        assert r.status_code == 200
        offers = r.json()
        assert len(offers) >= 4

    def test_offer_crud_lifecycle(self, admin_session):
        # CREATE
        payload = {"type": "discount", "value": "TEST 25% off", "description": "test offer",
                   "trigger_reason": "Too expensive", "discount_percent": 25, "active": True}
        r = admin_session.post(f"{API}/offers", json=payload)
        assert r.status_code == 200, r.text
        created = r.json()
        oid = created["id"]
        assert created["value"] == "TEST 25% off"
        assert created["active"] is True
        assert created["stripe_coupon_id"]  # simulated

        # verify in list
        lst = admin_session.get(f"{API}/offers").json()
        assert any(o["id"] == oid for o in lst)

        # PATCH: toggle off
        r = admin_session.patch(f"{API}/offers/{oid}", json={"active": False})
        assert r.status_code == 200
        assert r.json()["active"] is False

        # PATCH: update value
        r = admin_session.patch(f"{API}/offers/{oid}", json={"value": "TEST 40% off", "discount_percent": 40})
        assert r.status_code == 200
        assert r.json()["value"] == "TEST 40% off"

        # DELETE
        r = admin_session.delete(f"{API}/offers/{oid}")
        assert r.status_code == 200
        lst = admin_session.get(f"{API}/offers").json()
        assert not any(o["id"] == oid for o in lst)


# ---------- Public Cancellation Session ----------
class TestPublicSession:
    def test_init_bad_api_key_401(self):
        r = requests.post(f"{API}/v1/session/init", json={
            "api_key": "bad_key", "external_user_id": "ext_1001",
            "subscription_id": "sub_demo_1001"
        })
        assert r.status_code == 401

    def _init(self, ext_id="ext_1001", sub="sub_demo_1001"):
        r = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": ext_id, "subscription_id": sub
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["token"]
        assert d["org_name"] == "Acme Analytics"
        assert "Too expensive" in d["flow"]["reasons"]
        return d["token"]

    def test_flow_discount_accept(self, admin_session):
        token = self._init()
        r = requests.post(f"{API}/v1/session/respond", json={
            "token": token, "selected_reason": "Too expensive"})
        assert r.status_code == 200
        offer = r.json()["offer"]
        assert offer and offer["type"] == "discount"
        assert offer["discount_percent"] == 50

        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": token, "action": "accept_discount", "offer_id": offer["id"]})
        assert r.status_code == 200
        d = r.json()
        assert d["outcome"] == "retained_discount"
        assert d["stripe"]["simulated"] is True
        assert "SIMULATED" in d["stripe"]["message"] or d["stripe"]["ok"]

    def test_flow_pause_accept(self):
        token = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1002",
            "subscription_id": "sub_demo_1002"}).json()["token"]
        r = requests.post(f"{API}/v1/session/respond", json={
            "token": token, "selected_reason": "Not using it enough"})
        offer = r.json()["offer"]
        assert offer["type"] == "pause"
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": token, "action": "accept_pause", "offer_id": offer["id"]})
        assert r.status_code == 200
        assert r.json()["outcome"] == "retained_pause"
        assert r.json()["stripe"]["simulated"] is True

    def test_flow_cancel(self):
        token = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1003",
            "subscription_id": "sub_demo_1003"}).json()["token"]
        requests.post(f"{API}/v1/session/respond", json={
            "token": token, "selected_reason": "Technical issues"})
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": token, "action": "cancel"})
        assert r.status_code == 200
        d = r.json()
        assert d["outcome"] == "canceled"
        assert d["stripe"]["simulated"] is True

    def test_invalid_action(self):
        token = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1004",
            "subscription_id": "sub_demo_1004"}).json()["token"]
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": token, "action": "invalid_xyz"})
        assert r.status_code == 400
