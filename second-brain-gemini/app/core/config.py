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
    
    # WhatsApp Provider Selection
    whatsapp_provider: str = "twilio"  # Options: 'twilio' or 'meta'
    
    # Twilio Settings (for WhatsApp/SMS)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: Optional[str] = None  # Format: whatsapp:+14155238886
    twilio_whatsapp_to: Optional[str] = None    # Format: whatsapp:+972XXXXXXXXX
    twilio_sms_from: Optional[str] = None       # Format: +14155238886 (regular phone number)
    twilio_sms_to: Optional[str] = None         # Format: +972XXXXXXXXX (regular phone number)
    
    # Meta WhatsApp Cloud API Settings
    whatsapp_cloud_api_token: Optional[str] = None  # Meta WhatsApp API access token
    whatsapp_phone_number_id: Optional[str] = None  # Meta WhatsApp Phone Number ID
    whatsapp_verify_token: Optional[str] = None     # Meta WhatsApp webhook verification token
    
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
print(f"Configured provider: {settings.whatsapp_provider}")
print(f"Twilio configured: {bool(settings.twilio_account_sid and settings.twilio_auth_token)}")
print(f"Meta configured: {bool(settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id)}")
if settings.whatsapp_provider.lower() == 'meta':
    print(f"Meta config details:")
    print(f"  - WHATSAPP_CLOUD_API_TOKEN: {'✅' if settings.whatsapp_cloud_api_token else '❌'}")
    print(f"  - WHATSAPP_PHONE_NUMBER_ID: {'✅' if settings.whatsapp_phone_number_id else '❌'}")
    print(f"  - WHATSAPP_VERIFY_TOKEN: {'✅' if settings.whatsapp_verify_token else '❌'}")
print(f"{'='*60}\n")
