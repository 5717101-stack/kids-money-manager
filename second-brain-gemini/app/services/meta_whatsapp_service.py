"""
Meta WhatsApp Cloud API service for sending WhatsApp messages.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
import requests
import os
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
        self.app_id = None
        self.app_secret = None
        
        if settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id:
            try:
                self.access_token = settings.whatsapp_cloud_api_token
                self.phone_number_id = settings.whatsapp_phone_number_id
                self.app_id = settings.whatsapp_app_id
                self.app_secret = settings.whatsapp_app_secret
                self.is_configured_flag = True
                print("✅ Meta WhatsApp Cloud API initialized successfully")
                if self.app_id and self.app_secret:
                    print("   ✅ Token refresh enabled (App ID and Secret configured)")
                else:
                    print("   ⚠️  Token refresh disabled - set WHATSAPP_APP_ID and WHATSAPP_APP_SECRET for automatic token refresh")
                
                # Check token type and expiration
                self._check_token_info()
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
    
    def _check_token_info(self):
        """Check token type and expiration date."""
        if not self.access_token:
            return
        
        try:
            # Use debug_token endpoint to check token info
            url = f"{self.BASE_URL}/debug_token"
            params = {
                "input_token": self.access_token,
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                token_data = data.get('data', {})
                
                expires_at = token_data.get('expires_at')
                is_valid = token_data.get('is_valid', False)
                
                if expires_at:
                    from datetime import datetime
                    exp_time = datetime.fromtimestamp(expires_at)
                    now = datetime.now()
                    days_left = (exp_time - now).days
                    hours_left = (exp_time - now).total_seconds() / 3600
                    
                    if days_left > 30:
                        print(f"   ✅ Token is Long-Lived (expires in {days_left} days)")
                    elif hours_left > 1:
                        print(f"   ⚠️  Token is Short-Lived (expires in {int(hours_left)} hours)")
                        print(f"   ⚠️  WARNING: Short-Lived tokens expire after 1 hour!")
                        print(f"   ⚠️  To fix: Convert to Long-Lived token (60 days) using:")
                        print(f"      curl -X GET \"https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_TOKEN\"")
                    else:
                        print(f"   ❌ Token expires soon (in {int(hours_left)} hours)")
                elif is_valid:
                    print(f"   ⚠️  Token is valid but expiration date unknown")
                else:
                    print(f"   ❌ Token is invalid")
            else:
                print(f"   ⚠️  Could not check token info (status: {response.status_code})")
        except Exception as e:
            print(f"   ⚠️  Could not check token info: {e}")
    
    def _is_token_expired_error(self, error_message: str) -> bool:
        """Check if error indicates token expiration."""
        expired_indicators = [
            "session has expired",
            "error validating access token",
            "token expired",
            "invalid access token",
            "access token has expired"
        ]
        error_lower = error_message.lower()
        return any(indicator in error_lower for indicator in expired_indicators)
    
    def _refresh_access_token(self) -> Optional[str]:
        """
        Attempt to refresh the access token using App ID and Secret.
        
        Returns:
            New access token if refresh successful, None otherwise
        """
        if not self.app_id or not self.app_secret or not self.access_token:
            return None
        
        try:
            print("🔄 Attempting to refresh Meta WhatsApp access token...")
            
            # Exchange short-lived token for long-lived token
            url = f"{self.BASE_URL}/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            new_token = result.get("access_token")
            
            if new_token:
                print(f"✅ Successfully refreshed Meta WhatsApp access token!")
                print(f"   New token expires in: {result.get('expires_in', 'unknown')} seconds")
                self.access_token = new_token
                return new_token
            else:
                print("⚠️  Token refresh response did not contain access_token")
                return None
                
        except Exception as e:
            print(f"❌ Failed to refresh Meta WhatsApp token: {e}")
            return None
    
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
        
        # Use provided 'to' or fallback to config default
        recipient = to or settings.whatsapp_to
        if not recipient:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided. Set WHATSAPP_TO environment variable or provide 'to' parameter."
            }
        
        # Ensure phone number is in E.164 format (remove whatsapp: prefix if present)
        if recipient.startswith("whatsapp:"):
            recipient = recipient.replace("whatsapp:", "")
        
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
            
            # Check response status
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                print(f"❌ Meta WhatsApp API returned error: {error_msg}")
                response.raise_for_status()
            
            result_data = response.json()
            
            # Check if message was actually sent
            messages = result_data.get('messages', [])
            if not messages:
                print(f"⚠️  Meta API response does not contain message data")
                print(f"   Full response: {result_data}")
                return {
                    "success": False,
                    "error": "No message data in API response",
                    "response": result_data,
                    "message": "Meta API did not return message confirmation"
                }
            
            message_id = messages[0].get('id')
            contacts = result_data.get('contacts', [])
            
            print(f"✅ WhatsApp message sent successfully via Meta API!")
            print(f"   Message ID: {message_id}")
            if contacts:
                contact = contacts[0]
                print(f"   Recipient: {contact.get('wa_id', 'N/A')}")
                print(f"   Input: {contact.get('input', 'N/A')}")
            
            # Check for errors in response
            errors = result_data.get('errors', [])
            if errors:
                error_msg = errors[0].get('message', 'Unknown error')
                print(f"⚠️  Warning: API returned errors: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message_id": message_id,
                    "response": result_data,
                    "message": f"Meta API returned error: {error_msg}"
                }
            
            return {
                "success": True,
                "message_id": message_id,
                "status": "sent",
                "response": result_data,
                "message": "WhatsApp message sent successfully via Meta API"
            }
            
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            error_code = None
            try:
                error_response = e.response.json()
                error_detail = error_response.get('error', {}).get('message', str(e))
                error_code = error_response.get('error', {}).get('code')
            except:
                error_detail = str(e)
            
            # Check if token expired and try to refresh
            if self._is_token_expired_error(error_detail):
                print(f"⚠️  Meta WhatsApp token expired: {error_detail}")
                print("🔄 Attempting automatic token refresh...")
                
                new_token = self._refresh_access_token()
                if new_token:
                    print("🔄 Retrying message send with refreshed token...")
                    # Retry the request with new token
                    try:
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = requests.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        
                        result_data = response.json()
                        print(f"✅ WhatsApp message sent successfully after token refresh!")
                        print(f"   Message ID: {result_data.get('messages', [{}])[0].get('id', 'N/A')}")
                        
                        return {
                            "success": True,
                            "message_id": result_data.get('messages', [{}])[0].get('id'),
                            "status": "sent",
                            "message": "WhatsApp message sent successfully via Meta API (after token refresh)"
                        }
                    except Exception as retry_error:
                        print(f"❌ Retry failed after token refresh: {retry_error}")
                        return {
                            "success": False,
                            "error": f"Token expired and refresh failed: {str(retry_error)}",
                            "code": error_code,
                            "message": "Meta WhatsApp token expired. Please update WHATSAPP_CLOUD_API_TOKEN in your environment variables. For automatic refresh, set WHATSAPP_APP_ID and WHATSAPP_APP_SECRET."
                        }
                else:
                    print("❌ Token refresh not available or failed")
                    return {
                        "success": False,
                        "error": error_detail,
                        "code": error_code,
                        "message": f"Meta WhatsApp token expired. Please update WHATSAPP_CLOUD_API_TOKEN in your environment variables. For automatic refresh, set WHATSAPP_APP_ID and WHATSAPP_APP_SECRET. Error: {error_detail}"
                    }
            
            print(f"❌ Meta WhatsApp API error: {error_detail}")
            return {
                "success": False,
                "error": error_detail,
                "code": error_code or (e.response.status_code if hasattr(e, 'response') else None),
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
    
    def send_audio(self, audio_path: str, caption: str = "", to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an audio file via WhatsApp using Meta WhatsApp Cloud API.
        
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
                "error": "Meta WhatsApp not configured",
                "message": "Meta WhatsApp credentials not set"
            }
        
        # Use provided 'to' or fallback to config default
        recipient = to or settings.whatsapp_to
        if not recipient:
            return {
                "success": False,
                "error": "Recipient number required",
                "message": "Recipient phone number must be provided"
            }
        
        # Ensure phone number is in E.164 format
        if recipient.startswith("whatsapp:"):
            recipient = recipient.replace("whatsapp:", "")
        
        try:
            # Verify file exists before attempting upload
            if not os.path.exists(audio_path):
                print(f"❌ Audio file does not exist: {audio_path}")
                return {
                    "success": False,
                    "error": "Audio file not found",
                    "message": f"Audio file does not exist: {audio_path}"
                }
            
            file_size = os.path.getsize(audio_path)
            print(f"📤 Uploading audio file: {audio_path} (size: {file_size} bytes)")
            
            # Step 1: Upload media to Meta's servers
            upload_url = f"{self.BASE_URL}/{self.phone_number_id}/media"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Read audio file and set correct MIME type for MP3
            with open(audio_path, 'rb') as audio_file:
                filename = audio_path.split('/')[-1]
                # Ensure filename ends with .mp3 for proper MIME type detection
                if not filename.endswith('.mp3'):
                    filename = 'audio_slice.mp3'
                files = {
                    'file': (filename, audio_file, 'audio/mpeg')  # MP3 MIME type for Meta API
                }
                data = {
                    'messaging_product': 'whatsapp',
                    'type': 'audio'
                }
                
                print(f"📤 Uploading to Meta: {upload_url}")
                print(f"   Filename: {filename}")
                print(f"   MIME type: audio/mpeg")
                
                upload_response = requests.post(upload_url, headers=headers, files=files, data=data)
                
                if upload_response.status_code != 200:
                    error_detail = upload_response.text
                    print(f"❌ Upload failed with status {upload_response.status_code}: {error_detail}")
                    return {
                        "success": False,
                        "error": f"Upload failed: HTTP {upload_response.status_code}",
                        "message": f"Failed to upload audio to Meta servers: {error_detail}",
                        "status_code": upload_response.status_code
                    }
                
                upload_response.raise_for_status()
                upload_result = upload_response.json()
                media_id = upload_result.get('id')
                
                print(f"✅ Upload successful - Media ID: {media_id}")
                
                if not media_id:
                    print(f"❌ No media ID in upload response: {upload_result}")
                    return {
                        "success": False,
                        "error": "No media ID in upload response",
                        "message": "Failed to upload audio to Meta servers",
                        "response": upload_result
                    }
            
            # Step 2: Send message with media
            message_url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            message_headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "audio",
                "audio": {
                    "id": media_id
                }
            }
            
            # Send audio message FIRST (before caption) to ensure audio is the primary message
            print(f"📤 Sending audio message to {recipient}...")
            print(f"   Media ID: {media_id}")
            print(f"   Payload: {payload}")
            response = requests.post(message_url, json=payload, headers=message_headers)
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ Audio message send failed with status {response.status_code}: {error_detail}")
                print(f"   Response headers: {dict(response.headers)}")
                # If audio send fails, DO NOT send caption as fallback - return error immediately
                return {
                    "success": False,
                    "error": f"Send failed: HTTP {response.status_code}",
                    "message": f"Failed to send audio message: {error_detail}",
                    "status_code": response.status_code,
                    "response_text": error_detail
                }
            
            response.raise_for_status()
            result_data = response.json()
            
            print(f"✅ Audio message sent successfully")
            print(f"   Response: {result_data}")
            
            # Verify we got a message ID (confirms audio was actually sent)
            message_id = result_data.get('messages', [{}])[0].get('id')
            if not message_id:
                print(f"❌ No message ID in response - audio may not have been sent")
                print(f"   Full response: {result_data}")
                return {
                    "success": False,
                    "error": "No message ID in response",
                    "message": "Audio upload succeeded but message send failed",
                    "response": result_data
                }
            
            print(f"✅ Audio file sent via Meta WhatsApp API!")
            print(f"   Message ID: {message_id}")
            print(f"   Media ID: {media_id}")
            
            # Only send caption AFTER audio is successfully sent and verified
            if caption:
                print(f"📝 Sending caption after audio: {caption[:50]}...")
                caption_payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "text",
                    "text": {
                        "body": caption
                    }
                }
                caption_response = requests.post(message_url, json=caption_payload, headers=message_headers)
                if caption_response.status_code != 200:
                    print(f"⚠️  Caption send failed: {caption_response.status_code} - {caption_response.text}")
                    # Don't fail the whole operation if caption fails - audio was sent successfully
                else:
                    print(f"✅ Caption sent successfully")
                    caption_response.raise_for_status()
            
            print(f"✅ Audio file sent via Meta WhatsApp API!")
            print(f"   Message ID: {message_id}")
            print(f"   Media ID: {media_id}")
            
            return {
                "success": True,
                "message_id": message_id,
                "media_id": media_id,
                "status": "sent",
                "message": "Audio file sent successfully via Meta API"
            }
            
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_response = e.response.json()
                error_detail = error_response.get('error', {}).get('message', str(e))
            except:
                error_detail = str(e)
            
            print(f"❌ Meta WhatsApp API error sending audio: {error_detail}")
            return {
                "success": False,
                "error": error_detail,
                "message": f"Failed to send audio via Meta API: {error_detail}"
            }
        except Exception as e:
            print(f"❌ Unexpected error sending audio via Meta API: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Unexpected error sending audio via Meta API"
            }


# Singleton instance
meta_whatsapp_service = MetaWhatsAppService()
