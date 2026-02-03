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
        Format analysis data into a readable WhatsApp message.
        
        Args:
            analysis_data: The analysis result from Gemini
            
        Returns:
            Formatted message string
        """
        lines = []
        
        # Header
        date = analysis_data.get('date', 'לא צוין')
        lines.append(f"🧠 *סיכום יומי - Second Brain*")
        lines.append(f"📅 תאריך: {date}")
        lines.append("")
        
        # Summary
        if analysis_data.get('summary'):
            lines.append("*סיכום כללי:*")
            summary = analysis_data['summary']
            # Truncate if too long (WhatsApp has limits)
            if len(summary) > 500:
                summary = summary[:500] + "..."
            lines.append(summary)
            lines.append("")
        
        # Action Items
        if analysis_data.get('action_items') and isinstance(analysis_data['action_items'], list):
            lines.append("*✅ משימות פעולה:*")
            for i, item in enumerate(analysis_data['action_items'][:5], 1):  # Limit to 5 items
                if isinstance(item, dict):
                    title = item.get('title', '')
                    priority = item.get('priority', '')
                    if title:
                        item_text = f"{i}. {title}"
                        if priority:
                            item_text += f" [{priority}]"
                        lines.append(item_text)
                else:
                    lines.append(f"{i}. {str(item)}")
            if len(analysis_data['action_items']) > 5:
                lines.append(f"... ועוד {len(analysis_data['action_items']) - 5} משימות")
            lines.append("")
        
        # Key Insights
        if analysis_data.get('insights') and isinstance(analysis_data['insights'], list):
            lines.append("*💡 תובנות מפתח:*")
            for insight in analysis_data['insights'][:3]:  # Limit to 3 insights
                lines.append(f"• {str(insight)}")
            lines.append("")
        
        # Leadership feedback (brief)
        if analysis_data.get('leadership_feedback'):
            lf = analysis_data['leadership_feedback']
            if lf.get('the_why'):
                lines.append("*💡 מנהיגות:*")
                why = lf['the_why']
                if len(why) > 200:
                    why = why[:200] + "..."
                lines.append(why)
                lines.append("")
        
        # Footer
        lines.append("📄 לפרטים מלאים, הורד את ה-PDF מהמערכת")
        
        # Join all lines
        message = "\n".join(lines)
        
        # Limit total message length to 1500 characters (SMS/WhatsApp limits)
        MAX_MESSAGE_LENGTH = 1500
        if len(message) > MAX_MESSAGE_LENGTH:
            # Truncate and add indicator
            truncated = message[:MAX_MESSAGE_LENGTH - 20]  # Reserve space for "..."
            # Try to cut at a newline to avoid cutting mid-word
            last_newline = truncated.rfind('\n')
            if last_newline > MAX_MESSAGE_LENGTH - 100:  # If we can find a reasonable break point
                message = truncated[:last_newline] + "\n\n... (הודעה קוצרה)"
            else:
                message = truncated + "... (הודעה קוצרה)"
        
        return message
    
    def send_whatsapp(self, message: str, to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio.
        
        Args:
            message: The message to send
            to: Recipient number (optional, uses config default if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Twilio not configured",
                "message": "Twilio credentials not set"
            }
        
        if not settings.twilio_whatsapp_from:
            return {
                "success": False,
                "error": "WhatsApp from number not configured",
                "message": "TWILIO_WHATSAPP_FROM not set"
            }
        
        recipient = to or settings.twilio_whatsapp_to
        if not recipient:
            return {
                "success": False,
                "error": "WhatsApp recipient not configured",
                "message": "TWILIO_WHATSAPP_TO not set and no 'to' parameter provided"
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
            to: Recipient number (optional, uses config default if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured_flag:
            return {
                "success": False,
                "error": "Twilio not configured",
                "message": "Twilio credentials not set"
            }
        
        if not settings.twilio_sms_from:
            return {
                "success": False,
                "error": "SMS from number not configured",
                "message": "TWILIO_SMS_FROM not set"
            }
        
        recipient = to or settings.twilio_sms_to
        if not recipient:
            return {
                "success": False,
                "error": "SMS recipient not configured",
                "message": "TWILIO_SMS_TO not set and no 'to' parameter provided"
            }
        
        try:
            print(f"📱 Sending SMS to {recipient}...")
            
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
    
    def send_summary(self, analysis_data: Dict[str, Any], to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send analysis summary as WhatsApp message.
        
        Args:
            analysis_data: The analysis result from Gemini
            to: Recipient number (optional)
            
        Returns:
            Dictionary with success status and details
        """
        message = self.format_summary_message(analysis_data)
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
        """Get the provider name."""
        return "twilio"


# Singleton instance
twilio_service = TwilioService()
