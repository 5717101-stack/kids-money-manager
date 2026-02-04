# Technical State Report: Second Brain - Gemini Edition

**Version:** 2.3.0  
**Generated:** 2025-02-04  
**Project:** Second Brain - Daily Sync (Gemini Edition)

---

## 1. Project Structure

```
second-brain-gemini/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── prompts.py                 # System prompts for Gemini AI
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Configuration & environment variables
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py      # Google Gemini AI integration
│   │   ├── pdf_service.py         # PDF report generation
│   │   ├── twilio_service.py      # Twilio WhatsApp/SMS service
│   │   ├── meta_whatsapp_service.py  # Meta WhatsApp Cloud API service
│   │   └── whatsapp_provider.py   # Provider factory pattern
│   └── fonts/
│       └── ArialUnicode.ttf        # Hebrew font for PDF
├── static/
│   └── index.html                 # Web UI frontend
├── process_meetings.py             # Background cron job for Google Drive
├── check_token.py                 # Utility for token validation
├── requirements.txt               # Python dependencies
├── Procfile                       # Deployment configuration
├── render.yaml                    # Render.com deployment config
├── VERSION                        # Current version (2.3.0)
└── [Documentation files]
```

---

## 2. Tech Stack

### Core Framework
- **FastAPI** (0.115.0) - Modern Python web framework
- **Uvicorn** (0.32.0) - ASGI server
- **Pydantic** (2.10.0) - Data validation and settings management

### AI & ML
- **google-generativeai** (>=0.3.0) - Google Gemini AI integration
  - Model: `gemini-2.5-pro` (mapped from `gemini-1.5-pro-latest`)
  - Supports multimodal input (audio, images, text)

### Communication Services
- **Twilio** (9.3.0) - WhatsApp & SMS messaging
- **requests** (>=2.31.0) - HTTP client for Meta WhatsApp Cloud API

### Document Generation
- **reportlab** (4.0.7) - PDF generation
- **python-bidi** (0.4.2) - Hebrew RTL text support

### Google Services
- **google-api-python-client** (2.144.0) - Google Drive API
- **google-auth** (2.35.0) - Google authentication

### Utilities
- **python-dotenv** (1.0.0) - Environment variable management
- **python-dateutil** (2.8.2) - Date/time utilities

---

## 3. Architecture & Data Flow

### Request Flow: WhatsApp Webhook

#### Meta WhatsApp Cloud API Flow:

```
1. User sends message → Meta WhatsApp Cloud API
2. Meta sends webhook POST → /webhook endpoint
3. FastAPI receives JSON payload:
   {
     "object": "whatsapp_business_account",
     "entry": [{
       "changes": [{
         "value": {
           "messages": [{...}],
           "statuses": [{...}]
         }
       }]
     }]
   }
4. Endpoint extracts:
   - Message: from_number, message_body, message_id, type, timestamp
   - Status: message_id, status_type (delivered/read/failed)
5. Processes message (logs, optional auto-reply)
6. Returns 200 OK immediately (acknowledgment)
```

#### Twilio WhatsApp Flow:

```
1. User sends message → Twilio
2. Twilio sends webhook POST → /whatsapp endpoint (form data)
3. FastAPI extracts:
   - From: request.form.get('From')
   - Body: request.form.get('Body')
4. Logs message
5. Returns TwiML response: "Message received and saved to memory."
```

### Analysis Flow: `/analyze` Endpoint

```
1. Client uploads files (audio/images/text) → POST /analyze
2. Files saved to temp directory
3. Files uploaded to Google Gemini File API
4. Wait for processing (state='ACTIVE')
5. Build prompt with:
   - System prompt (3 expert personas)
   - Text inputs
   - File references
6. Call Gemini API: model.generate_content(contents)
7. Parse JSON response (with error fixing for incomplete JSON)
8. Format summary message
9. Send via WhatsApp (configured provider) and SMS (if enabled)
10. Generate PDF (optional)
11. Cleanup: Delete temp files and Gemini uploaded files
12. Return analysis result
```

---

## 4. Core Logic Breakdown

### Main Application (`app/main.py`)

#### Key Endpoints:

1. **`GET /`** - Serves web interface (`static/index.html`)
2. **`GET /health`** - Health check endpoint
3. **`GET /version`** - Returns current version from `VERSION` file
4. **`GET /whatsapp-provider-status`** - Shows active WhatsApp provider and configuration
5. **`POST /test-whatsapp`** - Test WhatsApp sending
6. **`POST /test-sms`** - Test SMS sending
7. **`GET /webhook`** - Meta WhatsApp webhook verification
8. **`POST /webhook`** - Meta WhatsApp webhook handler (messages & statuses)
9. **`GET /whatsapp`** - Meta WhatsApp webhook verification (alternative)
10. **`POST /whatsapp`** - Unified webhook (Twilio + Meta)
11. **`POST /analyze`** - Main analysis endpoint (multimodal input)
12. **`POST /generate-pdf`** - Generate PDF from analysis result

