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
from pathlib import Path
from datetime import datetime

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
                                message_body = message.get("text", {}).get("body", "")
                                message_id = message.get("id")
                                message_type = message.get("type")
                                timestamp = message.get("timestamp")
                                
                                print(f"📨 Processing Incoming Message:")
                                print(f"   From: {from_number}")
                                print(f"   Message: {message_body}")
                                print(f"   Message ID: {message_id}")
                                print(f"   Type: {message_type}")
                                print(f"   Timestamp: {timestamp}")
                                
                                # Process message with memory
                                if whatsapp_provider and message_type == "text" and message_body:
                                    try:
                                        # CRITICAL: Get memory at the very start to trigger cache refresh check
                                        # This ensures we detect manual edits before processing the message
                                        memory = drive_memory_service.get_memory()
                                        chat_history = memory.get('chat_history', [])
                                        
                                        print(f"💾 Retrieved memory: {len(chat_history)} previous interactions")
                                        
                                        # Generate AI response with context
                                        ai_response = gemini_service.chat_with_memory(
                                            user_message=message_body,
                                            chat_history=chat_history
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
                                                "user_message": message_body,
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
                                
                                # TODO: Add auto-reply here if needed
                                # You can send a response using whatsapp_provider.send_whatsapp()
                
                print(f"{'='*60}\n")
                return JSONResponse(content={"status": "ok"})
        
        # Twilio webhook (form data)
        form_data = await request.form()
        sender_number = form_data.get('From', '')
        message_body = form_data.get('Body', '')
        
        print(f"\n{'='*50}")
        print(f"📱 Incoming WhatsApp Message (Twilio)")
        print(f"{'='*50}")
        print(f"From: {sender_number}")
        print(f"Message: {message_body}")
        print(f"{'='*50}\n")
        
        # Process message with memory (if message body exists)
        if message_body and drive_memory_service.is_configured:
            try:
                # CRITICAL: Get memory at the very start to trigger cache refresh check
                # This ensures we detect manual edits before processing the message
                memory = drive_memory_service.get_memory()
                chat_history = memory.get('chat_history', [])
                
                print(f"💾 Retrieved memory: {len(chat_history)} previous interactions")
                
                # Generate AI response with context
                ai_response = gemini_service.chat_with_memory(
                    user_message=message_body,
                    chat_history=chat_history
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
    request: Request
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
        
        # Process audio files - use duck typing (check for read() and filename)
        print(f"[ANALYZE] Processing {len(audio_files_list)} audio files...")
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
        
        try:
            result = gemini_service.analyze_day(
                audio_paths=audio_paths,
                image_paths=image_paths,
                text_inputs=text_inputs
            )
            print(f"✅ Gemini analysis complete")
            
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
        # Cleanup temp files
        for tmp_path in temp_files:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    print(f"🗑️  Deleted temp file: {tmp_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete temp file {tmp_path}: {e}")


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
