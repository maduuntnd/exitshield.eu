"""Settings/Integration + Stripe Connect (simulated) tests."""
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
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module", autouse=True)
def ensure_disconnected(admin_session):
    """Always start/finish disconnected."""
    admin_session.post(f"{API}/settings/stripe/disconnect")
    yield
    admin_session.post(f"{API}/settings/stripe/disconnect")


class TestIntegration:
    def test_integration_initial_disconnected(self, admin_session):
        r = admin_session.get(f"{API}/settings/integration")
        assert r.status_code == 200
        d = r.json()
        assert d["org_name"] == "Acme Analytics"
        assert d["api_key"] == DEMO_API_KEY
        assert d["stripe_connect"]["connected"] is False
        assert d["live_platform"] is False

    def test_integration_unauth_401(self):
        r = requests.get(f"{API}/settings/integration")
        assert r.status_code == 401


class TestStripeConnect:
    def test_connect_simulated(self, admin_session):
        r = admin_session.post(f"{API}/settings/stripe/connect")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["mode"] == "simulated"
        assert d["stripe_connect"]["connected"] is True
        assert d["stripe_connect"]["account_id"].startswith("acct_test_")

        # verify via GET
        info = admin_session.get(f"{API}/settings/integration").json()
        assert info["stripe_connect"]["connected"] is True
        assert info["stripe_connect"]["account_id"].startswith("acct_test_")

    def test_apply_offer_mentions_connected_account(self, admin_session):
        # Ensure connected
        admin_session.post(f"{API}/settings/stripe/connect")
        info = admin_session.get(f"{API}/settings/integration").json()
        acct = info["stripe_connect"]["account_id"]

        # public flow
        t = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1001",
            "subscription_id": "sub_demo_1001"}).json()["token"]
        requests.post(f"{API}/v1/session/respond", json={
            "token": t, "selected_reason": "Too expensive"})
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": t, "action": "accept_discount"})
        assert r.status_code == 200
        msg = r.json()["stripe"]["message"]
        assert "connected account" in msg
        assert acct in msg

    def test_disconnect(self, admin_session):
        admin_session.post(f"{API}/settings/stripe/connect")
        r = admin_session.post(f"{API}/settings/stripe/disconnect")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        info = admin_session.get(f"{API}/settings/integration").json()
        assert info["stripe_connect"]["connected"] is False

    def test_apply_offer_no_connection_message(self, admin_session):
        admin_session.post(f"{API}/settings/stripe/disconnect")
        t = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1002",
            "subscription_id": "sub_demo_1002"}).json()["token"]
        requests.post(f"{API}/v1/session/respond", json={
            "token": t, "selected_reason": "Too expensive"})
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": t, "action": "accept_discount"})
        assert r.status_code == 200
        assert "no Stripe account connected" in r.json()["stripe"]["message"]