### Service Modules

#### `app/services/gemini_service.py`
- **Purpose:** Google Gemini AI integration
- **Key Methods:**
  - `analyze_day()` - Main analysis function
    - Uploads files to Gemini File API
    - Waits for processing (state='ACTIVE')
    - Calls `model.generate_content()` with multimodal content
    - Parses JSON response with error recovery
  - `upload_and_wait()` - Upload file and wait for processing
  - `cleanup_files()` - Delete uploaded files from Gemini storage
- **Features:**
  - Automatic JSON error fixing (incomplete JSON, trailing commas)
  - Retry logic for connection errors
  - 10-minute timeout for large files

#### `app/services/pdf_service.py`
- **Purpose:** Generate PDF reports from analysis results
- **Features:**
  - Hebrew RTL text support (python-bidi)
  - Three-section layout (Leadership, Strategy, Parenting)
  - Custom Hebrew font (ArialUnicode.ttf)

#### `app/services/whatsapp_provider.py`
- **Purpose:** Provider factory pattern for WhatsApp services
- **Architecture:**
  - Abstract base class: `WhatsAppProvider`
  - Factory: `WhatsAppProviderFactory`
  - Implementations: `TwilioService`, `MetaWhatsAppService`
- **Features:**
  - Dynamic provider selection via `WHATSAPP_PROVIDER` env var
  - Automatic fallback to Twilio if Meta not configured
  - Lazy loading to avoid circular imports

#### `app/services/twilio_service.py`
- **Purpose:** Twilio WhatsApp & SMS integration
- **Methods:**
  - `send_whatsapp()` - Send WhatsApp via Twilio
  - `send_sms()` - Send SMS
  - `format_summary_message()` - Format analysis for messaging

#### `app/services/meta_whatsapp_service.py`
- **Purpose:** Meta WhatsApp Cloud API integration
- **Methods:**
  - `send_whatsapp()` - Send WhatsApp via Meta API
  - `_refresh_access_token()` - Automatic token refresh
  - `_check_token_info()` - Validate token type and expiration
  - `verify_webhook()` - Webhook verification
- **Features:**
  - Automatic token refresh (if App ID + Secret configured)
  - Token expiration detection
  - Error handling with retry logic

#### `app/core/config.py`
- **Purpose:** Centralized configuration management
- **Uses:** Pydantic Settings for environment variable validation
- **Key Settings:**
  - Google Gemini API key
  - WhatsApp provider selection (twilio/meta)
  - Twilio credentials
  - Meta WhatsApp credentials
  - SMS enable/disable flag

#### `app/prompts.py`
- **Purpose:** System prompts for Gemini AI
- **Content:** Hebrew-language prompt defining 3 expert personas:
  1. Simon Sinek (Leadership)
  2. High-Tech Strategy Consultant
  3. Adler Institute (Parenting)

---

## 5. Memory & Context Handling

### Current State: **NO PERSISTENT MEMORY**

**Critical Finding:** The application does **NOT** store conversation history or context between requests.

#### How "Memory" Currently Works:

1. **Per-Request Context Only:**
   - Each `/analyze` request is independent
   - Gemini receives only the current session's inputs (audio/images/text)
   - No conversation history is maintained

2. **System Prompt Context:**
   - The `SYSTEM_PROMPT` in `app/prompts.py` provides expert persona definitions
   - This is static and sent with every request
   - No dynamic context accumulation

3. **File Storage:**
   - Files are uploaded to **Google Gemini File API** (temporary)
   - Files are deleted after analysis via `cleanup_files()`
   - No local or cloud storage of analysis results

4. **Response Handling:**
   - Analysis results are:
     - Returned to client (JSON)
     - Sent via WhatsApp/SMS (formatted text)
     - Optionally generated as PDF (temporary file, returned to client)
   - **No database storage**
   - **No Google Drive storage of results**
   - **No conversation history**

#### Implications:

- **No Multi-Turn Conversations:** Each request is isolated
- **No Historical Context:** Cannot reference previous analyses
- **No User Profiles:** No persistent user data or preferences
- **No Memory of Past Interactions:** WhatsApp messages are logged but not stored

#### Potential Storage Solutions (Not Currently Implemented):

