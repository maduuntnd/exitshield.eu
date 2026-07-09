# ChurnGuard Auth Testing

## Auth methods
1. JWT email/password (cookies: access_token, refresh_token) + Bearer fallback.
2. Emergent Google OAuth (cookie: session_token). Backend exchange at POST /api/auth/google/session.

## Credentials (JWT)
- Email: demo@churnguard.io
- Password: ChurnGuard2026!
- This user is admin and owns the demo org "Acme Analytics".

## API checks
curl -c cookies.txt -X POST {BASE}/api/auth/login -H "Content-Type: application/json" -d '{"email":"demo@churnguard.io","password":"ChurnGuard2026!"}'
curl -b cookies.txt {BASE}/api/auth/me
curl -b cookies.txt {BASE}/api/dashboard/kpis
curl -b cookies.txt {BASE}/api/offers

## Public cancellation flow (no auth)
Demo API key: cg_live_demo_9f3a7c21b8e4
POST {BASE}/api/v1/session/init  {api_key, external_user_id: "ext_1001", subscription_id: "sub_demo_1001"}
POST {BASE}/api/v1/session/respond  {token, selected_reason: "Too expensive"}
POST {BASE}/api/v1/stripe/apply-offer  {token, action: "accept_discount" | "accept_pause" | "cancel"}

## Google session simulation (for gated UI browser tests)
mongosh --eval "
use('test_database');
var userId='test-user-'+Date.now();
var st='test_session_'+Date.now();
db.users.insertOne({user_id:userId,email:'g'+Date.now()+'@example.com',name:'G Tester',role:'vendor',auth_provider:'google',org_id:null,created_at:new Date()});
db.user_sessions.insertOne({user_id:userId,session_token:st,expires_at:new Date(Date.now()+7*864e5),created_at:new Date()});
print('session_token: '+st);
"
Set cookie session_token (secure, sameSite None) then visit /dashboard.
NOTE: Google test users have no org_id, so dashboard KPI calls 400. Prefer JWT admin (demo@churnguard.io) for gated-page tests since it owns the seeded org with data.

## Billing & Stripe (LIVE mode) — updated
- Billing now uses the REAL Stripe SDK with LIVE keys. Vendor plans are real recurring subscriptions via Stripe Checkout (subscription mode, trial_period_days=14).
- Endpoints: /api/billing/plans, /api/billing/subscription, /api/billing/checkout (returns cs_live_ url), /api/billing/checkout/status/{id}, /api/billing/change-plan, /api/billing/cancel, /api/stripe/webhook (sig-verified, idempotent).
- Connect (real OAuth): POST /api/settings/stripe/connect -> {mode:'oauth', url}; GET /api/settings/stripe/connect/callback; POST /api/settings/stripe/disconnect.
- DO NOT complete a real checkout (collects a real card) or complete Connect OAuth in automated tests. Only verify session/url creation and non-erroring endpoints.
- Demo org is seeded trialing (display only, no real Stripe subscription) so it is never charged.
