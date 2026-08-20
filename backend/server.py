from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

# Import routers
from app.routers import auth_routes, billing_routes, dashboard_routes, session_routes, settings_routes
from app.stripe_service import StripeService
from app.db import init_db

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Required environment variables
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "FRONTEND_URL",
    "BACKEND_URL",
]

def validate_environment():
    """Validate that all required environment variables are set."""
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set these variables in your .env file or environment.\n"
            f"See .env.example for reference."
        )
        print(f"ERROR: {error_msg}", file=sys.stderr)
        sys.exit(1)
    
    print("✓ All required environment variables are set")


# Validate environment on startup
validate_environment()

# Initialize Stripe service after validation
stripe_service = StripeService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("✓ Database initialized")
    yield
    # Shutdown
    print("✓ Application shutdown")


app = FastAPI(
    title="ExitShield API",
    description="B2B SaaS Retention System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(billing_routes.router, prefix="/api/billing", tags=["Billing"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(session_routes.router, prefix="/api/session", tags=["Session"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])


@app.get("/")
async def root():
    return {"message": "ExitShield API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "exitshield-api"}