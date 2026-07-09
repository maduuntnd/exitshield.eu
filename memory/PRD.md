# ChurnGuard — PRD

## Original Problem Statement
Build "ChurnGuard", a high-ticket B2B SaaS customer retention portal that plugs into other SaaS apps to stop users from canceling. External apps redirect canceling users to `/cancel?user_id=X&subscription_id=Y&api_key=Z`. ChurnGuard presents a high-converting cancellation wizard and dynamically offers a retention incentive: apply Stripe discount coupon, pause subscription (30/60 days), or cancel at period end. Vendor Dashboard with KPIs, Offer Manager CRUD, and Analytics. Public end-user wizard (reason -> dynamic offer -> success/goodbye).

## User Choices
- Database: MongoDB
- Payments: pre-configured Stripe test key (proxy `sk_test_emergent`)
- Auth: Emergent Google social login + JWT email/password
- Seed demo data: yes
- Design: Vendor dashboard dark mode emerald (#10B981 on #0B0F19); public wizard clean light mode (#F9FAFB / #111827); smooth transitions.

## Architecture
- Backend: FastAPI (modular `app/` package: db, models, auth, stripe_service, seed, routers/{auth,dashboard,session}). MongoDB via motor. All routes `/api` prefixed.
- Frontend: React 19 + react-router 7, framer-motion, recharts, sonner. Dual-theme (dark dashboard, light portal, marketing landing).
- Auth: JWT (bcrypt, access+refresh httpOnly cookies, brute-force lockout) + Emergent Google OAuth (session_token). Unified `users` collection (user_id UUID), each vendor owns an org.
- Stripe: real SDK methods (Coupon.create, Subscription.modify with coupon/pause_collection/cancel_at_period_end) with labeled SIMULATION fallback because the proxy key can't mutate real subscriptions.

## Collections
organizations, customers, cancellation_flows, retention_offers, cancel_sessions, users, user_sessions, login_attempts, password_reset_tokens.

## Implemented (2026-07-09)
- MVP complete, 100% backend + frontend tests passing.
- Marketing landing page (dark emerald).
- Vendor auth: JWT login/register + Google OAuth. Admin seeded (demo@churnguard.io / ChurnGuard2026!).
- Vendor Dashboard: KPI cards (Churn Saved %, MRR Recovered, MRR Lost, Sessions), MRR trend area chart, outcome breakdown, Top Cancellation Reasons bar chart, integration URL + API key copy.
- Offer Manager: full CRUD, inline active toggle, reason-triggered offers.
- Analytics: sessions table with All/Saved/Canceled filters.
- Public cancellation wizard: 3-step, reason-matched dynamic offer, discount/pause/cancel outcomes, animated transitions, split-screen calm visual.
- Public APIs: /api/v1/session/init, /respond, /stripe/apply-offer.
- Seed: org "Acme Analytics" (api_key cg_live_demo_9f3a7c21b8e4), 5 customers, 4 offers, 40 historical sessions.

## Backlog
- P1: Custom cancellation-flow builder UI (edit steps_json/questions from dashboard).
- P1: Configurable vendor `return_url` to redirect user back to the vendor app after cancel.
- P2: Real Stripe live mode (swap in real sk_test_ key + create real customers/subscriptions on seed).
- P2: Password reset email delivery (currently logs token to console) via Resend/SendGrid.
- P2: Multi-user orgs / team roles; webhook receiver for Stripe subscription events.
- P2: A/B testing of offers, per-offer conversion analytics.

## Next Tasks
1. Flow builder UI for custom survey questions.
2. Vendor settings page (return_url, branding).
3. Optional: wire a real Stripe test key for live mutations.

## Monetization / Vendor Billing (added 2026-07-09)
- Three flat monthly tiers: Starter $49 (250 sessions/mo, 3 offers, 1 seat), Growth $99 (1,500 sessions, 15 offers, badge removal, advanced analytics, 3 seats), Scale $149 (10k sessions, ~unlimited offers, custom branding, API, 10 seats).
- 14-day free trial (default Growth) auto-created for every org; in-app lifecycle engine (`app/billing.py evaluate_lifecycle`) handles trialing → active (auto-charge) → past_due (grace 2d) → suspended, plus renewals and cancel_at_period_end.
- Soft-limit (nudge banner) then hard-limit (offer creation blocked, HTTP 402) after grace / on suspension.
- Real Emergent Stripe checkout (`emergentintegrations`) for the pay/add-payment-method step (creates `payment_transactions`, status polling + idempotent webhook `/api/webhook/stripe`).
- Frontend: public `/pricing`, dashboard `/dashboard/billing` (current plan, trial countdown, usage bars, plan upgrade/downgrade, cancel), dashboard-wide BillingBanner.
- SIMULATED: recurring auto-charge & renewals + saved cards (sk_test_emergent proxy can't do subscription mode). Swap a real Stripe key + subscription-mode prices to go fully live.
- Tests: 28/28 backend (test_churnguard.py + test_billing.py), frontend 100%.
