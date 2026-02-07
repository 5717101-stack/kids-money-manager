"""
WhatsApp Provider Interface and Factory
Uses Meta Cloud API as the sole WhatsApp provider.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.core.config import settings


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers."""
    
    @abstractmethod
    def send_whatsapp(self, message: str, to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message.
        
        Args:
            message: Message text to send
            to: Recipient phone number (optional, uses default if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider."""
        pass
    
    @abstractmethod
    def send_audio(self, audio_path: str, caption: str = "", to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an audio file via WhatsApp.
        
        Args:
            audio_path: Path to the audio file to send
            caption: Optional caption/text message to send with the audio
            to: Recipient phone number (optional, uses default if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        pass


class WhatsAppProviderFactory:
    """Factory for creating WhatsApp provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a provider class."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: Optional[str] = None, fallback: bool = True):
        """
        Create a WhatsApp provider instance based on configuration.
        
        Args:
            provider_name: Optional provider name override. Defaults to 'meta'.
            fallback: Unused (kept for backward compatibility).
            
        Returns:
            WhatsAppProvider instance or None if not configured
        """
        if provider_name is None:
            provider_name = 'meta'
        
        print(f"🔍 Creating WhatsApp provider: '{provider_name}'")
        
        if provider_name == 'meta':
            print(f"   Meta config check:")
            print(f"      WHATSAPP_CLOUD_API_TOKEN: {'✅ Set' if settings.whatsapp_cloud_api_token else '❌ Missing'}")
            print(f"      WHATSAPP_PHONE_NUMBER_ID: {'✅ Set' if settings.whatsapp_phone_number_id else '❌ Missing'}")
        
        if provider_name not in cls._providers:
            print(f"⚠️  Unknown WhatsApp provider: {provider_name}")
            print(f"   Available providers: {list(cls._providers.keys())}")
            return None
        
        try:
            provider_class = cls._providers[provider_name]
            instance = provider_class()
            
            if instance.is_configured():
                print(f"✅ WhatsApp provider '{provider_name}' initialized successfully")
                return instance
            else:
                print(f"⚠️  WhatsApp provider '{provider_name}' is not properly configured")
                print(f"   Please check your environment variables for META WhatsApp")
                return None
        except Exception as e:
            print(f"❌ Failed to initialize WhatsApp provider '{provider_name}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider names."""
        return list(cls._providers.keys())


# Register Meta provider
def register_providers():
    """Register available WhatsApp providers."""
    try:
        from app.services.meta_whatsapp_service import MetaWhatsAppService
        WhatsAppProviderFactory.register_provider('meta', MetaWhatsAppService)
        print("✅ Registered Meta WhatsApp provider")
    except ImportError as e:
        print(f"⚠️  Failed to register Meta provider: {e}")


# Auto-register on import
try:
    register_providers()
except Exception as e:
    print(f"⚠️  Error registering providers: {e}")
    import traceback
    traceback.print_exc()
