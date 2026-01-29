"""
Configuration settings for the Daily Sync application.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    api_title: str = "Daily Sync - AI Life Coach API"
    api_version: str = "1.0.0"
    api_description: str = "AI-powered personal coach for daily insights and actionable advice"
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000  # Will be overridden by PORT env var in main.py
    debug: bool = False
    
    # LLM Provider Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: str = "openai"  # "openai" or "anthropic"
    default_model: str = "gpt-4o"  # or "claude-3-5-sonnet-20241022"
    
    # Database Settings
    mongodb_uri: Optional[str] = None  # MongoDB connection string (from MONGODB_URI env var)
    mongodb_db_name: str = "daily_sync"  # MongoDB database name
    chroma_db_path: str = "data/chroma"  # ChromaDB for vector storage (local file system)
    
    # Backward compatibility - map MONGODB_URI env var
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map MONGODB_URI env var if not set
        if not self.mongodb_uri:
            import os
            self.mongodb_uri = os.getenv("MONGODB_URI")
    
    # Whisper Settings
    whisper_model: str = "base"  # tiny, base, small, medium, large (for local Whisper)
    use_whisper_api: bool = True  # Use OpenAI Whisper API instead of local (supports MP3 directly, no ffmpeg needed)
    
    # Vector Store Settings
    embedding_model: str = "text-embedding-3-small"  # OpenAI embedding model
    collection_name: str = "daily_sync_memories"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields for backward compatibility
        extra = "ignore"


settings = Settings()
