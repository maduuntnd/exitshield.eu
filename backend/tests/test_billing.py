"""ChurnGuard vendor billing API tests (iteration 2)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://churn-guard-14.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL

ADMIN_EMAIL = "demo@churnguard.io"
ADMIN_PASSWORD = "ChurnGuard2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# ---------- Plans (public) ----------
def test_plans_public_no_auth():
    r = requests.get(f"{API}/billing/plans")
    assert r.status_code == 200
    data = r.json()
    plans = {p["id"]: p for p in data["plans"]}
    assert set(plans.keys()) == {"starter", "growth", "scale"}
    assert plans["starter"]["price"] == 49.0
    assert plans["starter"]["offer_limit"] == 3
    assert plans["growth"]["price"] == 99.0
    assert plans["growth"]["offer_limit"] == 15
    assert plans["scale"]["price"] == 149.0
    assert plans["scale"]["offer_limit"] == 100


# ---------- Subscription state ----------
class TestSubscription:
    def test_get_subscription_trialing_growth(self, admin_session):
        r = admin_session.get(f"{API}/billing/subscription")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subscription"]["status"] == "trialing"
        assert d["subscription"]["plan_id"] == "growth"
        assert d["plan"]["id"] == "growth"
        assert d["plan"]["price"] == 99.0
        assert d["limits"]["offers"] == 15
        assert d["limits"]["sessions"] == 1500
        assert "sessions" in d["usage"] and "offers" in d["usage"]
        assert d["soft_limited"] is False
        assert d["hard_limited"] is False
        assert d["trial_days_left"] is not None and d["trial_days_left"] >= 0

    def test_subscription_unauth_401(self):
        r = requests.get(f"{API}/billing/subscription")
        assert r.status_code == 401


# ---------- Checkout ----------
class TestCheckout:
    def test_create_checkout_scale(self, admin_session):
        r = admin_session.post(f"{API}/billing/checkout",
                               json={"plan_id": "scale", "origin_url": ORIGIN})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith("http")
        assert d["session_id"]
        # save for status test
        pytest.session_id_scale = d["session_id"]

    def test_checkout_invalid_plan(self, admin_session):
        r = admin_session.post(f"{API}/billing/checkout",
                               json={"plan_id": "nope", "origin_url": ORIGIN})
        assert r.status_code == 400

    def test_checkout_status(self, admin_session):
        sid = getattr(pytest, "session_id_scale", None)
        if not sid:
            pytest.skip("no session id from previous test")
        r = admin_session.get(f"{API}/billing/checkout/status/{sid}")
        assert r.status_code == 200, r.text
        d = r.json()
        # payment_status is expected to be unpaid/open since we never complete
        assert "payment_status" in d
        assert "status" in d
        assert d["plan_id"] == "scale"

    def test_checkout_status_not_found(self, admin_session):
        r = admin_session.get(f"{API}/billing/checkout/status/nonexistent_sid")
        assert r.status_code == 404


# ---------- Plan changes & cancel ----------
class TestChangeAndCancel:
    def test_change_plan_to_starter_then_back_to_growth(self, admin_session):
        r = admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "starter"})
        assert r.status_code == 200, r.text
        assert r.json()["subscription"]["plan_id"] == "starter"

        # verify via GET
        r = admin_session.get(f"{API}/billing/subscription")
        assert r.json()["subscription"]["plan_id"] == "starter"

        # revert to growth so other tests / UI remain consistent with seed
        r = admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "growth"})
        assert r.status_code == 200
        assert r.json()["subscription"]["plan_id"] == "growth"

    def test_change_plan_invalid(self, admin_session):
        r = admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "gold"})
        assert r.status_code == 400

    def test_cancel_sets_cancel_at_period_end(self, admin_session):
        r = admin_session.post(f"{API}/billing/cancel")
        assert r.status_code == 200
        assert r.json()["subscription"]["cancel_at_period_end"] is True
        # verify via GET
        r = admin_session.get(f"{API}/billing/subscription")
        assert r.json()["subscription"]["cancel_at_period_end"] is True

        # reset cancel flag via change-plan to keep state clean
        r = admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "growth"})
        assert r.json()["subscription"]["cancel_at_period_end"] is False


# ---------- Offer limit enforcement (402) ----------
class TestOfferLimit:
    def test_normal_offer_create_ok_under_growth_limit(self, admin_session):
        # Growth limit is 15; demo has ~4 offers, well under.
        payload = {"type": "discount", "value": "TEST BILLING 10%", "description": "billing limit test",
                   "trigger_reason": "Too expensive", "discount_percent": 10, "active": True}
        r = admin_session.post(f"{API}/offers", json=payload)
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        # cleanup
        admin_session.delete(f"{API}/offers/{oid}")

    def test_offer_limit_402_when_over(self, admin_session):
        """Switch org to Starter (limit 3), then attempt creating offers beyond limit -> 402."""
        # Move to starter (limit 3). Demo has ~4 existing offers already, so any new create should 402.
        r = admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "starter"})
        assert r.status_code == 200
        state = r.json()
        try:
            assert state["limits"]["offers"] == 3
            # Should already be over-limit
            assert state["usage"]["offers"] >= state["limits"]["offers"]
            payload = {"type": "discount", "value": "TEST OVERLIMIT", "description": "should fail",
                       "trigger_reason": "Too expensive", "discount_percent": 10, "active": True}
            r = admin_session.post(f"{API}/offers", json=payload)
            assert r.status_code == 402, f"expected 402 got {r.status_code} {r.text}"
            assert "limit" in r.json().get("detail", "").lower() or "upgrade" in r.json().get("detail", "").lower()
        finally:
            # revert plan
            admin_session.post(f"{API}/billing/change-plan", json={"plan_id": "growth"})
