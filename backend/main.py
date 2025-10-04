"""
Main FastAPI application for Wink retail analytics platform.
Simple production deployment with environment-based camera processor toggle.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment configuration
DISABLE_CAMERA_PROCESSORS = os.getenv("DISABLE_CAMERA_PROCESSORS", "true").lower() == "true"

# Import routes
from src.routes.auth_routes import router as auth_router
from src.routes.ingest_routes import router as ingest_router
from src.routes.camera_routes import router as camera_router
from src.routes.analytics_routes import router as analytics_router
from src.routes.insights_routes import router as insights_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Wink Analytics API...")

    if DISABLE_CAMERA_PROCESSORS:
        logger.info("Camera processors DISABLED (cloud deployment mode)")
    else:
        logger.info("Camera processors ENABLED (edge deployment mode)")
        # Here you would start camera processors if needed

    yield

    logger.info("Shutting down Wink Analytics API...")


# Create FastAPI app
app = FastAPI(
    title="Wink Analytics API",
    description="Production retail analytics with edge ingestion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(camera_router)
app.include_router(analytics_router)
app.include_router(insights_router)


# Health check
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Wink Analytics API",
        "version": "1.0.0",
        "status": "running",
        "camera_processors": "disabled" if DISABLE_CAMERA_PROCESSORS else "enabled"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from src.database.connection import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
