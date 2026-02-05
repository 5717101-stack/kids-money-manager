"""
Second Brain - Daily Sync (Gemini Edition)
Main FastAPI application entry point.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, BackgroundTasks
from fastapi.datastructures import FormData
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import tempfile
import os
import io
import requests
from pathlib import Path
from datetime import datetime
from collections import deque
from threading import Lock

from app.core.config import settings
from app.services.gemini_service import gemini_service
from app.services.pdf_service import pdf_service
from app.services.twilio_service import twilio_service  # Keep for SMS and message formatting
from app.services.whatsapp_provider import WhatsAppProviderFactory
from app.services.drive_memory_service import DriveMemoryService

# Initialize WhatsApp provider based on configuration
whatsapp_provider = WhatsAppProviderFactory.create_provider()

# Debug: Print which provider was selected
if whatsapp_provider:
    print(f"📱 WhatsApp provider initialized: {whatsapp_provider.get_provider_name()}")
    print(f"   Config setting: {settings.whatsapp_provider}")
else:
    print(f"⚠️  WhatsApp provider not initialized!")
    print(f"   Config setting: {settings.whatsapp_provider}")
    print(f"   Available providers: {WhatsAppProviderFactory.get_available_providers()}")

# Initialize Drive Memory Service
drive_memory_service = DriveMemoryService()
if drive_memory_service.is_configured:
    print(f"✅ Drive Memory Service initialized")
    print(f"   Memory folder ID: {drive_memory_service.folder_id}")
else:
    print(f"⚠️  Drive Memory Service not configured (DRIVE_MEMORY_FOLDER_ID not set)")

# Idempotency: Track processed WhatsApp message IDs to prevent duplicate processing
# Use deque with maxlen to automatically limit memory usage (keeps last 1000 message IDs)
processed_message_ids = deque(maxlen=1000)

# Voice Imprinting: Track pending speaker identifications
# Key: message_id (wam_id), Value: file_path (temporary audio slice file)
pending_identifications = {}
_processed_ids_lock = Lock()  # Thread-safe access to processed_message_ids

def is_message_processed(message_id: str) -> bool:
    """
    Check if a message ID has already been processed.
    
    Args:
        message_id: WhatsApp message ID (wam_id)
    
    Returns:
        True if message was already processed, False otherwise
    """
    if not message_id:
        return False
    
    with _processed_ids_lock:
        return message_id in processed_message_ids

def mark_message_processed(message_id: str) -> None:
    """
    Mark a message ID as processed.
    
    Args:
        message_id: WhatsApp message ID (wam_id)
    """
    if not message_id:
        return
    
    with _processed_ids_lock:
        if message_id not in processed_message_ids:
            processed_message_ids.append(message_id)
            print(f"✅ Marked message {message_id} as processed (total tracked: {len(processed_message_ids)})")


def is_history_query(message: str) -> bool:
    """
    Check if a message is asking about past conversations/history.
    
    Examples:
    - "מה דיברתי עם מירי?"
    - "What did I talk about with John?"
    - "על מה דיברנו אתמול?"
    - "סכם את השיחות עם דני"
    """
    message_lower = message.lower()
    
    # Hebrew patterns
    hebrew_patterns = [
        'מה דיברתי',
        'מה דיברנו',
        'על מה דיברתי',
        'על מה דיברנו',
        'סכם את השיחות',
        'סכם שיחות',
        'מה אמר',
        'מה אמרה',
        'מה אמרו',
        'מתי דיברתי',
        'האם דיברתי',
        'האם דיברנו',
        'תזכיר לי מה',
        'מה היה בשיחה',
        'מה היה בהקלטה',
    ]
    
    # English patterns
    english_patterns = [
        'what did i talk',
        'what did we talk',
        'what did i discuss',
        'summarize my conversation',
        'summarize conversations',
        'what did .* say',
        'when did i talk',
        'did i talk',
        'remind me what',
        'what was in the call',
        'what was in the recording',
    ]
    
    # Check Hebrew patterns
    for pattern in hebrew_patterns:
        if pattern in message_lower:
            return True
    
    # Check English patterns
    import re
    for pattern in english_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def search_history_for_context(chat_history: list, query: str) -> str:
    """
    Search through chat history for relevant transcripts based on query.
    Returns formatted context string for Gemini.
    
    Searches for:
    - Speaker names mentioned in query
    - Keywords/topics mentioned in query
    - Audio transcripts with matching content
    """
    if not chat_history:
        return ""
    
    query_lower = query.lower()
    relevant_transcripts = []
    
    # Extract potential names from query (words that might be names)
    # Common Hebrew words to exclude
    hebrew_stopwords = ['מה', 'עם', 'את', 'על', 'של', 'לי', 'אני', 'הוא', 'היא', 'הם', 'דיברתי', 'דיברנו', 'אמר', 'אמרה']
    english_stopwords = ['what', 'did', 'i', 'we', 'talk', 'about', 'with', 'the', 'a', 'an', 'say', 'said']
    
    # Get all words from query as potential search terms
    import re
    words = re.findall(r'\b\w+\b', query_lower)
    search_terms = [w for w in words if w not in hebrew_stopwords and w not in english_stopwords and len(w) > 1]
    
    print(f"🔍 Searching history with terms: {search_terms}")
    
    for interaction in chat_history:
        # Only look at audio interactions with transcripts
        if interaction.get('type') != 'audio':
            continue
        
        transcript = interaction.get('transcript', {})
        if not transcript:
            continue
        
        speakers = interaction.get('speakers', [])
        segments = transcript.get('segments', []) if isinstance(transcript, dict) else []
        timestamp = interaction.get('timestamp', '')
        
        # Check if any speaker name matches search terms
        speaker_match = False
        for speaker in speakers:
            speaker_lower = speaker.lower()
            for term in search_terms:
                if term in speaker_lower or speaker_lower in term:
                    speaker_match = True
                    break
        
        # Check if any segment text contains search terms
        content_match = False
        matching_segments = []
        for segment in segments:
            text = segment.get('text', '').lower()
            speaker = segment.get('speaker', '')
            for term in search_terms:
                if term in text:
                    content_match = True
                    matching_segments.append(segment)
                    break
        
        # If we found a match, add to results
        if speaker_match or content_match:
            # Format the transcript for context
            transcript_text = f"\n📅 Recording from {timestamp}:\n"
            transcript_text += f"👥 Speakers: {', '.join(speakers) if speakers else 'Unknown'}\n"
            
            # Include all segments if speaker match, or just matching segments if content match
            segments_to_include = segments if speaker_match else matching_segments
            for seg in segments_to_include[:20]:  # Limit to first 20 segments to avoid too much text
                speaker = seg.get('speaker', 'Unknown')
                text = seg.get('text', '')
                transcript_text += f"  {speaker}: {text}\n"
            
            relevant_transcripts.append(transcript_text)
    
    if relevant_transcripts:
        context = f"Found {len(relevant_transcripts)} relevant recording(s):\n"
        context += "\n---\n".join(relevant_transcripts[:5])  # Limit to 5 most relevant
        return context
    
    return ""


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: Pre-warm memory cache
@app.on_event("startup")
async def startup_event():
    """Pre-warm memory cache on server startup."""
    if drive_memory_service.is_configured:
        print("🔥 Pre-warming memory cache...")
        drive_memory_service.preload_memory()
    else:
        print("⚠️  Skipping memory cache pre-warm (Drive Memory Service not configured)")

# Get the project root directory (parent of app/)
_base_dir = Path(__file__).parent.parent.resolve()
_static_dir = _base_dir / "static"
_html_path = _static_dir / "index.html"

print(f"📁 Base dir: {_base_dir}")
print(f"📁 Static dir: {_static_dir}")
print(f"📄 HTML path: {_html_path}")
print(f"✅ HTML exists: {_html_path.exists()}")


@app.get("/")
async def root():
    """Root endpoint - serves the web interface."""
    # Serve HTML directly
    if _html_path.exists():
        return FileResponse(
            str(_html_path),
            media_type="text/html"
        )
    
    # Fallback
    return {
        "message": "Second Brain - Daily Sync (Gemini Edition)",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "web_interface": "/static/index.html"
    }


@app.get("/static/index.html")
async def serve_index():
    """Serve the main HTML page."""
    if _html_path.exists():
        return FileResponse(
            str(_html_path),
            media_type="text/html"
        )
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "second-brain-gemini"
    }


@app.get("/version")
async def get_version():
    """Get the current version number."""
    version_file = _base_dir / "VERSION"
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
        return {"version": version}
    return {"version": "1.0.0"}


@app.get("/whatsapp-provider-status")
async def get_whatsapp_provider_status():
    """Get current WhatsApp provider status and configuration."""
    meta_token_info = None
    if whatsapp_provider and whatsapp_provider.get_provider_name() == 'meta':
        # Try to get token info
        try:
            from app.services.meta_whatsapp_service import meta_whatsapp_service
            import requests
            from datetime import datetime
            
            token = meta_whatsapp_service.access_token
            if token:
                url = f"https://graph.facebook.com/v18.0/debug_token"
                params = {
                    "input_token": token,
                    "access_token": token
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    token_data = data.get('data', {})
                    expires_at = token_data.get('expires_at')
                    if expires_at:
                        exp_time = datetime.fromtimestamp(expires_at)
                        now = datetime.now()
                        days_left = (exp_time - now).days
                        hours_left = (exp_time - now).total_seconds() / 3600
                        meta_token_info = {
                            "expires_at": exp_time.isoformat(),
                            "days_left": days_left,
                            "hours_left": round(hours_left, 1),
                            "is_long_lived": days_left > 30,
                            "is_short_lived": hours_left < 24
                        }
                    else:
                        meta_token_info = {
                            "error": "No expiration date in token data",
                            "token_data": token_data
                        }
                else:
                    error_data = response.json() if response.content else {}
                    meta_token_info = {
                        "error": f"API returned status {response.status_code}",
                        "message": error_data.get('error', {}).get('message', 'Unknown error')
                    }
            else:
                meta_token_info = {"error": "Token not available in service"}
        except Exception as e:
            import traceback
            meta_token_info = {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    status = {
        "configured_provider": settings.whatsapp_provider,
        "active_provider": whatsapp_provider.get_provider_name() if whatsapp_provider else None,
        "available_providers": WhatsAppProviderFactory.get_available_providers(),
        "meta_configured": bool(settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id),
        "twilio_configured": bool(settings.twilio_account_sid and settings.twilio_auth_token),
        "meta_config": {
            "has_token": bool(settings.whatsapp_cloud_api_token),
            "has_phone_id": bool(settings.whatsapp_phone_number_id),
            "has_verify_token": bool(settings.whatsapp_verify_token),
            "has_app_id": bool(settings.whatsapp_app_id),
            "has_app_secret": bool(settings.whatsapp_app_secret),
            "token_info": meta_token_info
        }
    }
    return JSONResponse(content=status)


@app.post("/test-whatsapp")
async def test_whatsapp(request: Request):
    """
    Send a test WhatsApp message.
    
    Expects JSON body with optional 'message' field.
    """
    try:
        data = await request.json()
        message = data.get('message', 'testing')
        
        print(f"\n{'='*60}")
        print(f"📱 Test WhatsApp request received: {message}")
        print(f"{'='*60}")
        print(f"🔍 Current WhatsApp provider: {whatsapp_provider.get_provider_name() if whatsapp_provider else 'None'}")
        print(f"🔍 Config setting (WHATSAPP_PROVIDER): {settings.whatsapp_provider}")
        print(f"🔍 Provider type: {type(whatsapp_provider).__name__ if whatsapp_provider else 'None'}")
        print(f"{'='*60}\n")
        
        # Use WhatsApp provider (Twilio or Meta based on config)
        if not whatsapp_provider:
            raise HTTPException(
                status_code=500,
                detail="WhatsApp provider not configured. Please check your environment variables."
            )
        
        # Get recipient from request or use default from config
        recipient = data.get('to', None)
        
        # For Meta, we need a recipient number
        if whatsapp_provider.get_provider_name() == 'meta' and not recipient:
            # Try to use default from config
            recipient = settings.whatsapp_to
        
        result = whatsapp_provider.send_whatsapp(message, recipient)
        
        if result.get('success'):
            # Log additional info for debugging
            if 'message_id' in result:
                print(f"✅ Message ID: {result.get('message_id')}")
            if 'response' in result:
                response_data = result.get('response', {})
                if 'contacts' in response_data:
                    print(f"📱 Contact info: {response_data.get('contacts')}")
                if 'errors' in response_data:
                    print(f"⚠️  Response errors: {response_data.get('errors')}")
            return JSONResponse(content=result)
        else:
            error_msg = result.get('error', 'Failed to send WhatsApp message')
            error_detail = result.get('message', error_msg)
            print(f"❌ Failed to send WhatsApp: {error_detail}")
            raise HTTPException(
                status_code=500,
                detail=error_detail
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in test-whatsapp endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test message: {str(e)}"
        )


@app.post("/test-sms")
async def test_sms(request: Request):
    """
    Send a test SMS message.
    
    Expects JSON body with optional 'message' field.
    """
    try:
        data = await request.json()
        message = data.get('message', 'testing')
        
        print(f"📱 Test SMS request received: {message}")
        
        result = twilio_service.send_sms(message)
        
        if result.get('success'):
            return JSONResponse(content=result)
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to send SMS message')
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in test-sms endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test SMS: {str(e)}"
        )


@app.get("/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """
    Meta WhatsApp webhook verification endpoint.
    """
    from app.services.meta_whatsapp_service import meta_whatsapp_service
    
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode and token and challenge:
        result = meta_whatsapp_service.verify_webhook(mode, token, challenge)
        if result:
            return int(result)
    
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.get("/webhook")
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle WhatsApp Cloud API webhook for Meta.
    GET: Webhook verification
    POST: Incoming messages and status updates
    """
    if request.method == "GET":
        # Webhook verification
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        verify_token = os.environ.get("WEBHOOK_VERIFY_TOKEN")
        
        if mode == "subscribe" and token == verify_token:
            print(f"✅ Webhook verified successfully")
            return int(challenge) if challenge else JSONResponse(content={"status": "verified"})
        else:
            print(f"❌ Webhook verification failed: mode={mode}, token_match={token == verify_token}")
            raise HTTPException(status_code=403, detail="Webhook verification failed")
    
    elif request.method == "POST":
        # Handle incoming messages and status updates
        try:
            payload = await request.json()
            
            # Print entire payload for debugging
            print(f"\n{'='*60}")
            print(f"📱 WhatsApp Cloud API Webhook Received")
            print(f"{'='*60}")
            import json
            print(json.dumps(payload, indent=2))
            print(f"{'='*60}\n")
            
            # Process the webhook payload
            if "entry" in payload:
                for entry in payload.get("entry", []):
                    changes = entry.get("changes", [])
                    for change in changes:
                        value = change.get("value", {})
                        field = change.get("field")
                        
                        # Handle incoming messages
                        if field == "messages" and "messages" in value:
                            messages = value.get("messages", [])
                            metadata = value.get("metadata", {})
                            phone_number_id = metadata.get("phone_number_id")
                            
                            for message in messages:
                                from_number = message.get("from")
                                message_body_text = message.get("text", {}).get("body", "")
                                message_id = message.get("id")
                                message_type = message.get("type")
                                timestamp = message.get("timestamp")
                                
                                # STRICT REPLY INTERCEPTOR: Check for voice imprinting reply BEFORE any other processing
                                context = message.get("context", {})
                                replied_message_id = context.get("id") if context else None
                                
                                print(f"📨 Processing Incoming Message:")
                                print(f"   From: {from_number}")
                                print(f"   Message: {message_body_text}")
                                print(f"   Message ID: {message_id}")
                                print(f"   Type: {message_type}")
                                print(f"   Timestamp: {timestamp}")
                                print(f"   Context: {context}")
                                print(f"   Replied to Message ID: {replied_message_id}")
                                print(f"   Pending identifications: {list(pending_identifications.keys())}")
                                
                                # VOICE IMPRINTING: Strict Reply Interceptor - Check BEFORE idempotency check
                                # Only process text messages that are replies to voice identification requests
                                if message_type == "text" and replied_message_id and replied_message_id in pending_identifications:
                                    print(f"🎤 STRICT REPLY INTERCEPTOR: Detected reply to voice identification message!")
                                    print(f"   Replying to message ID: {replied_message_id}")
                                    
                                    # This is a reply to a speaker identification request
                                    file_path = pending_identifications.pop(replied_message_id)
                                    person_name = message_body_text.strip()
                                    
                                    print(f"🎤 Voice Imprinting: User identified speaker as '{person_name}'")
                                    print(f"   Audio file path: {file_path}")
                                    
                                    # Mark message as processed to prevent duplicate processing
                                    mark_message_processed(message_id)
                                    
                                    # Check if file still exists (might have been cleaned up)
                                    if os.path.exists(file_path):
                                        # Upload voice signature to Drive
                                        file_id = drive_memory_service.upload_voice_signature(
                                            file_path=file_path,
                                            person_name=person_name
                                        )
                                        
                                        if file_id:
                                            # Send confirmation message
                                            confirmation = f"✅ למדתי! הקול של *{person_name}* נשמר במערכת."
                                            whatsapp_provider.send_whatsapp(
                                                message=confirmation,
                                                to=f"+{from_number}"
                                            )
                                            print(f"✅ Voice signature saved for '{person_name}' (File ID: {file_id})")
                                        else:
                                            print(f"⚠️  Failed to upload voice signature for '{person_name}'")
                                            whatsapp_provider.send_whatsapp(
                                                message="⚠️  שגיאה בשמירת הקול. נסה שוב.",
                                                to=f"+{from_number}"
                                            )
                                        
                                        # Cleanup file after successful upload
                                        try:
                                            os.unlink(file_path)
                                            print(f"🗑️  Cleaned up slice file after voice imprinting: {file_path}")
                                        except Exception as cleanup_error:
                                            print(f"⚠️  Failed to cleanup slice file: {cleanup_error}")
                                    else:
                                        print(f"⚠️  Audio file no longer exists: {file_path}")
                                        print(f"   File may have been cleaned up before user replied")
                                    
                                    # CRITICAL: STOP PROCESSING here. Do not call Gemini.
                                    print(f"🛑 Voice imprinting complete - skipping Gemini processing")
                                    continue
                                
                                # IDEMPOTENCY CHECK: Prevent duplicate processing due to webhook retries
                                if is_message_processed(message_id):
                                    print(f"⚠️  Duplicate message received (ID: {message_id}). Ignoring.")
                                    continue  # Skip processing, but return 200 OK to WhatsApp
                                
                                # Mark message as processed BEFORE processing (prevents race conditions)
                                mark_message_processed(message_id)
                                
                                # Handle audio messages
                                if message_type == "audio":
                                    try:
                                        print("🎤 Audio message detected - starting processing...")
                                        
                                        # Get audio media info from message
                                        audio_data = message.get("audio", {})
                                        media_id = audio_data.get("id")
                                        
                                        if not media_id:
                                            print("❌ CRITICAL AUDIO ERROR: No media ID found in audio message")
                                            continue
                                        
                                        print(f"📥 Media ID: {media_id}")
                                        
                                        # Get WhatsApp API token (Meta)
                                        from app.services.meta_whatsapp_service import meta_whatsapp_service
                                        if not meta_whatsapp_service.is_configured:
                                            print("❌ CRITICAL AUDIO ERROR: Meta WhatsApp service not configured")
                                            continue
                                        
                                        access_token = meta_whatsapp_service.access_token
                                        phone_number_id = meta_whatsapp_service.phone_number_id
                                        
                                        if not access_token:
                                            print("❌ CRITICAL AUDIO ERROR: WhatsApp API token not available")
                                            continue
                                        
                                        print("🔐 Attempting to download media from WhatsApp...")
                                        
                                        # Step 1: Get media URL from WhatsApp API
                                        import requests
                                        media_url = f"https://graph.facebook.com/v18.0/{media_id}"
                                        headers = {
                                            "Authorization": f"Bearer {access_token}"
                                        }
                                        
                                        print(f"   Requesting media URL from: {media_url}")
                                        media_response = requests.get(media_url, headers=headers, timeout=30)
                                        
                                        if media_response.status_code != 200:
                                            print(f"❌ CRITICAL AUDIO ERROR: Failed to get media URL. Status: {media_response.status_code}")
                                            print(f"   Response: {media_response.text[:500]}")
                                            continue
                                        
                                        media_info = media_response.json()
                                        download_url = media_info.get("url")
                                        
                                        if not download_url:
                                            print("❌ CRITICAL AUDIO ERROR: No download URL in media response")
                                            print(f"   Media info: {media_info}")
                                            continue
                                        
                                        print(f"✅ Media URL retrieved: {download_url[:100]}...")
                                        
                                        # Step 2: Download the actual audio file
                                        print("📥 Downloading audio file from WhatsApp...")
                                        download_headers = {
                                            "Authorization": f"Bearer {access_token}"
                                        }
                                        
                                        audio_response = requests.get(download_url, headers=download_headers, timeout=60)
                                        
                                        if audio_response.status_code != 200:
                                            print(f"❌ CRITICAL AUDIO ERROR: Failed to download audio. Status: {audio_response.status_code}")
                                            print(f"   Response: {audio_response.text[:500]}")
                                            continue
                                        
                                        audio_bytes = audio_response.content
                                        print(f"✅ Media downloaded successfully. Size: {len(audio_bytes)} bytes")
                                        
                                        # Step 3: Upload to Drive archive
                                        print("📤 Attempting to upload to Google Drive...")
                                        # Convert downloaded content to a stream
                                        file_stream = io.BytesIO(audio_bytes)
                                        audio_metadata = drive_memory_service.upload_audio_to_archive(
                                            audio_file_obj=file_stream,
                                            filename=f"whatsapp_audio_{message_id}.ogg",
                                            mime_type="audio/ogg"
                                        )
                                        
                                        if not audio_metadata:
                                            print("❌ CRITICAL AUDIO ERROR: upload_audio_to_archive returned None")
                                            continue
                                        
                                        print(f"✅ Audio archived successfully. File ID: {audio_metadata.get('file_id')}")
                                        
                                        # Step 4: Process with Gemini (save to temp file first)
                                        import tempfile
                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_file:
                                            tmp_file.write(audio_bytes)
                                            tmp_path = tmp_file.name
                                        
                                        print("🤖 Processing audio with Gemini...")
                                        
                                        # Initialize variables that will be used later (even if processing fails)
                                        segments = []
                                        unknown_speakers_found = []
                                        success = False
                                        processing_error_occurred = False  # Track if error was caught
                                        
                                        # Retrieve voice signatures for speaker identification
                                        reference_voices = []
                                        known_speaker_names = []  # List of names we already know (for filtering)
                                        if drive_memory_service.is_configured:
                                            try:
                                                print("🎤 Retrieving voice signatures for speaker identification...")
                                                reference_voices = drive_memory_service.get_voice_signatures()
                                                # Also get just the names for filtering (lowercase for comparison)
                                                known_speaker_names = [rv['name'].lower() for rv in reference_voices]
                                                if reference_voices:
                                                    print(f"✅ Retrieved {len(reference_voices)} voice signature(s): {[rv['name'] for rv in reference_voices]}")
                                                    print(f"📋 Known speaker names for filtering: {known_speaker_names}")
                                                else:
                                                    print("ℹ️  No voice signatures found - will use generic speaker IDs")
                                            except Exception as voice_sig_error:
                                                print(f"⚠️  Error retrieving voice signatures: {voice_sig_error}")
                                                import traceback
                                                traceback.print_exc()
                                                # Continue without voice signatures
                                                reference_voices = []
                                                known_speaker_names = []
                                        
                                        try:
                                            result = gemini_service.analyze_day(
                                                audio_paths=[tmp_path],
                                                audio_file_metadata=[audio_metadata],
                                                reference_voices=reference_voices
                                            )
                                            
                                            print("✅ Gemini analysis complete")
                                            
                                            # Extract JSON transcript (now contains segments with timestamps)
                                            transcript_json = result.get('transcript', {})
                                            segments = transcript_json.get('segments', [])
                                            
                                            print(f"   Transcript segments: {len(segments)} segments")
                                            
                                            # Validate segments have valid timestamps before processing
                                            valid_segments = []
                                            for seg in segments:
                                                start = seg.get('start', None)
                                                end = seg.get('end', None)
                                                if start is not None and end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
                                                    if end > start and start >= 0:
                                                        valid_segments.append(seg)
                                                    else:
                                                        print(f"⚠️  Skipping invalid segment: start={start}, end={end} (end must be > start, start >= 0)")
                                                else:
                                                    print(f"⚠️  Skipping segment with missing/invalid timestamps: start={start}, end={end}")
                                            
                                            segments = valid_segments
                                            print(f"   Valid segments with timestamps: {len(segments)}")
                                            
                                            # Extract unique speaker names from segments for searchability
                                            speaker_names = set()
                                            for segment in segments:
                                                speaker = segment.get('speaker', '')
                                                if speaker and not speaker.lower().startswith('speaker '):
                                                    # Only add actual names, not generic "Speaker 1", "Speaker 2", etc.
                                                    speaker_names.add(speaker)
                                            speaker_names = list(speaker_names)
                                            print(f"   Identified speakers: {speaker_names if speaker_names else 'Generic speaker IDs only'}")
                                            
                                            # Save full JSON transcript to memory (with identified speaker names)
                                            audio_interaction = {
                                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                                "type": "audio",
                                                "file_id": audio_metadata.get('file_id', ''),
                                                "web_content_link": audio_metadata.get('web_content_link', ''),
                                                "web_view_link": audio_metadata.get('web_view_link', ''),
                                                "filename": audio_metadata.get('filename', ''),
                                                "transcript": transcript_json,  # Full JSON with segments (includes speaker names)
                                                "speakers": speaker_names,  # List of identified speaker names for searchability
                                                "message_id": message_id,
                                                "from_number": from_number
                                            }
                                            
                                            success = drive_memory_service.update_memory(audio_interaction, background_tasks=background_tasks)
                                            if success:
                                                print(f"✅ Saved audio interaction to memory")
                                            
                                            # SPEAKER IDENTIFICATION: Detect unknown speakers and slice audio
                                            from pydub import AudioSegment
                                            import tempfile
                                            
                                            # Load original audio for slicing with FFmpeg safety check
                                            audio_segment = None
                                            slicing_error_occurred = False
                                            
                                            try:
                                                audio_segment = AudioSegment.from_file(tmp_path)
                                                print(f"✅ Loaded audio: {len(audio_segment)}ms ({len(audio_segment)/1000:.1f}s)")
                                            except FileNotFoundError as e:
                                                print(f"❌ ERROR: FFmpeg is likely missing on the server.")
                                                print(f"   Error: {e}")
                                                print(f"   Install FFmpeg: apt-get install ffmpeg (Linux) or brew install ffmpeg (Mac)")
                                                slicing_error_occurred = True
                                                error_message = "Error: Audio processing failed - FFmpeg missing (check logs)."
                                            except Exception as e:
                                                print(f"❌ SLICING ERROR: Failed to load audio file")
                                                print(f"   Error: {e}")
                                                import traceback
                                                traceback.print_exc()
                                                slicing_error_occurred = True
                                                error_message = "Error: Audio processing failed (check logs)."
                                            
                                            # If audio loading failed, send error message and skip slicing
                                            if slicing_error_occurred:
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message=error_message,
                                                        to=f"+{from_number}"
                                                    )
                                                    print(f"📤 Sent error alert to user via WhatsApp")
                                                continue
                                            
                                            # Iterate through segments to find unknown speakers
                                            unknown_speakers_found = []
                                            processed_speakers = set()  # Track speakers we've already sent samples for
                                            
                                            # MINIMUM SLICE LENGTH: 5 seconds for good voice identification
                                            MIN_SLICE_MS = 5000
                                            MAX_SLICE_MS = 10000
                                            
                                            for i, segment in enumerate(segments):
                                                # STEP 1: Immediate Conversion - Convert Gemini timestamps (SECONDS) to Pydub timestamps (MILLISECONDS)
                                                # Gemini returns floats in SECONDS (e.g., 5.5), Pydub operates in MILLISECONDS (int)
                                                start_ms = int(segment.get('start', 0.0) * 1000)
                                                end_ms = int(segment.get('end', 0.0) * 1000)
                                                segment_duration_ms = end_ms - start_ms
                                                
                                                speaker = segment.get('speaker', '')
                                                
                                                # Skip segments shorter than 1 second (too short to be meaningful)
                                                if segment_duration_ms < 1000:
                                                    print(f"⏭️  Skipping segment {i}: too short ({segment_duration_ms}ms < 1000ms)")
                                                    continue
                                                
                                                # Skip Speaker 1 (assumed to be the user/phone owner)
                                                if speaker and speaker.lower() in ['speaker 1', 'דובר 1', 'speaker a']:
                                                    print(f"⏭️  Skipping Speaker 1 (assumed to be User): {speaker}")
                                                    continue
                                                
                                                # AUTO-FILTER 1: Skip speakers that match our known voice signatures
                                                # If speaker name is in our Voice_Signatures folder, don't ask "Who is this?"
                                                speaker_lower = speaker.lower()
                                                if speaker_lower in known_speaker_names:
                                                    print(f"✅ Skipping segment {i}: Speaker '{speaker}' is in Voice_Signatures - already known!")
                                                    continue
                                                
                                                # AUTO-FILTER 2: Skip speakers that Gemini identified with a real name
                                                # If speaker name doesn't start with "Speaker" or "דובר", it means Gemini
                                                # matched the voice to a known reference voice - no need to ask "Who is this?"
                                                is_generic_speaker = (
                                                    speaker_lower.startswith('speaker ') or 
                                                    speaker.startswith('דובר ') or
                                                    speaker_lower.startswith('unknown') or
                                                    speaker_lower == ''
                                                )
                                                if speaker and not is_generic_speaker:
                                                    print(f"✅ Skipping segment {i}: Speaker '{speaker}' identified by Gemini - no need to ask!")
                                                    continue
                                                
                                                # Skip if we've already processed this speaker
                                                if speaker in processed_speakers:
                                                    print(f"⏭️  Skipping segment {i}: already sent sample for speaker '{speaker}'")
                                                    continue
                                                
                                                print(f"🔍 Processing segment {i} - Speaker: {speaker} at {segment.get('start', 0.0):.2f}s - {segment.get('end', 0.0):.2f}s (duration: {segment_duration_ms}ms)")
                                                
                                                # Ensure slice doesn't exceed audio bounds
                                                audio_length_ms = len(audio_segment)
                                                if start_ms < 0:
                                                    start_ms = 0
                                                if end_ms > audio_length_ms:
                                                    end_ms = audio_length_ms
                                                if start_ms >= end_ms:
                                                    print(f"⚠️  Invalid slice bounds after adjustment: {start_ms}ms - {end_ms}ms - skipping")
                                                    continue
                                                
                                                # STEP 3: Slicing - ensure at least 5 seconds, max 10 seconds
                                                try:
                                                    # Calculate slice bounds: ensure minimum 5 seconds
                                                    slice_start = start_ms
                                                    slice_end = end_ms
                                                    
                                                    # If segment is shorter than MIN_SLICE_MS, extend it
                                                    current_duration = slice_end - slice_start
                                                    if current_duration < MIN_SLICE_MS:
                                                        # Try to extend forward first
                                                        extension_needed = MIN_SLICE_MS - current_duration
                                                        new_end = min(slice_end + extension_needed, audio_length_ms)
                                                        
                                                        # If we couldn't extend enough forward, try extending backward
                                                        if (new_end - slice_start) < MIN_SLICE_MS:
                                                            backward_extension = MIN_SLICE_MS - (new_end - slice_start)
                                                            slice_start = max(0, slice_start - backward_extension)
                                                        
                                                        slice_end = new_end
                                                        print(f"   📏 Extended slice from {current_duration}ms to {slice_end - slice_start}ms (min {MIN_SLICE_MS}ms required)")
                                                    
                                                    # Cap at maximum duration
                                                    if (slice_end - slice_start) > MAX_SLICE_MS:
                                                        slice_end = slice_start + MAX_SLICE_MS
                                                    
                                                    # Perform the slice
                                                    audio_slice = audio_segment[slice_start : slice_end]
                                                    
                                                    # Verify slice length
                                                    slice_length_ms = len(audio_slice)
                                                    print(f"✂️  SLICING: {slice_start}ms - {slice_end}ms. Final duration: {slice_length_ms}ms")
                                                    
                                                    # Skip if still too short (couldn't extend enough)
                                                    if slice_length_ms < MIN_SLICE_MS:
                                                        print(f"⚠️  Slice still too short ({slice_length_ms}ms < {MIN_SLICE_MS}ms) - skipping")
                                                        continue
                                                    
                                                    print(f"✅ Slice created successfully: {slice_length_ms}ms ({slice_length_ms/1000:.1f}s)")
                                                    
                                                    unknown_speakers_found.append({
                                                        'segment_index': i,
                                                        'speaker': speaker,
                                                        'start': segment.get('start', 0.0),
                                                        'end': segment.get('end', 0.0),
                                                        'text': segment.get('text', '')
                                                    })
                                                    
                                                    # STEP 5: Export as MP3 (to satisfy WhatsApp) - with error handling
                                                    try:
                                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as slice_file:
                                                            audio_slice.export(slice_file.name, format='mp3')
                                                            slice_path = slice_file.name
                                                            
                                                            # Verify file was created and has content
                                                            if not os.path.exists(slice_path):
                                                                print(f"❌ ERROR: Exported MP3 file does not exist - skipping send")
                                                                continue
                                                            
                                                            file_size = os.path.getsize(slice_path)
                                                            print(f"   📁 Exported MP3 file: {file_size} bytes")
                                                            if file_size == 0:
                                                                print(f"❌ ERROR: Exported MP3 file is empty (0 bytes) - skipping send")
                                                                os.unlink(slice_path)
                                                                continue
                                                        
                                                        # Send audio clip to user with clean, user-friendly message
                                                        if not whatsapp_provider:
                                                            print(f"❌ WhatsApp provider not initialized - cannot send audio")
                                                        elif not hasattr(whatsapp_provider, 'send_audio'):
                                                            print(f"❌ WhatsApp provider does not support send_audio method")
                                                        else:
                                                            # PRODUCTION: Clean WhatsApp message - user-friendly prompt
                                                            caption = f"🔊 זוהה דובר חדש: *{speaker}*. מי זה/זו? (הגב עם השם)"
                                                            
                                                            print(f"📤 Attempting to send audio slice via {whatsapp_provider.get_provider_name()}...")
                                                            print(f"   Speaker: {speaker}, Duration: {slice_length_ms}ms")
                                                            audio_result = whatsapp_provider.send_audio(
                                                                audio_path=slice_path,
                                                                caption=caption,
                                                                to=f"+{from_number}"
                                                            )
                                                            
                                                            if audio_result.get('success'):
                                                                # IMPORTANT: User replies to the CAPTION message, not the audio message
                                                                # So we need to track the caption_message_id if it exists
                                                                caption_msg_id = audio_result.get('caption_message_id')
                                                                audio_msg_id = audio_result.get('wam_id') or audio_result.get('message_id')
                                                                
                                                                # Use caption message ID if available (user replies to caption), otherwise use audio message ID
                                                                sent_msg_id = caption_msg_id or audio_msg_id
                                                                
                                                                print(f"✅ Sent audio slice to user for speaker identification")
                                                                print(f"   Audio Message ID: {audio_msg_id}")
                                                                print(f"   Caption Message ID: {caption_msg_id}")
                                                                print(f"   Tracking Message ID (wam_id): {sent_msg_id}")
                                                                
                                                                # Store message_id -> file_path mapping for voice imprinting
                                                                # User will reply to the caption message, so we track that ID
                                                                if sent_msg_id:
                                                                    pending_identifications[sent_msg_id] = slice_path
                                                                    print(f"📝 Stored pending identification: {sent_msg_id} -> {slice_path}")
                                                                    print(f"   User will reply to this message ID to identify the speaker")
                                                                
                                                                # Mark this speaker as processed - we've sent their sample
                                                                processed_speakers.add(speaker)
                                                                print(f"✅ Added '{speaker}' to processed_speakers set")
                                                                
                                                                # IMPORTANT: Don't delete slice file immediately - keep it for voice imprinting
                                                                # File will be cleaned up after user replies with person name, or after timeout
                                                                print(f"📝 Keeping slice file for voice imprinting: {slice_path}")
                                                                # TODO: Add cleanup task for files older than X hours if user doesn't reply
                                                            else:
                                                                print(f"⚠️  Failed to send audio slice: {audio_result.get('error')}")
                                                                print(f"   Full error response: {audio_result}")
                                                                # Don't mark as processed if send failed - allow retry
                                                                
                                                                # If send failed, cleanup immediately
                                                                try:
                                                                    if os.path.exists(slice_path):
                                                                        os.unlink(slice_path)
                                                                        print(f"🗑️  Cleaned up slice file after failed send: {slice_path}")
                                                                except Exception as cleanup_error:
                                                                    print(f"⚠️  Failed to cleanup slice file: {cleanup_error}")
                                                            
                                                    except FileNotFoundError:
                                                        print(f"❌ ERROR: FFmpeg is likely missing on the server (during export).")
                                                        print(f"   Install FFmpeg: apt-get install ffmpeg (Linux) or brew install ffmpeg (Mac)")
                                                        if whatsapp_provider:
                                                            whatsapp_provider.send_whatsapp(
                                                                message="Error: Audio processing failed - FFmpeg missing (check logs).",
                                                                to=f"+{from_number}"
                                                            )
                                                        continue
                                                    except Exception as export_error:
                                                        print(f"❌ SLICING ERROR: Failed to export audio slice")
                                                        print(f"   Error: {export_error}")
                                                        import traceback
                                                        traceback.print_exc()
                                                        if whatsapp_provider:
                                                            whatsapp_provider.send_whatsapp(
                                                                message="Error: Audio processing failed (check logs).",
                                                                to=f"+{from_number}"
                                                            )
                                                        continue
                                                
                                                except FileNotFoundError:
                                                    print(f"❌ ERROR: FFmpeg is likely missing on the server (during slicing).")
                                                    print(f"   Install FFmpeg: apt-get install ffmpeg (Linux) or brew install ffmpeg (Mac)")
                                                    if whatsapp_provider:
                                                        whatsapp_provider.send_whatsapp(
                                                            message="Error: Audio processing failed - FFmpeg missing (check logs).",
                                                            to=f"+{from_number}"
                                                        )
                                                    continue
                                                except Exception as slicing_error:
                                                    print(f"❌ SLICING ERROR: {slicing_error}")
                                                    import traceback
                                                    traceback.print_exc()
                                                    if whatsapp_provider:
                                                        whatsapp_provider.send_whatsapp(
                                                            message="Error: Audio processing failed (check logs).",
                                                            to=f"+{from_number}"
                                                        )
                                                    continue
                                                
                                            if not unknown_speakers_found:
                                                print("✅ No unknown speakers detected - all speakers identified")
                                                
                                        except ImportError:
                                            print("⚠️  pydub not installed - cannot slice audio for speaker identification")
                                            print("   Install with: pip install pydub")
                                        except Exception as gemini_error:
                                            # Handle ALL errors from Gemini processing and pydub
                                            processing_error_occurred = True  # Mark that an error occurred
                                            print(f"❌ CRITICAL AUDIO ERROR: Gemini/audio processing failed: {gemini_error}")
                                            import traceback
                                            traceback.print_exc()
                                            
                                            # Still save the audio interaction without transcript/summary
                                            audio_interaction = {
                                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                                "type": "audio",
                                                "file_id": audio_metadata.get('file_id', ''),
                                                "web_content_link": audio_metadata.get('web_content_link', ''),
                                                "web_view_link": audio_metadata.get('web_view_link', ''),
                                                "filename": audio_metadata.get('filename', ''),
                                                "transcript": "",
                                                "summary": "Processing failed",
                                                "speakers": ["User", "Unknown"],
                                                "message_id": message_id,
                                                "from_number": from_number
                                            }
                                            
                                            drive_memory_service.update_memory(audio_interaction, background_tasks=background_tasks)
                                            
                                            # Send error message to user with more details
                                            error_type = type(gemini_error).__name__
                                            error_msg_short = str(gemini_error)[:80] if str(gemini_error) else "Unknown error"
                                            
                                            # Create user-friendly error message
                                            if "timeout" in error_msg_short.lower() or "timeout" in error_type.lower():
                                                user_error_msg = "⚠️  האודיו ארוך מדי או שהשרת עמוס. נסה שוב מאוחר יותר."
                                            elif "api" in error_msg_short.lower() or "key" in error_msg_short.lower():
                                                user_error_msg = "⚠️  בעיה בהגדרת Gemini API. אנא בדוק את הלוגים."
                                            else:
                                                user_error_msg = f"⚠️  שגיאה בעיבוד האודיו: {error_msg_short}"
                                            
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message=user_error_msg,
                                                    to=f"+{from_number}"
                                                )
                                            
                                            # Cleanup temp file
                                            try:
                                                os.unlink(tmp_path)
                                            except:
                                                pass
                                            
                                            # Cleanup temporary reference voice files
                                            for rv in reference_voices:
                                                try:
                                                    if os.path.exists(rv.get('file_path', '')):
                                                        os.unlink(rv['file_path'])
                                                except:
                                                    pass
                                        
                                        # Send confirmation message (only if processing succeeded, we have segments, and no error occurred)
                                        if segments and success and not processing_error_occurred:
                                            reply_message = f"🎤 הקלטה נשמרה!\n\n📝 {len(segments)} קטעים זוהו"
                                            if unknown_speakers_found:
                                                reply_message += f"\n🔍 {len(unknown_speakers_found)} דוברים לא מזוהים - נשלחו קטעי אודיו לזיהוי"
                                            
                                            reply_result = whatsapp_provider.send_whatsapp(
                                                message=reply_message,
                                                to=f"+{from_number}"
                                            )
                                            
                                            if reply_result.get('success'):
                                                print("✅ Confirmation sent to user")
                                            else:
                                                print(f"⚠️  Failed to send confirmation: {reply_result.get('error')}")
                                        elif not segments:
                                            print("⚠️  No segments to send confirmation - processing may have failed")
                                        
                                        if not success:
                                            print("⚠️  Failed to save audio interaction to memory")
                                        
                                        # Cleanup temp files (main audio and reference voices)
                                        try:
                                            os.unlink(tmp_path)
                                        except:
                                            pass
                                        
                                        # Cleanup temporary reference voice files
                                        for rv in reference_voices:
                                            try:
                                                if os.path.exists(rv.get('file_path', '')):
                                                    os.unlink(rv['file_path'])
                                                    print(f"🗑️  Cleaned up reference voice file: {rv['file_path']}")
                                            except Exception as cleanup_error:
                                                print(f"⚠️  Failed to cleanup reference voice file: {cleanup_error}")
                                        
                                    except Exception as audio_error:
                                        import traceback
                                        print("=" * 60)
                                        print("❌ RAW ERROR TYPE:", type(audio_error).__name__)
                                        print("❌ RAW ERROR MESSAGE:", str(audio_error))
                                        print("=" * 60)
                                        print("FULL TRACEBACK:")
                                        print("=" * 60)
                                        traceback.print_exc()
                                        print("=" * 60)
                                
                                # Process message with memory
                                elif whatsapp_provider and message_type == "text" and message_body_text:
                                    try:
                                        # CRITICAL: Get memory at the very start to trigger cache refresh check
                                        # This ensures we detect manual edits before processing the message
                                        memory = drive_memory_service.get_memory()
                                        chat_history = memory.get('chat_history', [])
                                        user_profile = memory.get('user_profile', {})
                                        
                                        print(f"💾 Retrieved memory: {len(chat_history)} previous interactions")
                                        if user_profile:
                                            print(f"👤 User profile loaded: {list(user_profile.keys())}")
                                        
                                        # Check if this is a HISTORY QUERY (asking about past conversations)
                                        if is_history_query(message_body_text):
                                            print(f"🔍 Detected HISTORY QUERY: {message_body_text[:50]}...")
                                            
                                            # Search through chat history for relevant transcripts
                                            history_context = search_history_for_context(chat_history, message_body_text)
                                            
                                            if history_context:
                                                print(f"📚 Found relevant history context ({len(history_context)} chars)")
                                            else:
                                                print(f"📚 No relevant history found for query")
                                            
                                            # Generate answer using Gemini
                                            ai_response = gemini_service.answer_history_query(
                                                user_query=message_body_text,
                                                history_context=history_context,
                                                user_profile=user_profile
                                            )
                                        else:
                                            # Regular chat: Generate AI response with context and user profile
                                            ai_response = gemini_service.chat_with_memory(
                                                user_message=message_body_text,
                                                chat_history=chat_history,
                                                user_profile=user_profile
                                            )
                                        
                                        print(f"🤖 Generated AI response: {ai_response[:100]}...")
                                        
                                        # Send AI response via WhatsApp
                                        reply_result = whatsapp_provider.send_whatsapp(
                                            message=ai_response,
                                            to=f"+{from_number}"  # Add + prefix for E.164 format
                                        )
                                        
                                        if reply_result.get('success'):
                                            print(f"✅ AI response sent successfully")
                                            
                                            # Save interaction to memory (cache updated immediately, Drive sync in background)
                                            new_interaction = {
                                                "user_message": message_body_text,
                                                "ai_response": ai_response,
                                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                                "message_id": message_id,
                                                "from_number": from_number
                                            }
                                            
                                            # Update cache immediately, sync to Drive in background
                                            success = drive_memory_service.update_memory(new_interaction, background_tasks=background_tasks)
                                            if success:
                                                print(f"✅ Saved interaction to memory cache (Drive sync in background)")
                                            else:
                                                print(f"⚠️  Failed to save interaction to memory")
                                        else:
                                            print(f"⚠️  Failed to send AI response: {reply_result.get('error')}")
                                    except Exception as reply_error:
                                        print(f"⚠️  Error processing message with AI: {reply_error}")
                                        import traceback
                                        traceback.print_exc()
                                        
                                        # Fallback: Send simple acknowledgment
                                        try:
                                            fallback_message = "Message received and saved to memory."
                                            whatsapp_provider.send_whatsapp(
                                                message=fallback_message,
                                                to=f"+{from_number}"
                                            )
                                        except:
                                            pass
                        
                        # Handle message status updates
                        elif field == "messages" and "statuses" in value:
                            statuses = value.get("statuses", [])
                            for status in statuses:
                                message_id = status.get("id")
                                status_type = status.get("status")
                                recipient = status.get("recipient_id")
                                
                                print(f"📊 Message Status Update:")
                                print(f"   Message ID: {message_id}")
                                print(f"   Status: {status_type}")
                                print(f"   Recipient: {recipient}")
                                
                                if status_type == "failed":
                                    error = status.get("errors", [{}])[0]
                                    error_code = error.get("code")
                                    error_title = error.get("title")
                                    print(f"   ❌ Error: {error_title} (Code: {error_code})")
                                elif status_type == "delivered":
                                    print(f"   ✅ Message delivered!")
                                elif status_type == "read":
                                    print(f"   ✅ Message read!")
            
            # Return 200 immediately (acknowledge receipt)
            return JSONResponse(content={"status": "ok"})
            
        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            import traceback
            traceback.print_exc()
            # Still return 200 to avoid retries
            return JSONResponse(content={"status": "error", "message": str(e)})


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming WhatsApp messages and webhooks.
    Supports both Twilio (form data) and Meta (JSON) webhooks.
    """
    try:
        content_type = request.headers.get("content-type", "")
        
        # Check if it's Meta WhatsApp webhook (JSON)
        if "application/json" in content_type:
            data = await request.json()
            
            # Meta webhook structure
            if "entry" in data:
                print(f"\n{'='*60}")
                print(f"📱 Meta WhatsApp Webhook Received")
                print(f"{'='*60}")
                
                for entry in data.get("entry", []):
                    changes = entry.get("changes", [])
                    for change in changes:
                        value = change.get("value", {})
                        
                        # Message status updates
                        if "statuses" in value:
                            statuses = value.get("statuses", [])
                            for status in statuses:
                                message_id = status.get("id")
                                status_type = status.get("status")
                                recipient = status.get("recipient_id")
                                
                                print(f"📊 Message Status Update:")
                                print(f"   Message ID: {message_id}")
                                print(f"   Status: {status_type}")
                                print(f"   Recipient: {recipient}")
                                
                                if status_type == "failed":
                                    error = status.get("errors", [{}])[0]
                                    error_code = error.get("code")
                                    error_title = error.get("title")
                                    print(f"   ❌ Error: {error_title} (Code: {error_code})")
                                
                                if status_type == "delivered":
                                    print(f"   ✅ Message delivered!")
                                
                                if status_type == "read":
                                    print(f"   ✅ Message read!")
                        
                        # Incoming messages
                        if "messages" in value:
                            messages = value.get("messages", [])
                            for message in messages:
                                from_number = message.get("from")
                                message_body = message.get("text", {}).get("body", "")
                                message_id = message.get("id")
                                
                                print(f"📨 Incoming Message:")
                                print(f"   From: {from_number}")
                                print(f"   Message: {message_body}")
                                print(f"   Message ID: {message_id}")
                                
                                # IDEMPOTENCY CHECK: Prevent duplicate processing due to webhook retries
                                if is_message_processed(message_id):
                                    print(f"⚠️  Duplicate message received (ID: {message_id}). Ignoring.")
                                    continue  # Skip processing, but return 200 OK to WhatsApp
                                
                                # Mark message as processed BEFORE processing (prevents race conditions)
                                mark_message_processed(message_id)
                                
                                # TODO: Add auto-reply here if needed
                                # You can send a response using whatsapp_provider.send_whatsapp()
                
                print(f"{'='*60}\n")
                return JSONResponse(content={"status": "ok"})
        
        # Twilio webhook (form data)
        form_data = await request.form()
        sender_number = form_data.get('From', '')
        message_body = form_data.get('Body', '')
        # Twilio uses MessageSid as the unique message ID
        message_id = form_data.get('MessageSid', '') or form_data.get('MessageId', '')
        
        print(f"\n{'='*50}")
        print(f"📱 Incoming WhatsApp Message (Twilio)")
        print(f"{'='*50}")
        print(f"From: {sender_number}")
        print(f"Message: {message_body}")
        print(f"Message ID: {message_id}")
        print(f"{'='*50}\n")
        
        # IDEMPOTENCY CHECK: Prevent duplicate processing due to webhook retries
        if message_id and is_message_processed(message_id):
            print(f"⚠️  Duplicate message received (ID: {message_id}). Ignoring.")
            # Return 200 OK to Twilio to acknowledge receipt
            from twilio.twiml.messaging_response import MessagingResponse
            response = MessagingResponse()
            return Response(content=str(response), media_type='text/xml')
        
        # Mark message as processed BEFORE processing (prevents race conditions)
        if message_id:
            mark_message_processed(message_id)
        
        # Process message with memory (if message body exists)
        if message_body and drive_memory_service.is_configured:
            try:
                # CRITICAL: Get memory at the very start to trigger cache refresh check
                # This ensures we detect manual edits before processing the message
                memory = drive_memory_service.get_memory()
                chat_history = memory.get('chat_history', [])
                user_profile = memory.get('user_profile', {})
                
                print(f"💾 Retrieved memory: {len(chat_history)} previous interactions")
                if user_profile:
                    print(f"👤 User profile loaded: {list(user_profile.keys())}")
                
                # Generate AI response with context and user profile
                ai_response = gemini_service.chat_with_memory(
                    user_message=message_body,
                    chat_history=chat_history,
                    user_profile=user_profile
                )
                
                print(f"🤖 Generated AI response: {ai_response[:100]}...")
                
                # Save interaction to memory (cache updated immediately, Drive sync in background)
                new_interaction = {
                    "user_message": message_body,
                    "ai_response": ai_response,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "from_number": sender_number
                }
                
                # Update cache immediately, sync to Drive in background
                success = drive_memory_service.update_memory(new_interaction, background_tasks=background_tasks)
                if success:
                    print(f"✅ Saved interaction to memory cache (Drive sync in background)")
                else:
                    print(f"⚠️  Failed to save interaction to memory")
                
                # Return TwiML response with AI reply
                from twilio.twiml.messaging_response import MessagingResponse
                response = MessagingResponse()
                response.message(ai_response)
                return Response(content=str(response), media_type='text/xml')
            except Exception as e:
                print(f"⚠️  Error processing message with AI: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: Return simple acknowledgment
        from twilio.twiml.messaging_response import MessagingResponse
        response = MessagingResponse()
        response.message('Message received and saved to memory.')
        return Response(content=str(response), media_type='text/xml')
        
    except Exception as e:
        print(f"❌ Error processing WhatsApp webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to return appropriate response
        try:
            from twilio.twiml.messaging_response import MessagingResponse
            response = MessagingResponse()
            response.message('Sorry, an error occurred while processing your message.')
            return Response(content=str(response), media_type='text/xml')
        except:
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    """
    Generate a PDF report from analysis results.
    
    Expects JSON body with the analysis data.
    """
    try:
        # Get JSON data from request
        data = await request.json()
        
        # Generate PDF
        pdf_path = pdf_service.create_pdf(data)
        
        # Return PDF file
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=f"second-brain-analysis-{data.get('date', 'report')}.pdf",
            headers={
                "Content-Disposition": f"attachment; filename=second-brain-analysis-{data.get('date', 'report')}.pdf"
            }
        )
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@app.post("/analyze")
async def analyze_day(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Analyze a day's worth of inputs using Gemini 1.5 Pro.
    
    - **audio_files**: Audio files (MP3, WAV, M4A, etc.)
    - **image_files**: Image files (JPG, PNG)
    - **text_notes**: Text notes (newline-separated or JSON array)
    
    Returns structured JSON analysis with three expert perspectives.
    """
    temp_files = []
    
    try:
        # Parse multipart form data
        form = await request.form()
        
        print(f"[ANALYZE] Request received")
        print(f"[ANALYZE] Content-Type: {request.headers.get('content-type', 'N/A')}")
        print(f"[ANALYZE] Form keys: {list(form.keys())}")
        
        # Get all files from form
        audio_paths = []
        image_paths = []
        audio_files_list = []
        image_files_list = []
        
        # Process all form items - check getlist for multiple files with same name
        if 'audio_files' in form:
            audio_files_list = form.getlist('audio_files')
            print(f"[ANALYZE] Found {len(audio_files_list)} audio files via getlist")
        
        if 'image_files' in form:
            image_files_list = form.getlist('image_files')
            print(f"[ANALYZE] Found {len(image_files_list)} image files via getlist")
        
        # Get text notes
        text_notes = form.get('text_notes', None)
        
        print(f"[ANALYZE] Audio files: {len(audio_files_list)}")
        print(f"[ANALYZE] Image files: {len(image_files_list)}")
        print(f"[ANALYZE] Text notes: {text_notes[:100] if text_notes else 'None'}...")
        
        # Parse text notes
        text_inputs = []
        if text_notes:
            # Try to parse as JSON array first
            try:
                import json
                text_inputs = json.loads(text_notes)
                if not isinstance(text_inputs, list):
                    text_inputs = [text_notes]
            except:
                # If not JSON, split by newlines
                text_inputs = [note.strip() for note in text_notes.split('\n') if note.strip()]
        
        print(f"[ANALYZE] Parsed text inputs: {len(text_inputs)}")
        
        # Process audio files - upload to Drive archive first, then process with Gemini
        print(f"[ANALYZE] Processing {len(audio_files_list)} audio files...")
        audio_file_metadata = []  # Store Drive file metadata for each audio file
        
        for i, audio_file in enumerate(audio_files_list):
            print(f"[ANALYZE] Audio file {i+1}: type={type(audio_file)}, has read={hasattr(audio_file, 'read')}, has filename={hasattr(audio_file, 'filename')}")
            # Check if it has the methods we need (read, filename) - this works for any UploadFile-like object
            if hasattr(audio_file, 'read') and hasattr(audio_file, 'filename'):
                print(f"[ANALYZE] ✅ Has read() and filename - treating as UploadFile")
                print(f"[ANALYZE] Processing UploadFile: {audio_file.filename}")
                
                # Create temp file
                suffix = Path(audio_file.filename).suffix if audio_file.filename else '.mp3'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    content = await audio_file.read()
                    tmp_file.write(content)
                    tmp_path = tmp_file.name
                    temp_files.append(tmp_path)
                    audio_paths.append(tmp_path)
                    print(f"📥 Saved audio: {audio_file.filename} -> {tmp_path}")
                
                # Upload to Drive archive (The Vault)
                if drive_memory_service.is_configured:
                    try:
                        print(f"📤 Uploading audio to Drive archive: {audio_file.filename}")
                        archive_metadata = drive_memory_service.upload_audio_to_archive(
                            audio_path=tmp_path,
                            filename=audio_file.filename
                        )
                        if archive_metadata:
                            audio_file_metadata.append(archive_metadata)
                            print(f"✅ Audio archived: file_id={archive_metadata.get('file_id')}")
                        else:
                            print(f"⚠️  Failed to archive audio file, continuing with analysis...")
                    except Exception as e:
                        print(f"⚠️  Error archiving audio: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue with analysis even if archiving fails
            else:
                print(f"[ANALYZE] ⚠️  Audio file {i+1} doesn't have read() or filename")
                print(f"[ANALYZE] ⚠️  Attributes: {[attr for attr in dir(audio_file) if not attr.startswith('_')][:10]}")
        
        # Process image files
        for image_file in image_files_list:
            if hasattr(image_file, 'read') and hasattr(image_file, 'filename'):
                # Create temp file
                suffix = Path(image_file.filename).suffix if image_file.filename else '.jpg'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    content = await image_file.read()
                    tmp_file.write(content)
                    tmp_path = tmp_file.name
                    temp_files.append(tmp_path)
                    image_paths.append(tmp_path)
                    print(f"📥 Saved image: {image_file.filename} -> {tmp_path}")
        
        print(f"[ANALYZE] Final counts - Audio paths: {len(audio_paths)}, Image paths: {len(image_paths)}, Text inputs: {len(text_inputs)}")
        
        # Check if we have any inputs
        if not audio_paths and not image_paths and not text_inputs:
            print(f"[ANALYZE] ❌ No inputs provided - raising 400 error")
            raise HTTPException(
                status_code=400,
                detail="No inputs provided. Please provide at least one audio file, image file, or text note."
            )
        
        # Analyze using Gemini
        print(f"🔍 Starting Gemini analysis...")
        print(f"   Audio files: {len(audio_paths)}")
        print(f"   Image files: {len(image_paths)}")
        print(f"   Text inputs: {len(text_inputs)}")
        
        # Retrieve voice signatures for speaker identification (if we have audio files)
        reference_voices = []
        if audio_paths and drive_memory_service.is_configured:
            try:
                print("🎤 Retrieving voice signatures for speaker identification...")
                reference_voices = drive_memory_service.get_voice_signatures()
                if reference_voices:
                    print(f"✅ Retrieved {len(reference_voices)} voice signature(s): {[rv['name'] for rv in reference_voices]}")
                else:
                    print("ℹ️  No voice signatures found - will use generic speaker IDs")
            except Exception as voice_sig_error:
                print(f"⚠️  Error retrieving voice signatures: {voice_sig_error}")
                import traceback
                traceback.print_exc()
                # Continue without voice signatures
                reference_voices = []
        
        try:
            result = gemini_service.analyze_day(
                audio_paths=audio_paths,
                image_paths=image_paths,
                text_inputs=text_inputs,
                audio_file_metadata=audio_file_metadata,
                reference_voices=reference_voices
            )
            print(f"✅ Gemini analysis complete")
            
            # If we have audio files, save structured audio interaction to memory
            if audio_paths and drive_memory_service.is_configured and result.get('type') == 'audio_analysis':
                try:
                    # Extract transcript and summary from result
                    transcript = result.get('transcript', {})
                    summary = result.get('summary', '')
                    
                    # Extract unique speaker names from segments for searchability
                    segments = transcript.get('segments', []) if isinstance(transcript, dict) else []
                    speaker_names = set()
                    for segment in segments:
                        speaker = segment.get('speaker', '') if isinstance(segment, dict) else ''
                        if speaker and not speaker.lower().startswith('speaker '):
                            # Only add actual names, not generic "Speaker 1", "Speaker 2", etc.
                            speaker_names.add(speaker)
                    speaker_names = list(speaker_names) if speaker_names else ["User", "Unknown"]
                    
                    # Create structured audio interaction entry
                    for i, audio_meta in enumerate(audio_file_metadata):
                        audio_interaction = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "type": "audio",
                            "file_id": audio_meta.get('file_id', ''),
                            "web_content_link": audio_meta.get('web_content_link', ''),
                            "web_view_link": audio_meta.get('web_view_link', ''),
                            "filename": audio_meta.get('filename', ''),
                            "transcript": transcript if i == 0 else {},  # Use same transcript for all files in batch
                            "summary": summary if i == 0 else "",  # Use same summary for all files in batch
                            "speakers": speaker_names  # List of identified speaker names for searchability
                        }
                        
                        # Save to memory
                        success = drive_memory_service.update_memory(audio_interaction, background_tasks=background_tasks)
                        if success:
                            print(f"✅ Saved audio interaction to memory: {audio_meta.get('filename')}")
                        else:
                            print(f"⚠️  Failed to save audio interaction to memory")
                except Exception as e:
                    print(f"⚠️  Error saving audio interaction to memory: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Send summary via WhatsApp and SMS if configured
            try:
                # Format the summary message (using TwilioService formatter, works for all providers)
                formatted_message = twilio_service.format_summary_message(result)
                
                results = {
                    "whatsapp": None,
                    "sms": None
                }
                
                # Send WhatsApp via configured provider (Twilio or Meta)
                if whatsapp_provider:
                    try:
                        # Get recipient - for Meta we need it, for Twilio it's optional
                        whatsapp_recipient = None
                        if whatsapp_provider.get_provider_name() == 'meta':
                            whatsapp_recipient = settings.whatsapp_to
                            if not whatsapp_recipient:
                                print(f"⚠️  WHATSAPP_TO not set - required for Meta provider")
                                results["whatsapp"] = {
                                    "success": False,
                                    "error": "WHATSAPP_TO not configured",
                                    "message": "Meta WhatsApp requires WHATSAPP_TO environment variable"
                                }
                            else:
                                print(f"📱 Sending WhatsApp via Meta to {whatsapp_recipient}")
                                whatsapp_result = whatsapp_provider.send_whatsapp(formatted_message, whatsapp_recipient)
                                results["whatsapp"] = whatsapp_result
                                if whatsapp_result.get('success'):
                                    print(f"✅ Summary sent to WhatsApp successfully via {whatsapp_provider.get_provider_name()}")
                                else:
                                    print(f"⚠️  Failed to send WhatsApp: {whatsapp_result.get('error', 'Unknown error')}")
                                    print(f"   Full error details: {whatsapp_result}")
                        else:
                            # Twilio provider
                            print(f"📱 Sending WhatsApp via Twilio")
                            whatsapp_result = whatsapp_provider.send_whatsapp(formatted_message, whatsapp_recipient)
                            results["whatsapp"] = whatsapp_result
                            if whatsapp_result.get('success'):
                                print(f"✅ Summary sent to WhatsApp successfully via {whatsapp_provider.get_provider_name()}")
                            else:
                                print(f"⚠️  Failed to send WhatsApp: {whatsapp_result.get('error', 'Unknown error')}")
                    except Exception as whatsapp_error:
                        print(f"⚠️  Error sending WhatsApp: {whatsapp_error}")
                        import traceback
                        traceback.print_exc()
                        results["whatsapp"] = {
                            "success": False,
                            "error": str(whatsapp_error),
                            "message": "Exception occurred while sending WhatsApp"
                        }
                else:
                    print(f"⚠️  WhatsApp provider not configured")
                    results["whatsapp"] = {
                        "success": False,
                        "error": "WhatsApp provider not configured",
                        "message": "Please configure WhatsApp provider in environment variables"
                    }
                
                # Send SMS via Twilio (SMS is only supported by Twilio)
                # Only send SMS if explicitly enabled
                if settings.enable_sms and twilio_service.is_configured_flag and settings.twilio_sms_from:
                    try:
                        sms_result = twilio_service.send_sms(formatted_message)
                        results["sms"] = sms_result
                        if sms_result.get('success'):
                            print(f"✅ Summary sent to SMS successfully")
                        else:
                            print(f"⚠️  Failed to send SMS: {sms_result.get('error', 'Unknown error')}")
                    except Exception as sms_error:
                        print(f"⚠️  Error sending SMS: {sms_error}")
                else:
                    if not settings.enable_sms:
                        print(f"ℹ️  SMS sending is disabled (ENABLE_SMS=false)")
                    results["sms"] = {"success": False, "message": "SMS sending is disabled"}
                
            except Exception as messaging_error:
                print(f"⚠️  Error sending messages (non-fatal): {messaging_error}")
                import traceback
                traceback.print_exc()
                # Don't fail the request if messaging fails
            
        except Exception as gemini_error:
            print(f"❌ Gemini analysis error: {gemini_error}")
            import traceback
            traceback.print_exc()
            raise
        
        # Cleanup uploaded files from Google storage
        # Temporarily disabled to debug the 40 character error
        # gemini_service.cleanup_files()
        print("⚠️  Cleanup disabled for debugging")
        
        return JSONResponse(content=result)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Cleanup on error
        # Temporarily disabled to debug the 40 character error
        # gemini_service.cleanup_files()
        print(f"❌ Error processing request: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    
    finally:
        # Cleanup temp files (including reference voice files)
        for tmp_path in temp_files:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    print(f"🗑️  Deleted temp file: {tmp_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete temp file {tmp_path}: {e}")
        
        # Cleanup temporary reference voice files
        if 'reference_voices' in locals():
            for rv in reference_voices:
                try:
                    if os.path.exists(rv.get('file_path', '')):
                        os.unlink(rv['file_path'])
                        print(f"🗑️  Cleaned up reference voice file: {rv['file_path']}")
                except Exception as cleanup_error:
                    print(f"⚠️  Failed to cleanup reference voice file: {cleanup_error}")


if __name__ == "__main__":
    import uvicorn
    import sys
    import logging
    
    # Setup logging to file
    log_file = Path(__file__).parent.parent / "server.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    port = int(os.getenv("PORT", settings.port))
    print(f"📝 Logging to: {log_file}")
    uvicorn.run(
        app,
        host=settings.host,
        port=port,
        reload=settings.debug,
        log_config=None  # Use our custom logging
    )
