"""
FastAPI application entry point for the investment research agent.

Run with: uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import CORS_ORIGINS, validate_config
from app.db.database import init_db

# Configure logging -- structured logging would be better for prod,
# but basic logging is fine for a local MVP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Investment Research Agent",
    description="AI-powered first-pass investment memo generator",
    version="0.1.0",
)

# CORS -- allow Next.js frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Initialize database and validate config on startup."""
    logger.info("Starting Investment Research Agent API...")

    # Validate configuration
    warnings = validate_config()
    for warning in warnings:
        logger.warning(warning)

    # Initialize database
    init_db()
    logger.info("Database initialized.")

    logger.info("API ready. Docs at http://localhost:8000/docs")
