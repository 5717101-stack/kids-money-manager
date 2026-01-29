"""
Daily Sync - AI Life Coach Backend
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_mongodb
from app.routers import ingest, digest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting Daily Sync API...")
    await init_mongodb()
    print("✅ Database initialized")
    print(f"📊 ChromaDB path: {settings.chroma_db_path}")
    print(f"💾 MongoDB database: {settings.mongodb_db_name}")
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
import os
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins != "*":
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML page) - MUST be before routers
import os
from pathlib import Path

# Get the directory where main.py is located
base_dir = Path(__file__).parent
static_dir = base_dir / "static"

# Mount static files BEFORE other routes
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    print(f"✅ Static files mounted from: {static_dir}")
else:
    print(f"⚠️  Static directory not found: {static_dir}")

# Include routers (after static mount)
app.include_router(ingest.router)
app.include_router(digest.router)


@app.get("/")
async def root():
    """Root endpoint - serves the web interface."""
    from fastapi.responses import FileResponse
    
    html_path = base_dir / "static" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    
    return {
        "message": "Daily Sync - AI Life Coach API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "web_interface": "/static/index.html"
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
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=settings.debug
    )
