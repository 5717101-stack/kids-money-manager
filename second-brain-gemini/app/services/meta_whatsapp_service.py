"""
Meta WhatsApp Cloud API service for sending WhatsApp messages.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
import requests
from app.core.config import settings

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from app.services.whatsapp_provider import WhatsAppProvider


class MetaWhatsAppService:
    """Service for sending WhatsApp messages via Meta WhatsApp Cloud API."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self):
        """Initialize Meta WhatsApp service."""
        self.is_configured_flag = False
        self.phone_number_id = None
        self.access_token = None
        
        if settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id:
            try:
                self.access_token = settings.whatsapp_cloud_api_token
                self.phone_number_id = settings.whatsapp_phone_number_id
                self.is_configured_flag = True
                print("✅ Meta WhatsApp Cloud API initialized successfully")
            except Exception as e:
                print(f"⚠️  Failed to initialize Meta WhatsApp: {e}")
        else:
            print("⚠️  Meta WhatsApp not configured - WhatsApp messages will not be sent")
            if not settings.whatsapp_cloud_api_token:
                print("   Missing: WHATSAPP_CLOUD_API_TOKEN")
            if not settings.whatsapp_phone_number_id:
                print("   Missing: WHATSAPP_PHONE_NUMBER_ID")
    
    def is_configured(self) -> bool:
        """Check if Meta WhatsApp is properly configured."""
        return self.is_configured_flag
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "meta"
    
    def send_whatsapp(self, message: str, to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Meta WhatsApp Cloud API.
        
        Args:
            message: The message to send
            to: Recipient phone number in E.164 format (e.g., +972XXXXXXXXX)
                If not provided, will need to be configured separately
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Meta WhatsApp not configured",
                "message": "Meta WhatsApp credentials not set"
            }
        
        if not to:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided for Meta WhatsApp"
            }
        
        # Ensure phone number is in E.164 format (remove whatsapp: prefix if present)
        recipient = to.replace("whatsapp:", "") if to.startswith("whatsapp:") else to
        
        try:
            url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            print(f"\n{'='*60}")
            print(f"📱 [MetaWhatsAppService] Sending WhatsApp message via Meta API to {recipient}...")
            print(f"   ✅ USING META WHATSAPP CLOUD API")
            print(f"{'='*60}\n")
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result_data = response.json()
            
            print(f"✅ WhatsApp message sent successfully via Meta API!")
            print(f"   Message ID: {result_data.get('messages', [{}])[0].get('id', 'N/A')}")
            
            return {
                "success": True,
                "message_id": result_data.get('messages', [{}])[0].get('id'),
                "status": "sent",
                "message": "WhatsApp message sent successfully via Meta API"
            }
            
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_response = e.response.json()
                error_detail = error_response.get('error', {}).get('message', str(e))
            except:
                error_detail = str(e)
            
            print(f"❌ Meta WhatsApp API error: {error_detail}")
            return {
                "success": False,
                "error": error_detail,
                "code": e.response.status_code if hasattr(e, 'response') else None,
                "message": f"Failed to send WhatsApp via Meta API: {error_detail}"
            }
        except Exception as e:
            print(f"❌ Unexpected error sending WhatsApp via Meta API: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Unexpected error sending WhatsApp via Meta API"
            }
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook for Meta WhatsApp Cloud API.
        
        Args:
            mode: Verification mode from query params
            token: Verification token from query params
            challenge: Challenge string from query params
            
        Returns:
            Challenge string if verification succeeds, None otherwise
        """
        if mode == "subscribe" and token == settings.whatsapp_verify_token:
            print("✅ Meta WhatsApp webhook verified successfully")
            return challenge
        else:
            print("⚠️  Meta WhatsApp webhook verification failed")
            return None


# Singleton instance
meta_whatsapp_service = MetaWhatsAppService()
