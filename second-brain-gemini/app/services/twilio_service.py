"""
Twilio service for sending WhatsApp and SMS messages.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from app.services.whatsapp_provider import WhatsAppProvider


class TwilioService:
    """Service for sending WhatsApp and SMS messages via Twilio."""
    
    def __init__(self):
        """Initialize Twilio service."""
        self.client = None
        self.is_configured_flag = False
        
        if settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                self.client = Client(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token
                )
                self.is_configured_flag = True
                print("✅ Twilio client initialized successfully")
            except Exception as e:
                print(f"⚠️  Failed to initialize Twilio client: {e}")
        else:
            print("⚠️  Twilio not configured - WhatsApp messages will not be sent")
            if not settings.twilio_account_sid:
                print("   Missing: TWILIO_ACCOUNT_SID")
            if not settings.twilio_auth_token:
                print("   Missing: TWILIO_AUTH_TOKEN")
    
def format_summary_message(self, analysis_data: Dict[str, Any]) -> str:
        """
        Format analysis data into a concise WhatsApp/SMS message.
        
        Args:
            analysis_data: The analysis result from Gemini
        
        Returns:
            Formatted message string (limited to MAX_MESSAGE_LENGTH)
        """
        MAX_MESSAGE_LENGTH = 1500
        
        summary = analysis_data.get('summary', '')
        action_items = analysis_data.get('action_items', [])
        insights = analysis_data.get('insights', [])
        leadership_feedback = analysis_data.get('leadership_feedback', '')
        
        message_parts = []
        
        if summary:
            message_parts.append(f"📊 סיכום:\n{summary}")
        
        if action_items:
            message_parts.append(f"\n✅ משימות:\n" + "\n".join([f"• {item}" for item in action_items[:3]]))
            if len(action_items) > 3:
                message_parts.append(f"... ועוד {len(action_items) - 3} משימות")
        
        if insights:
            message_parts.append(f"\n💡 תובנות:\n" + "\n".join([f"• {insight}" for insight in insights[:2]]))
        
        if leadership_feedback:
            message_parts.append(f"\n👔 משוב מנהיגות:\n{leadership_feedback[:200]}")
        
        message = "\n".join(message_parts)
        
        # Truncate if too long
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH - 50] + "\n... (הודעה קוצרה)"
            message += f"\n\n📥 להורדת PDF מלא: [קישור]"
        
        return message
    
    def send_whatsapp(self, message: str, to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio.
        
        Args:
            message: The message to send
            to: Recipient phone number (optional, uses default if not provided)
        
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Twilio not configured",
                "message": "Twilio credentials not set"
            }
        
        # Use provided 'to' or fallback to config default
        recipient = to or settings.twilio_whatsapp_to
        if not recipient:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided. Set TWILIO_WHATSAPP_TO environment variable or provide 'to' parameter."
            }
        
        try:
            print(f"\n{'='*60}")
            print(f"📱 [TwilioService] Sending WhatsApp message to {recipient}...")
            print(f"   ⚠️  USING TWILIO PROVIDER (not Meta)")
            print(f"   This means either:")
            print(f"   1. WHATSAPP_PROVIDER is set to 'twilio'")
            print(f"   2. Meta is not configured and fallback to Twilio occurred")
            print(f"{'='*60}\n")
            
            message_obj = self.client.messages.create(
                body=message,
                from_=settings.twilio_whatsapp_from,
                to=recipient
            )
            
            print(f"✅ WhatsApp message sent successfully!")
            print(f"   SID: {message_obj.sid}")
            print(f"   Status: {message_obj.status}")
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status,
                "message": "WhatsApp message sent successfully"
            }
            
        except TwilioRestException as e:
            print(f"❌ Twilio error: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": e.code,
                "message": f"Failed to send WhatsApp: {e.msg}"
            }
        except Exception as e:
            print(f"❌ Unexpected error sending WhatsApp: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Unexpected error sending WhatsApp"
            }
    
    def send_sms(self, message: str, to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an SMS message via Twilio.
        
        Args:
            message: The message to send
            to: Recipient phone number (optional, uses default if not provided)
        
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Twilio not configured",
                "message": "Twilio credentials not set"
            }
        
        # Use provided 'to' or fallback to config default
        recipient = to or settings.twilio_sms_to
        if not recipient:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided. Set TWILIO_SMS_TO environment variable or provide 'to' parameter."
            }
        
        try:
            print(f"\n{'='*60}")
            print(f"📱 [TwilioService] Sending SMS to {recipient}...")
            print(f"{'='*60}\n")
            
            message_obj = self.client.messages.create(
                body=message,
                from_=settings.twilio_sms_from,
                to=recipient
            )
            
            print(f"✅ SMS sent successfully!")
            print(f"   SID: {message_obj.sid}")
            print(f"   Status: {message_obj.status}")
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status,
                "message": "SMS sent successfully"
            }
            
        except TwilioRestException as e:
            print(f"❌ Twilio error: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": e.code,
                "message": f"Failed to send SMS: {e.msg}"
            }
        except Exception as e:
            print(f"❌ Unexpected error sending SMS: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Unexpected error sending SMS"
            }
    
    def send_summary(self, analysis_data: Dict[str, Any], to: Optional[str] = None, channel: str = "whatsapp") -> Dict[str, Any]:
        """
        Send analysis summary as a WhatsApp or SMS message.
        
        Args:
            analysis_data: The analysis result from Gemini
            to: Recipient phone number (optional)
            channel: "whatsapp" or "sms"
        
        Returns:
            Dictionary with success status
        """
        message = self.format_summary_message(analysis_data)
        
        if channel == "sms":
            return self.send_sms(message, to)
        
        return self.send_whatsapp(message, to)
    
    def send_summary_both(self, analysis_data: Dict[str, Any], to_whatsapp: Optional[str] = None, to_sms: Optional[str] = None) -> Dict[str, Any]:
        """
        Send analysis summary as both WhatsApp and SMS messages.
        
        Args:
            analysis_data: The analysis result from Gemini
            to_whatsapp: WhatsApp recipient number (optional)
            to_sms: SMS recipient number (optional)
            
        Returns:
            Dictionary with success status for both channels
        """
        message = self.format_summary_message(analysis_data)
        
        results = {
            "whatsapp": None,
            "sms": None
        }
        
        # Send WhatsApp
        if settings.twilio_whatsapp_from and (to_whatsapp or settings.twilio_whatsapp_to):
            results["whatsapp"] = self.send_whatsapp(message, to_whatsapp)
        
        # Send SMS
        if settings.twilio_sms_from and (to_sms or settings.twilio_sms_to):
            results["sms"] = self.send_sms(message, to_sms)
        
        return results
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return self.is_configured_flag
    
    def get_provider_name(self) -> str:
        """Get the name of the provider."""
        return "twilio"
    
    def send_audio(self, audio_path: str, caption: str = "", to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an audio file via WhatsApp using Twilio.
        
        Args:
            audio_path: Path to the audio file to send
            caption: Optional caption/text message to send with the audio
            to: Recipient phone number (optional, uses default if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Twilio not configured",
                "message": "Twilio credentials not set"
            }
        
        # Use provided 'to' or fallback to config default
        recipient = to or settings.twilio_whatsapp_to
        if not recipient:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided"
            }
        
        try:
            # Send caption first if provided
            if caption:
                caption_result = self.send_whatsapp(caption, to=recipient)
                if not caption_result.get("success"):
                    print(f"⚠️  Failed to send audio caption: {caption_result.get('error')}")
            
            # For Twilio, we need to upload the file to a publicly accessible URL first
            # For now, we'll send a message indicating the limitation
            # In production, you would upload to S3/Cloud Storage and use that URL
            print(f"⚠️  Twilio audio sending requires public URL - sending caption only")
            print(f"   Audio file path: {audio_path}")
            
            return {
                "success": False,
                "error": "Twilio requires public URL for media",
                "message": "Audio file sending via Twilio requires uploading to a public URL first. Please use Meta WhatsApp provider for direct file uploads."
            }
            
        except Exception as e:
            print(f"❌ Unexpected error sending audio: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Unexpected error sending audio"
            }


# Singleton instance
twilio_service = TwilioService()
