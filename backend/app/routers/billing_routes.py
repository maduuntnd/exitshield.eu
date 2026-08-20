from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import stripe
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

router = APIRouter()

# Get webhook secret from environment
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_WEBHOOK_SECRET:
    raise ValueError(
        "STRIPE_WEBHOOK_SECRET environment variable is not set. "
        "Please add it to your .env file."
    )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    IMPORTANT: Always verifies signature - no bypass for development!
    Use Stripe CLI for local webhook testing:
    stripe listen --forward-to localhost:8000/api/billing/webhook
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # ALWAYS verify signature - security critical!
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payload: {str(e)}"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature - potential security threat
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signature: {str(e)}"
        )
    
    # Extract event data
    event_type = event["type"]
    event_data = event["data"]["object"]
    
    # Log the event for debugging
    print(f"✓ Received Stripe webhook: {event_type}")
    
    # Handle different event types
    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event_data)
        
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_data)
        
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_data)
        
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event_data)
        
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data)
        
        else:
            print(f"ℹ️ Unhandled event type: {event_type}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "event_type": event_type}
        )
    
    except Exception as e:
        # Log error but return 200 to prevent Stripe retries
        print(f"❌ Error processing webhook {event_type}: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={"received": True, "error": str(e)}
        )


async def handle_checkout_completed(session_data: dict):
    """Handle successful checkout session completion."""
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")
    metadata = session_data.get("metadata", {})
    
    print(f"✓ Checkout completed:")
    print(f"  - Customer: {customer_id}")
    print(f"  - Subscription: {subscription_id}")
    print(f"  - Metadata: {metadata}")
    
    # TODO: Update database with subscription info
    # - Mark user as premium
    # - Store subscription ID
    # - Set renewal date


async def handle_subscription_updated(subscription_data: dict):
    """Handle subscription updates (plan changes, cancellations, etc.)."""
    subscription_id = subscription_data.get("id")
    customer_id = subscription_data.get("customer")
    status = subscription_data.get("status")
    
    print(f"✓ Subscription updated:")
    print(f"  - Subscription: {subscription_id}")
    print(f"  - Customer: {customer_id}")
    print(f"  - Status: {status}")
    
    # TODO: Update database
    # - Update subscription status
    # - Handle plan changes


async def handle_subscription_deleted(subscription_data: dict):
    """Handle subscription cancellation/deletion."""
    subscription_id = subscription_data.get("id")
    customer_id = subscription_data.get("customer")
    
    print(f"✓ Subscription deleted:")
    print(f"  - Subscription: {subscription_id}")
    print(f"  - Customer: {customer_id}")
    
    # TODO: Update database
    # - Mark user as free tier
    # - Remove subscription


async def handle_payment_succeeded(invoice_data: dict):
    """Handle successful payment."""
    customer_id = invoice_data.get("customer")
    amount_paid = invoice_data.get("amount_paid")
    currency = invoice_data.get("currency")
    
    print(f"✓ Payment succeeded:")
    print(f"  - Customer: {customer_id}")
    print(f"  - Amount: {amount_paid} {currency.upper()}")
    
    # TODO: Update database
    # - Log payment
    # - Extend subscription if needed


async def handle_payment_failed(invoice_data: dict):
    """Handle failed payment."""
    customer_id = invoice_data.get("customer")
    amount_due = invoice_data.get("amount_due")
    
    print(f"⚠️ Payment failed:")
    print(f"  - Customer: {customer_id}")
    print(f"  - Amount: {amount_due}")
    
    # TODO: Update database
    # - Flag account
    # - Send notification email
    # - Start dunning process


@router.get("/webhook-test")
async def webhook_test():
    """
    Test endpoint to verify webhook route is working.
    This is NOT for Stripe - just for debugging.
    """
    return {
        "status": "webhook endpoint is running",
        "timestamp": datetime.utcnow().isoformat()
    }