The codebase includes references to:
- **Google Drive API** (`process_meetings.py`) - Used only for background cron job
- **MongoDB** (in `daily-sync-backend`) - Different project, not used here
- **ChromaDB** (in `daily-sync-backend`) - Different project, not used here

**Recommendation:** To add memory, consider:
1. Database (PostgreSQL/MongoDB) for analysis results
2. Vector store (ChromaDB/Pinecone) for semantic search
3. Google Drive API for document storage
4. Conversation history in database

---

## 6. Integrations

### 6.1 Google Gemini AI

**Purpose:** Multimodal AI analysis (audio, images, text)

**Authentication:**
- Environment variable: `GOOGLE_API_KEY`
- Configured via: `genai.configure(api_key=settings.google_api_key)`

**API Usage:**
```python
# File upload
file_ref = genai.upload_file(path=file_path, display_name=name, mime_type=mime_type)

# Wait for processing
file_ref = genai.get_file(file_id)  # Check state='ACTIVE'

# Generate content
response = model.generate_content(contents, generation_config={...}, request_options={'timeout': 600})
```

**Model:** `gemini-2.5-pro` (mapped from `gemini-1.5-pro-latest`)

**Features:**
- Multimodal input (audio, images, text)
- JSON response parsing with error recovery
- Automatic file cleanup after analysis

---

### 6.2 Meta WhatsApp Cloud API

**Purpose:** Send/receive WhatsApp messages via Meta's official API

**Authentication:**
- Environment variables:
  - `WHATSAPP_CLOUD_API_TOKEN` - Access token (can be short-lived or long-lived)
  - `WHATSAPP_PHONE_NUMBER_ID` - Phone number ID
  - `WHATSAPP_VERIFY_TOKEN` - Webhook verification token
  - `WHATSAPP_APP_ID` - App ID (for token refresh, optional)
  - `WHATSAPP_APP_SECRET` - App Secret (for token refresh, optional)

**API Endpoints Used:**
- `POST https://graph.facebook.com/v18.0/{phone_number_id}/messages` - Send message
- `GET https://graph.facebook.com/v18.0/debug_token` - Check token info

**Features:**
- Automatic token refresh (if App ID + Secret configured)
- Token expiration detection
- Webhook verification and message handling
- Message status tracking (delivered, read, failed)

**Webhook Endpoints:**
- `GET /webhook` - Verification
- `POST /webhook` - Incoming messages and status updates
- `GET /whatsapp` - Alternative verification
- `POST /whatsapp` - Unified webhook (Meta + Twilio)

---

### 6.3 Twilio

**Purpose:** WhatsApp & SMS messaging (fallback/alternative provider)

**Authentication:**
- Environment variables:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM` - WhatsApp sender number
  - `TWILIO_WHATSAPP_TO` - WhatsApp recipient number
  - `TWILIO_SMS_FROM` - SMS sender number
  - `TWILIO_SMS_TO` - SMS recipient number

**Features:**
- WhatsApp messaging via Twilio API
- SMS messaging
- TwiML response generation
- Message formatting for summaries

---

### 6.4 Google Drive API

**Purpose:** Background processing of meeting recordings (cron job)

**Authentication:**
- Service Account JSON credentials (environment variables):
  - `GOOGLE_CLIENT_EMAIL`
  - `GOOGLE_PRIVATE_KEY`
  - `GOOGLE_PROJECT_ID`
  - `DRIVE_INBOX_ID` - Inbox folder ID
  - `DRIVE_ARCHIVE_ID` - Archive folder ID

**Usage:**
- Background script: `process_meetings.py`
- Checks Google Drive folder for new audio files
- Downloads, processes with Gemini, sends summary
- Moves processed files to Archive

**Note:** This is a separate cron job, not part of the main FastAPI application.

---

## 7. Key Code Snippets

### 7.1 WhatsApp Webhook Handler (Meta)

```python
@app.post("/webhook")
async def webhook(request: Request):
    if request.method == "POST":
        payload = await request.json()
        
        # Process incoming messages
        if "entry" in payload:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Handle messages
                    if "messages" in value:
                        for message in value.get("messages", []):
                            from_number = message.get("from")
                            message_body = message.get("text", {}).get("body", "")
                            
                            # Send auto-reply
                            if whatsapp_provider:
                                reply_result = whatsapp_provider.send_whatsapp(
                                    message="Message received and saved to memory.",
                                    to=f"+{from_number}"
                                )
        
        return JSONResponse(content={"status": "ok"})
