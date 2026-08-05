<div align="center">

  <img src="./assets/logo.png" alt="ExitShield Logo" width="450" />

  # 🛡️ ExitShield

  **Stop the churn before the cancel.**
  
  An automated, high-converting customer retention portal designed to plug directly into B2B SaaS applications to recover MRR and turn leaving customers into second chances.

  [![License](https://img.shields.io/badge/Under-Licence-10B981.svg)](LICENSE)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
  [![Built with: Gemini (3.6 Flash Extended)](https://www.freewebtools.com/api/badge/Built%20with-Gemini%20(3.6%20Flash%20Extended)-007ec6.svg?style=flat&labelColor=555)](https://gemini.google.com/)
  [![made with: ❤️](https://www.freewebtools.com/api/badge/made%20with-%E2%9D%A4%EF%B8%8F-700000.svg?style=flat&labelColor=555)](https://gemini.google.com/)
  
  [Live Demo](https://demo.exitshield.eu) • [Documentation](#-getting-started) • [Report Bug](https://github.com/maduuntnd/exitshield/issues)

</div>

---

## 📌 Overview

**ExitShield** is a plug-and-play customer retention infrastructure built for modern SaaS companies. Instead of allowing customers to quietly hit a dead-end "Cancel Subscription" button, ChurnGuard intercepts the cancellation flow with a dynamic, survey-driven retention portal powered by Stripe.

By delivering personalized incentives (discounts, subscription pauses, or direct founder calls) at the exact moment of exit, ChurnGuard recovers up to **30%+** of churning revenue completely on autopilot.

---

## ✨ Key Features

- 🎯 **Dynamic Retention Flows:** Automatically presents tailored offers based on the specific reason a customer chooses to leave.
- ⚡ **Seamless Stripe Integration:** Programmatically applies coupons, pauses billing cycles, or processes cancellations directly via the Stripe API.
- 📊 **Real-time Analytics Dashboard:** Track recovered MRR, churn rates, and top exit reasons in a sleek, dark-mode vendor command center.
- 🎨 **High-Converting UX:** Designed with an accessible, distraction-free wizard UI to build trust during critical exit decisions.
- 🔐 **Secure Tokenized Redirects:** Validates API keys and subscription IDs gracefully without exposing sensitive customer data.

---

## ⚙️ How It Works

```mermaid
graph LR
    A[Customer Clicks Cancel] --> B[Redirect to ExitShield]
    B --> C[Exit Survey Questionnaire]
    C --> D[Dynamic Retention Offer]
    D -->|Accepts Offer| E[Stripe Coupon / Pause Applied]
    D -->|Rejects Offer| F[Subscription Canceled at Period End]
