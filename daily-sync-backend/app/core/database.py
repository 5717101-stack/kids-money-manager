"""
Database setup and utilities for MongoDB and ChromaDB.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import chromadb
from pathlib import Path
from typing import Optional
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


# MongoDB Database
_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db = None


async def get_mongo_client() -> AsyncIOMotorClient:
    """Get or create MongoDB client."""
    global _mongo_client
    if _mongo_client is None:
        if not settings.mongodb_uri:
            raise ValueError(
                "MONGODB_URI not set. Please set MONGODB_URI in .env file or environment variables."
            )
        _mongo_client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )
    return _mongo_client


async def get_mongo_db():
    """Get MongoDB database instance."""
    global _mongo_db
    if _mongo_db is None:
        client = await get_mongo_client()
        _mongo_db = client[settings.mongodb_db_name]
    return _mongo_db


async def init_mongodb():
    """Initialize MongoDB database with required collections and indexes."""
    try:
        db = await get_mongo_db()
        
        # Create collections if they don't exist (MongoDB creates them automatically on first insert)
        # But we'll create indexes for better performance
        
        # Ingestion logs collection
        ingestion_logs = db.ingestion_logs
        await ingestion_logs.create_index("timestamp")
        await ingestion_logs.create_index("content_hash")
        await ingestion_logs.create_index("data_type")
        await ingestion_logs.create_index([("timestamp", 1), ("data_type", 1)])
        
        # Daily digests collection
        daily_digests = db.daily_digests
        await daily_digests.create_index("date", unique=True)
        await daily_digests.create_index("created_at")
        
        # Agent responses collection
        agent_responses = db.agent_responses
        await agent_responses.create_index("digest_id")
        await agent_responses.create_index("agent_type")
        await agent_responses.create_index([("digest_id", 1), ("agent_type", 1)])
        await agent_responses.create_index("created_at")
        
        # Test connection
        await db.command("ping")
        print("✅ MongoDB connected and initialized")
        
    except ConnectionFailure as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")
    except Exception as e:
        print(f"⚠️  MongoDB initialization warning: {str(e)}")
        # Don't fail if indexes already exist


# ChromaDB Vector Store (kept for vector embeddings)
_chroma_client: Optional[chromadb.ClientAPI] = None
_chroma_collection: Optional[chromadb.Collection] = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        db_path = Path(settings.chroma_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    return _chroma_client


def get_chroma_collection() -> chromadb.Collection:
    """Get or create ChromaDB collection for storing embeddings."""
    global _chroma_collection
    if _chroma_collection is None:
        client = get_chroma_client()
        try:
            _chroma_collection = client.get_collection(name=settings.collection_name)
        except Exception:
            _chroma_collection = client.create_collection(name=settings.collection_name)
    return _chroma_collection


# Backward compatibility - keep old function names but use MongoDB
async def init_sqlite_db():
    """Initialize database (now using MongoDB). Kept for backward compatibility."""
    await init_mongodb()


def get_db_path():
    """Get database path (deprecated - now using MongoDB). Kept for backward compatibility."""
    return None
