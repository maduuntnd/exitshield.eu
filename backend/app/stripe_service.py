import stripe
import os
from dotenv import load_dotenv

load_dotenv()


class StripeService:
    def __init__(self):
        # Validate Stripe keys are set
        secret_key = os.getenv("STRIPE_SECRET_KEY")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not secret_key:
            raise ValueError(
                "STRIPE_SECRET_KEY environment variable is not set. "
                "Please add it to your .env file."
            )
        
        if not webhook_secret:
            raise ValueError(
                "STRIPE_WEBHOOK_SECRET environment variable is not set. "
                "Please add it to your .env file."
            )
        
        stripe.api_key = secret_key
        self.webhook_secret = webhook_secret
    
    def create_customer(self, email: str, name: str = None):
        """Create a new Stripe customer."""
        customer_data = {"email": email}
        if name:
            customer_data["name"] = name
        
        customer = stripe.Customer.create(**customer_data)
        return customer
    
    def create_checkout_session(self, customer_id: str, price_id: str, success_url: str, cancel_url: str):
        """Create a Stripe Checkout session."""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{"price": price_id}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session
    
    def create_portal_session(self, customer_id: str, return_url: str):
        """Create a Stripe Customer Portal session."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session
    
    def get_subscription(self, subscription_id: str):
        """Retrieve a subscription by ID."""
        return stripe.Subscription.retrieve(subscription_id)
    
    def cancel_subscription(self, subscription_id: str):
        """Cancel a subscription."""
        return stripe.Subscription.cancel(subscription_id)
    
    def update_subscription(self, subscription_id: str, items: list):
        """Update a subscription's items."""
        return stripe.Subscription.modify(subscription_id, items=items)
    
    def create_coupon(self, coupon_data: dict):
        """Create a coupon."""
        return stripe.Coupon.create(**coupon_data)
    
    def apply_coupon_to_subscription(self, subscription_id: str, coupon_id: str):
        """Apply a coupon to a subscription."""
        return stripe.Subscription.modify(subscription_id, coupon=coupon_id)
    
    def construct_event(self, payload: bytes, sig_header: str):
        """Construct and verify a Stripe webhook event."""
        return stripe.Webhook.construct_event(
            payload, sig_header, self.webhook_secret
        )
        