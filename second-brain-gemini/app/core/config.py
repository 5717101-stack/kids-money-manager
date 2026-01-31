"""
Configuration settings for Second Brain - Gemini Edition.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    api_title: str = "Second Brain - Daily Sync (Gemini Edition)"
    api_version: str = "1.0.0"
    api_description: str = "AI-powered daily analysis using Google Gemini 1.5 Pro"
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Google Gemini Settings
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro-latest"
    
    # Twilio Settings (for WhatsApp/SMS)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: Optional[str] = None  # Format: whatsapp:+14155238886
    twilio_whatsapp_to: Optional[str] = None    # Format: whatsapp:+972XXXXXXXXX
    twilio_sms_from: Optional[str] = None       # Format: +14155238886 (regular phone number)
    twilio_sms_to: Optional[str] = None         # Format: +972XXXXXXXXX (regular phone number)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
