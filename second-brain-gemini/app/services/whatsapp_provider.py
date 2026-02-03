"""
WhatsApp Provider Interface and Factory
Supports multiple WhatsApp providers (Twilio, Meta Cloud API)
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


class WhatsAppProviderFactory:
    """Factory for creating WhatsApp provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a provider class."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: Optional[str] = None, fallback: bool = True) -> Optional[WhatsAppProvider]:
        """
        Create a WhatsApp provider instance based on configuration.
        
        Args:
            provider_name: Optional provider name override. If None, uses settings.whatsapp_provider
            fallback: If True, try to fallback to 'twilio' if requested provider is not configured
            
        Returns:
            WhatsAppProvider instance or None if provider not found/configured
        """
        if provider_name is None:
            provider_name = settings.whatsapp_provider.lower()
        
        print(f"🔍 Attempting to create WhatsApp provider: '{provider_name}'")
        print(f"   Config value: '{settings.whatsapp_provider}'")
        print(f"   Available providers: {list(cls._providers.keys())}")
        
        # Debug: Check Meta configuration if requested
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
                print(f"   Please check your environment variables for {provider_name.upper()}")
                
                # Only fallback if explicitly requested provider is not available AND fallback is enabled
                # But don't fallback silently - log it clearly
                if fallback and provider_name != 'twilio' and 'twilio' in cls._providers:
                    twilio_instance = cls._providers['twilio']()
                    if twilio_instance.is_configured():
                        print(f"⚠️  WARNING: Falling back to 'twilio' provider because '{provider_name}' is not configured")
                        print(f"   To use '{provider_name}', please configure the required environment variables")
                        return twilio_instance
                    else:
                        print(f"⚠️  Cannot fallback to 'twilio' - it's also not configured")
                
                return None
        except Exception as e:
            print(f"❌ Failed to initialize WhatsApp provider '{provider_name}': {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to Twilio on error
            if fallback and provider_name != 'twilio' and 'twilio' in cls._providers:
                print(f"🔄 Attempting fallback to 'twilio' provider after error...")
                return cls.create_provider('twilio', fallback=False)
            
            return None
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider names."""
        return list(cls._providers.keys())


# Import providers to register them
def register_providers():
    """Register all available WhatsApp providers."""
    from app.services.twilio_service import TwilioService
    
    # Register Twilio provider
    WhatsAppProviderFactory.register_provider('twilio', TwilioService)
    
    # Register Meta provider (will be created next)
    try:
        from app.services.meta_whatsapp_service import MetaWhatsAppService
        WhatsAppProviderFactory.register_provider('meta', MetaWhatsAppService)
    except ImportError:
        # Meta service not yet implemented, that's okay
        pass


# Auto-register providers when module is imported
register_providers()
