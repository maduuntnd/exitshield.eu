"""Stripe subscription-modification layer.

Uses the real Stripe Python SDK for programmatic subscription mutations:
  - apply a coupon/discount to an active subscription
  - pause a subscription (pause_collection) for 30/60 days
  - cancel a subscription at period end (cancel_at_period_end)

The pre-configured `sk_test_emergent` key is an Emergent checkout proxy and does NOT
authenticate against the raw Stripe API. When the configured key is invalid, or the
target subscription/customer does not exist in the connected Stripe account, we fall
back to a clearly-labelled SIMULATION so the retention flow is fully demonstrable
end-to-end. Supplying a real `sk_test_...` key + real subscription ids enables live
mutations automatically with no code changes.
"""
import os
import logging
import stripe

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", os.environ.get("STRIPE_API_KEY", ""))


def _live_key() -> bool:
    key = os.environ.get("STRIPE_SECRET_KEY", os.environ.get("STRIPE_API_KEY", ""))
    return key.startswith("sk_") and key != "sk_test_emergent"


def create_coupon(percent_off: int, name: str, stripe_account: str = None) -> dict:
    """Create a coupon on the vendor's connected account. Falls back to a simulated id."""
    if _live_key() and stripe_account:
        try:
            coupon = stripe.Coupon.create(
                percent_off=percent_off,
                duration="repeating",
                duration_in_months=2,
                name=name,
                stripe_account=stripe_account,
            )
            return {"stripe_coupon_id": coupon.id, "simulated": False}
        except Exception as e:
            logger.warning("Stripe coupon create failed, simulating: %s", e)
    return {"stripe_coupon_id": f"sim_coupon_{percent_off}off", "simulated": True}


def apply_discount(subscription_id: str, coupon_id: str, stripe_account: str = None) -> dict:
    """Attach a coupon to an active subscription on the vendor's connected account."""
    if _live_key() and subscription_id and stripe_account:
        try:
            stripe.Subscription.modify(subscription_id, coupon=coupon_id, stripe_account=stripe_account)
            return {"ok": True, "simulated": False,
                    "message": "Coupon applied to the live subscription."}
        except Exception as e:
            logger.warning("Stripe apply_discount failed, simulating: %s", e)
    via = f"via connected account {stripe_account}" if stripe_account else "no Stripe account connected"
    return {"ok": True, "simulated": True,
            "message": f"[SIMULATED] Coupon {coupon_id} applied to subscription {subscription_id or 'N/A'} ({via})."}


def pause_subscription(subscription_id: str, days: int, stripe_account: str = None) -> dict:
    """Pause payment collection for a subscription for `days` days."""
    from datetime import datetime, timezone, timedelta
    resume_at = int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())
    if _live_key() and subscription_id and stripe_account:
        try:
            stripe.Subscription.modify(
                subscription_id,
                pause_collection={"behavior": "void", "resumes_at": resume_at},
                stripe_account=stripe_account,
            )
            return {"ok": True, "simulated": False,
                    "message": f"Subscription paused for {days} days."}
        except Exception as e:
            logger.warning("Stripe pause failed, simulating: %s", e)
    via = f"via connected account {stripe_account}" if stripe_account else "no Stripe account connected"
    return {"ok": True, "simulated": True,
            "message": f"[SIMULATED] Subscription {subscription_id or 'N/A'} paused for {days} days ({via})."}


def cancel_at_period_end(subscription_id: str, stripe_account: str = None) -> dict:
    """Schedule cancellation at the end of the current billing period."""
    if _live_key() and subscription_id and stripe_account:
        try:
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=True, stripe_account=stripe_account)
            return {"ok": True, "simulated": False,
                    "message": "Subscription set to cancel at period end."}
        except Exception as e:
            logger.warning("Stripe cancel failed, simulating: %s", e)
    via = f"via connected account {stripe_account}" if stripe_account else "no Stripe account connected"
    return {"ok": True, "simulated": True,
            "message": f"[SIMULATED] Subscription {subscription_id or 'N/A'} will cancel at period end ({via})."}
