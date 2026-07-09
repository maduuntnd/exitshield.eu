"""Settings/Integration + Stripe Connect (REAL OAuth) tests - iteration 4.

Behavior changes vs iteration 3:
- /settings/stripe/connect returns {mode:'oauth', url:...} with a connect.stripe.com
  URL containing the configured client_id. It does NOT flip connected=True (that
  happens only after real OAuth callback which we cannot execute).
- /settings/integration.live_platform is True (client_id is configured).
- Public apply-offer for unconnected org returns simulated "no Stripe account connected".
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
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
    admin_session.post(f"{API}/settings/stripe/disconnect")
    yield
    admin_session.post(f"{API}/settings/stripe/disconnect")


class TestIntegration:
    def test_integration_demo_disconnected_live_platform(self, admin_session):
        r = admin_session.get(f"{API}/settings/integration")
        assert r.status_code == 200
        d = r.json()
        assert d["org_name"] == "Acme Analytics"
        assert d["api_key"] == DEMO_API_KEY
        assert d["stripe_connect"]["connected"] is False
        assert d["live_platform"] is True

    def test_integration_unauth_401(self):
        r = requests.get(f"{API}/settings/integration")
        assert r.status_code in (401, 403)


class TestStripeConnectOAuth:
    def test_connect_returns_real_oauth_url(self, admin_session):
        r = admin_session.post(f"{API}/settings/stripe/connect")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["mode"] == "oauth"
        assert d["url"].startswith("https://connect.stripe.com/oauth/authorize"), d["url"]
        # Contains configured client_id (prefix from problem statement)
        assert "client_id=ca_Ur9Mzk7" in d["url"], d["url"]
        # response_type + state present
        assert "response_type=code" in d["url"]
        assert "state=" in d["url"]

    def test_connect_does_not_flip_connected(self, admin_session):
        """Real OAuth requires callback; simply calling connect should NOT set connected."""
        admin_session.post(f"{API}/settings/stripe/connect")
        info = admin_session.get(f"{API}/settings/integration").json()
        assert info["stripe_connect"]["connected"] is False

    def test_apply_offer_no_connection_message(self, admin_session):
        # Ensure demo org is disconnected
        admin_session.post(f"{API}/settings/stripe/disconnect")
        t = requests.post(f"{API}/v1/session/init", json={
            "api_key": DEMO_API_KEY, "external_user_id": "ext_1002",
            "subscription_id": "sub_demo_1002"}).json()["token"]
        requests.post(f"{API}/v1/session/respond", json={
            "token": t, "selected_reason": "Too expensive"})
        r = requests.post(f"{API}/v1/stripe/apply-offer", json={
            "token": t, "action": "accept_discount"})
        assert r.status_code == 200, r.text
        msg = r.json()["stripe"]["message"]
        assert "no Stripe account connected" in msg
