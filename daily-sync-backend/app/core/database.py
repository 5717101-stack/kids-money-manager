"""
Database setup and utilities for SQLite and ChromaDB.
"""

import aiosqlite
import chromadb
from pathlib import Path
from typing import Optional
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


# SQLite Database
def get_db_path():
    """Get the database path, creating directories if needed."""
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


async def init_sqlite_db():
    """Initialize SQLite database with required tables."""
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        # Create ingestion logs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                data_type TEXT NOT NULL,
                content_hash TEXT,
                raw_content TEXT,
                processed_content TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create daily digests table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                summary TEXT,
                leadership_insights TEXT,
                strategy_insights TEXT,
                parenting_insights TEXT,
                action_items TEXT,
                full_digest TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create agent responses table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_id INTEGER,
                agent_type TEXT NOT NULL,
                input_content TEXT,
                response TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (digest_id) REFERENCES daily_digests(id)
            )
        """)
        
        await db.commit()


# ChromaDB Vector Store
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
