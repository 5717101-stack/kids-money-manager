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
    port: int = 8000
    debug: bool = False
    
    # LLM Provider Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: str = "openai"  # "openai" or "anthropic"
    default_model: str = "gpt-4o"  # or "claude-3-5-sonnet-20241022"
    
    # Database Settings
    sqlite_db_path: str = "data/sqlite/daily_sync.db"
    chroma_db_path: str = "data/chroma"
    
    # Whisper Settings
    whisper_model: str = "base"  # tiny, base, small, medium, large
    
    # Vector Store Settings
    embedding_model: str = "text-embedding-3-small"  # OpenAI embedding model
    collection_name: str = "daily_sync_memories"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