```

### 7.2 Gemini Analysis Flow

```python
def analyze_day(self, audio_paths, image_paths, text_inputs):
    # Upload files to Gemini
    uploaded_files = []
    for audio_path in audio_paths:
        file_ref = self.upload_and_wait(audio_path)
        uploaded_files.append(file_ref)
    
    # Build contents list
    contents = [SYSTEM_PROMPT]
    contents.extend(text_inputs)
    contents.extend(uploaded_files)  # File objects
    
    # Generate analysis
    response = self.model.generate_content(
        contents,
        generation_config={'max_output_tokens': 8192},
        request_options={'timeout': 600}
    )
    
    # Parse JSON response
    result = json.loads(response.text)
    return result
```

### 7.3 WhatsApp Provider Factory

```python
class WhatsAppProviderFactory:
    _providers: Dict[str, type] = {}
    
    @classmethod
    def create_provider(cls, provider_name=None, fallback=True):
        if provider_name is None:
            provider_name = settings.whatsapp_provider.lower()
        
        provider_class = cls._providers[provider_name]
        instance = provider_class()
        
        if instance.is_configured():
            return instance
        elif fallback and 'twilio' in cls._providers:
            return cls.create_provider('twilio', fallback=False)
        
        return None
```

### 7.4 Meta WhatsApp Message Sending

```python
def send_whatsapp(self, message: str, to: Optional[str] = None):
    url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {self.access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": message}
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    return {"success": True, "message_id": response.json().get('messages', [{}])[0].get('id')}
```

---

## 8. Current Capabilities

### ✅ Implemented

1. **Multimodal Analysis:**
   - Audio file processing (MP3, WAV, M4A, OGG)
   - Image processing (JPG, PNG)
   - Text note analysis
   - Combined analysis of all inputs

2. **Three Expert Personas:**
   - Simon Sinek (Leadership)
   - High-Tech Strategy Consultant
   - Adler Institute (Parenting)

3. **WhatsApp Integration:**
   - Dual provider support (Twilio + Meta)
   - Webhook handling (incoming messages)
   - Auto-reply functionality
   - Message status tracking

4. **Output Formats:**
   - JSON analysis result
   - WhatsApp/SMS summary
   - PDF report generation

5. **Error Handling:**
   - JSON parsing error recovery
   - Connection retry logic
   - Token refresh automation

### ❌ Limitations

1. **No Persistent Memory:**
   - No conversation history
   - No user profiles
   - No historical context

2. **No Data Storage:**
   - Analysis results not saved
   - No database integration
   - Files deleted after processing

3. **No Advanced Features:**
   - No semantic search
   - No vector embeddings
   - No multi-turn conversations
   - No user authentication

4. **Limited Webhook Processing:**
   - Messages logged but not stored
   - No conversation context building
   - Simple auto-reply only

---

## 9. Environment Variables Summary

### Required
- `GOOGLE_API_KEY` - Google Gemini API key

### WhatsApp Provider Selection
- `WHATSAPP_PROVIDER` - "twilio" or "meta" (default: "twilio")

### Twilio (if using)
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `TWILIO_WHATSAPP_TO`
- `TWILIO_SMS_FROM` (optional)
- `TWILIO_SMS_TO` (optional)
- `ENABLE_SMS` - "true" or "false" (default: false)

### Meta WhatsApp (if using)
- `WHATSAPP_CLOUD_API_TOKEN` - Access token
- `WHATSAPP_PHONE_NUMBER_ID` - Phone number ID
- `WHATSAPP_VERIFY_TOKEN` - Webhook verification token
- `WHATSAPP_TO` - Recipient number (E.164 format)
- `WHATSAPP_APP_ID` - App ID (optional, for token refresh)
- `WHATSAPP_APP_SECRET` - App Secret (optional, for token refresh)
- `WEBHOOK_VERIFY_TOKEN` - Alternative webhook token

### Server
- `PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: false)

---

## 10. Deployment

**Platform:** Render.com  
**Service Type:** Web Service  
**Build Command:** `pip install -r requirements.txt`  
**Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
**Auto-Deploy:** Enabled (GitHub push to main branch)

**URL:** `https://second-brain-6q8c.onrender.com`

---

## 11. Recommendations for Enhancement

1. **Add Persistent Storage:**
   - Database for analysis results
   - Conversation history storage
   - User profile management

2. **Implement Memory System:**
   - Vector embeddings for semantic search
   - Context accumulation across sessions
   - Historical reference in prompts

3. **Enhance Webhook Processing:**
   - Store incoming messages
   - Build conversation context
   - Implement intelligent responses (not just auto-reply)

4. **Add Authentication:**
   - User authentication system
   - API key management
   - Rate limiting

5. **Improve Error Handling:**
   - Retry queues for failed messages
   - Dead letter queue
   - Comprehensive error logging

---

**End of Report**
