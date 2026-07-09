from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from app.db import create_indexes, close_client
from app.seed import seed
from app.routers import auth_routes, dashboard_routes, session_routes
from app.routers import billing_routes

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("churnguard")

app = FastAPI(title="ChurnGuard API")

health_router = APIRouter(prefix="/api")


@health_router.get("/")
async def root():
    return {"service": "ChurnGuard", "status": "ok"}


@health_router.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(health_router)
app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(session_routes.router)
app.include_router(billing_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    try:
        await create_indexes()
        await seed()
        logger.info("ChurnGuard startup complete: indexes + seed done.")
    except Exception as e:
        logger.exception("Startup error: %s", e)


@app.on_event("shutdown")
async def on_shutdown():
    close_client()
