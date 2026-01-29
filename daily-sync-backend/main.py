"""
Daily Sync - AI Life Coach Backend
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_sqlite_db
from app.routers import ingest, digest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting Daily Sync API...")
    await init_sqlite_db()
    print("✅ Database initialized")
    print(f"📊 ChromaDB path: {settings.chroma_db_path}")
    print(f"💾 SQLite path: {settings.sqlite_db_path}")
    yield
    # Shutdown
    print("👋 Shutting down Daily Sync API...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
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
app.include_router(ingest.router)
app.include_router(digest.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Daily Sync - AI Life Coach API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "daily-sync-api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
