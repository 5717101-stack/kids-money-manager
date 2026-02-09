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
    gemini_model: str = "gemini-2.5-pro"  # NOTE: Actual model selection goes through MODEL_MAPPING in model_discovery.py
    
    # WhatsApp Provider Selection
    whatsapp_provider: str = "meta"  # Meta Cloud API
    
    # Meta WhatsApp Cloud API Settings
    whatsapp_cloud_api_token: Optional[str] = None  # Meta WhatsApp API access token
    whatsapp_phone_number_id: Optional[str] = None  # Meta WhatsApp Phone Number ID
    whatsapp_verify_token: Optional[str] = None     # Meta WhatsApp webhook verification token
    whatsapp_from: Optional[str] = None              # Meta WhatsApp sender number (E.164 format: +972XXXXXXXXX) - optional, Phone Number ID is used by default
    whatsapp_to: Optional[str] = None               # Meta WhatsApp recipient number (E.164 format: +972XXXXXXXXX)
    whatsapp_app_id: Optional[str] = None            # Meta App ID (for token refresh)
    whatsapp_app_secret: Optional[str] = None        # Meta App Secret (for token refresh)
    
    # Google Drive Memory Settings
    drive_memory_folder_id: Optional[str] = None     # Google Drive folder ID for storing memory file
    
    # Knowledge Base (Personal Context from Google Drive)
    context_folder_id: Optional[str] = None          # Google Drive folder ID for Second_Brain_Context
    
    # Voice Signature Settings (Legacy — Gemini multimodal approach)
    max_voice_signatures: int = 2  # Max signatures to download (0 = disable multimodal, reduces memory usage)
    enable_multimodal_voice: bool = True  # Enable multimodal voice comparison (set False on low-memory hosts)
    
    # pyannote Speaker Diarization & Identification
    huggingface_token: Optional[str] = None  # HuggingFace token for pyannote gated models
    pyannote_auto_threshold: float = 0.80  # Auto-identify speaker if cosine similarity >= this
    pyannote_suggest_threshold: float = 0.65  # Suggest match if similarity >= this (but < auto)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()

# Debug: Print WhatsApp provider configuration on startup
print(f"\n{'='*60}")
print(f"📱 WhatsApp Provider Configuration")
print(f"{'='*60}")
print(f"Provider: Meta Cloud API")
print(f"Meta configured: {bool(settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id)}")
print(f"  - WHATSAPP_CLOUD_API_TOKEN: {'✅' if settings.whatsapp_cloud_api_token else '❌'}")
print(f"  - WHATSAPP_PHONE_NUMBER_ID: {'✅' if settings.whatsapp_phone_number_id else '❌'}")
print(f"  - WHATSAPP_VERIFY_TOKEN: {'✅' if settings.whatsapp_verify_token else '❌'}")
print(f"{'='*60}\n")
