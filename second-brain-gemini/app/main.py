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
from app.services.conversation_engine import conversation_engine

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
# Key: message_id (wam_id), Value: dict with file_path and speaker_id
# Example: {"wamid.xxx": {"file_path": "/tmp/audio.mp3", "speaker_id": "Speaker 2"}}
pending_identifications = {}

# Voice Map: Persistent mapping of Speaker ID -> Real Name
# This is stored in Drive Memory as part of user_profile
# Local cache for quick access during processing
_voice_map_cache = {}  # {"Speaker 2": "Miri", "Speaker 3": "Shai"}

# WORKING MEMORY: Store the full JSON output of the most recent audio processing
# This enables "Zero Latency" RAG - bypasses Drive sync delay
_last_processed_session = {
    'summary': '',
    'speakers': [],
    'timestamp': '',
    'transcript_file_id': '',
    'segments': [],
    'full_transcript': {},  # Complete Gemini output
    'identified_speakers': {},  # Real-time voice_map snapshot at time of processing
    'raw_gemini_output': ''  # Original Gemini response for debugging
}
_session_context_lock = Lock()

def update_last_session_context(summary: str, speakers: list, timestamp: str, 
                                  transcript_file_id: str = '', segments: list = None,
                                  full_transcript: dict = None, identified_speakers: dict = None,
                                  expert_analysis: dict = None):
    """
    Update Working Memory with the last processed session.
    This provides Zero Latency access to the conversation that just ended.
    Includes expert analysis for immediate RAG queries.
    """
    global _last_processed_session
    with _session_context_lock:
        _last_processed_session = {
            'summary': summary,
            'speakers': speakers,
            'timestamp': timestamp,
            'transcript_file_id': transcript_file_id,
            'segments': segments or [],
            'full_transcript': full_transcript or {},
            'identified_speakers': identified_speakers or _voice_map_cache.copy(),
            'expert_analysis': expert_analysis or {}
        }
        print(f"📝 WORKING MEMORY updated:")
        print(f"   Speakers: {speakers}")
        print(f"   Summary: {len(summary)} chars")
        print(f"   Segments: {len(segments or [])} entries")
        print(f"   Identified speakers: {identified_speakers or _voice_map_cache}")
        if expert_analysis:
            print(f"   Expert analysis: {expert_analysis.get('persona', 'N/A')}")

def get_last_session_context() -> dict:
    """
    Get the Working Memory for RAG.
    Returns the full session data including real-time speaker identifications.
    """
    with _session_context_lock:
        # Also include the latest voice_map for real-time name resolution
        result = _last_processed_session.copy()
        result['current_voice_map'] = _voice_map_cache.copy()
        return result

_processed_ids_lock = Lock()  # Thread-safe access to processed_message_ids


def update_voice_map(speaker_id: str, real_name: str) -> bool:
    """
    Update the voice map with a new Speaker ID -> Real Name mapping.
    This is stored in Drive Memory for persistence.
    
    Args:
        speaker_id: The generic speaker ID (e.g., "Speaker 2", "Unknown Speaker 3")
        real_name: The actual person's name
    
    Returns:
        True if successful, False otherwise
    """
    global _voice_map_cache
    
    # Update local cache
    _voice_map_cache[speaker_id.lower()] = real_name
    print(f"📝 Updated voice map cache: {speaker_id} -> {real_name}")
    
    # Update in Drive Memory (within user_profile)
    try:
        if drive_memory_service.is_configured:
            memory = drive_memory_service.get_memory()
            user_profile = memory.get('user_profile', {})
            
            # Initialize voice_map in user_profile if not exists
            if 'voice_map' not in user_profile:
                user_profile['voice_map'] = {}
            
            user_profile['voice_map'][speaker_id.lower()] = real_name
            memory['user_profile'] = user_profile
            
            # Save back to Drive (we pass None for background_tasks since we want immediate save)
            drive_memory_service.update_memory(memory)
            print(f"✅ Voice map saved to Drive: {user_profile.get('voice_map', {})}")
            return True
    except Exception as e:
        print(f"⚠️  Failed to save voice map to Drive: {e}")
        import traceback
        traceback.print_exc()
    
    return False


def get_voice_map() -> dict:
    """
    Get the voice map from Drive Memory or local cache.
    
    Returns:
        Dict mapping speaker IDs to real names
    """
    global _voice_map_cache
    
    # If cache is empty, try to load from Drive
    if not _voice_map_cache and drive_memory_service.is_configured:
        try:
            memory = drive_memory_service.get_memory()
            user_profile = memory.get('user_profile', {})
            _voice_map_cache = user_profile.get('voice_map', {})
            print(f"📂 Loaded voice map from Drive: {_voice_map_cache}")
        except Exception as e:
            print(f"⚠️  Failed to load voice map from Drive: {e}")
    
    return _voice_map_cache

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


def is_kb_query(message: str) -> bool:
    """
    Check if a message is a Knowledge Base / organizational query.
    
    These queries skip the standard audio-summary flow and get
    a direct, fact-based answer from the Knowledge Base files.
    
    Examples (Hebrew):
    - "מי מדווח ליובל?"
    - "מה התפקיד של דנה?"
    - "מי בצוות של עמית?"
    - "מה המבנה הארגוני?"
    - "מי המנהל של שי?"
    - "ספר לי על התפקיד של..."
    """
    message_stripped = message.strip()
    
    # Hebrew prefix triggers (startswith)
    hebrew_prefix_triggers = [
        'מי מדווח ל',
        'מה התפקיד של',
        'מי בצוות של',
        'מי עובד תחת',
        'מי כפוף ל',
        'למי מדווח',
        'מי המנהל של',
        'מי האחראי על',
        'ספר לי על התפקיד',
        'מה המבנה הארגוני',
        'מה ההיררכיה',
        'תראה לי את המבנה',
        'מי אחראי על',
        'מה השכר של',
        'מה המשכורת של',
        'כמה מרוויח',
        'כמה מרוויחה',
        'מה הדירוג של',
        'מה הציון של',
        'מה ה-rating של',
        'תן לי את הדירוג',
        'תן לי את השכר',
        'תן לי את המשכורת',
        'תן לי את התפקיד',
        'תן לי מידע על',
        'ספר לי על ',
        'הראה לי את ',
    ]
    
    # Check prefix triggers
    for trigger in hebrew_prefix_triggers:
        if message_stripped.startswith(trigger):
            return True
    
    # Hebrew keyword combinations (must contain at least one keyword from each group)
    org_keywords = ['מדווח', 'כפוף', 'היררכיה', 'ארגוני', 'מבנה ארגוני', 'דרג', 'תפקיד',
                    'שכר', 'משכורת', 'בונוס', 'דירוג', 'rating', 'individual factor',
                    'פקטור', 'compensation', 'salary']
    question_words = ['מי', 'מה', 'איפה', 'כמה', 'האם', 'תן', 'הראה', 'ספר', 'איזה']
    
    has_org = any(kw in message_stripped for kw in org_keywords)
    has_question = any(kw in message_stripped for kw in question_words)
    
    if has_org and has_question:
        return True
    
    # English triggers
    english_triggers = [
        'who reports to',
        'what is the role of',
        'who is on the team',
        'who works under',
        'who manages',
        'org chart',
        'org structure',
        'reporting line',
        'what team is',
        'what is the salary',
        'how much does',
        'what is the rating',
        'individual factor',
        'compensation of',
        'who earns',
    ]
    
    message_lower = message_stripped.lower()
    for trigger in english_triggers:
        if trigger in message_lower:
            return True
    
    return False


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
    Search through chat history AND Transcripts folder in Drive for relevant transcripts.
    Returns formatted context string for Gemini.
    
    Searches:
    1. Chat history (in-memory)
    2. Transcripts folder in Google Drive (persistent storage)
    """
    query_lower = query.lower()
    relevant_transcripts = []
    
    # Extract search terms from query
    hebrew_stopwords = ['מה', 'עם', 'את', 'על', 'של', 'לי', 'אני', 'הוא', 'היא', 'הם', 'דיברתי', 'דיברנו', 'אמר', 'אמרה', 'סכם', 'תסכם']
    english_stopwords = ['what', 'did', 'i', 'we', 'talk', 'about', 'with', 'the', 'a', 'an', 'say', 'said', 'summarize']
    
    import re
    words = re.findall(r'\b\w+\b', query_lower)
    search_terms = [w for w in words if w not in hebrew_stopwords and w not in english_stopwords and len(w) > 1]
    
    print(f"🔍 Searching with terms: {search_terms}")
    
    # STEP 1: Search in Transcripts folder in Google Drive (PRIMARY SOURCE)
    if drive_memory_service.is_configured and search_terms:
        print("📂 Searching Transcripts folder in Google Drive...")
        try:
            drive_results = drive_memory_service.search_transcripts(search_terms, limit=5)
            
            for result in drive_results:
                filename = result.get('filename', '')
                created_time = result.get('created_time', '')
                speakers = result.get('speakers', [])
                segments = result.get('matching_segments', [])
                
                transcript_text = f"\n📅 Recording: {filename} ({created_time}):\n"
                transcript_text += f"👥 Speakers: {', '.join(speakers) if speakers else 'Unknown'}\n"
                
                for seg in segments[:15]:  # Limit segments
                    speaker = seg.get('speaker', 'Unknown')
                    text = seg.get('text', '')
                    transcript_text += f"  {speaker}: {text}\n"
                
                relevant_transcripts.append(transcript_text)
            
            print(f"   Found {len(drive_results)} matching transcript(s) in Drive")
            
        except Exception as e:
            print(f"⚠️  Error searching Drive transcripts: {e}")
    
    # STEP 2: Also search chat_history (backup/recent items)
    if chat_history:
        print("📚 Also searching chat history...")
        for interaction in chat_history:
            if interaction.get('type') != 'audio':
                continue
            
            transcript = interaction.get('transcript', {})
            if not transcript:
                continue
            
            speakers = interaction.get('speakers', [])
            segments = transcript.get('segments', []) if isinstance(transcript, dict) else []
            timestamp = interaction.get('timestamp', '')
            
            # Check for matches
            speaker_match = any(
                any(term in speaker.lower() for term in search_terms)
                for speaker in speakers
            )
            
            matching_segments = [
                seg for seg in segments
                if any(term in seg.get('text', '').lower() for term in search_terms)
            ]
            
            if speaker_match or matching_segments:
                transcript_text = f"\n📅 Recording from {timestamp}:\n"
                transcript_text += f"👥 Speakers: {', '.join(speakers) if speakers else 'Unknown'}\n"
                
                segments_to_show = segments[:15] if speaker_match else matching_segments[:10]
                for seg in segments_to_show:
                    speaker = seg.get('speaker', 'Unknown')
                    text = seg.get('text', '')
                    transcript_text += f"  {speaker}: {text}\n"
                
                # Avoid duplicates
                if transcript_text not in relevant_transcripts:
                    relevant_transcripts.append(transcript_text)
    
    if relevant_transcripts:
        context = f"נמצאו {len(relevant_transcripts)} הקלטות רלוונטיות:\n"
        context += "\n---\n".join(relevant_transcripts[:5])
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
    """Pre-warm memory cache, start scheduler, and send deployment notification."""
    
    # ================================================================
    # DEPLOYMENT NOTIFICATION: Send WhatsApp when server starts
    # This is triggered when Render finishes deploying and restarts the service
    # ================================================================
    try:
        # Read current version
        version_file = Path(__file__).parent.parent / "VERSION"
        current_version = version_file.read_text().strip() if version_file.exists() else "unknown"
        
        # Check if we should send notification (only in production)
        is_production = os.environ.get('RENDER', '') == 'true'
        
        if is_production:
            print(f"🚀 Production deployment detected - Version {current_version}")
            
            # Get Israel time (UTC+2 in winter, UTC+3 in summer - using +2 as base)
            from datetime import timezone, timedelta
            israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
            israel_time_str = israel_time.strftime('%d/%m/%Y %H:%M')
            
            # Get changes summary for deployment notification
            # Priority: 1) git log, 2) Google Drive memory, 3) .last_commit file
            changes_summary = ""
            
            # Method 1: Try git log to get latest commit message
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'log', '-1', '--pretty=%B'],
                    capture_output=True, text=True, timeout=5,
                    cwd=Path(__file__).parent.parent
                )
                if result.returncode == 0 and result.stdout.strip():
                    git_msg = result.stdout.strip()
                    # Extract meaningful part (skip version tags like "v3.9.1 - ")
                    if ' - ' in git_msg:
                        git_msg = git_msg.split(' - ', 1)[1]
                    changes_summary = git_msg[:150]
                    print(f"📝 Using git commit message: {changes_summary[:50]}...")
            except Exception as git_error:
                print(f"⚠️  Could not get git log: {git_error}")
            
            # Method 2: Fall back to Google Drive memory (saved by notify-cursor-started)
            if not changes_summary:
                try:
                    if drive_memory_service.is_configured:
                        memory = drive_memory_service.get_memory()
                        last_task = memory.get('last_cursor_task', {})
                        if last_task and last_task.get('prompt'):
                            prompt = last_task['prompt']
                            changes_summary = prompt[:150]
                            if len(prompt) > 150:
                                changes_summary += "..."
                            print(f"📝 Using Drive memory: {changes_summary[:50]}...")
                            
                            # Clear after reading to avoid stale data
                            memory.pop('last_cursor_task', None)
                            drive_memory_service.save_memory(memory)
                except Exception as drive_error:
                    print(f"⚠️  Could not read from Drive: {drive_error}")
            
            # Method 3: Fall back to .last_commit file (created during build)
            if not changes_summary:
                commit_file = Path(__file__).parent.parent / ".last_commit"
                if commit_file.exists():
                    try:
                        commit_msg = commit_file.read_text().strip()
                        if commit_msg and commit_msg not in ['No commit message available', '']:
                            changes_summary = commit_msg[:150]
                            print(f"📝 Using .last_commit: {changes_summary[:50]}...")
                    except Exception:
                        pass
            
            # Final fallback
            if not changes_summary:
                changes_summary = "עדכון מערכת"
            
            # Send deployment notification via WhatsApp (Message 3)
            from app.services.meta_whatsapp_service import meta_whatsapp_service
            
            notification_msg = f"""🚀 *גרסה חדשה עלתה לפרודקשן!*

📦 גרסה: *{current_version}*
⏰ זמן: {israel_time_str} (שעון ישראל)

📝 *שינויים עיקריים:*
{changes_summary}

✅ השרת פעיל ומוכן לעבודה!"""
            
            if meta_whatsapp_service.is_configured:
                result = meta_whatsapp_service.send_whatsapp(notification_msg)
                if result.get('success'):
                    print(f"✅ Deployment notification sent via WhatsApp")
                else:
                    print(f"⚠️  Failed to send deployment notification: {result.get('error')}")
            elif twilio_service.is_configured:
                result = twilio_service.send_whatsapp(notification_msg)
                if result.get('success'):
                    print(f"✅ Deployment notification sent via Twilio")
                else:
                    print(f"⚠️  Failed to send deployment notification: {result.get('error')}")
            else:
                print("⚠️  No WhatsApp provider configured for deployment notification")
        else:
            print(f"📍 Local development - Version {current_version} (no notification)")
            
    except Exception as e:
        print(f"⚠️  Deployment notification error: {e}")
        import traceback
        traceback.print_exc()
    
    # Pre-warm memory cache
    if drive_memory_service.is_configured:
        print("🔥 Pre-warming memory cache...")
        drive_memory_service.preload_memory()
    else:
        print("⚠️  Skipping memory cache pre-warm (Drive Memory Service not configured)")
    
    # ================================================================
    # IDENTITY CONTEXT VERIFICATION: Pre-load KB and print summary
    # ================================================================
    try:
        from app.services.knowledge_base_service import load_context, get_identity_context_summary
        
        print("\n📚 ══════════════════════════════════════════════")
        print("📚  IDENTITY CONTEXT INITIALIZATION")
        print("📚 ══════════════════════════════════════════════")
        
        kb_context = load_context()
        summary = get_identity_context_summary()
        
        if kb_context:
            print(f"✅ {summary}")
        else:
            print("⚠️  Identity Context: No data loaded (KB empty or not configured)")
        
        print("📚 ══════════════════════════════════════════════\n")
    except Exception as kb_init_error:
        print(f"⚠️  Identity Context initialization error: {kb_init_error}")
        import traceback
        traceback.print_exc()
    
    # ================================================================
    # CONVERSATION ENGINE: Initialize LLM-First engine with tools
    # Phase 1: Load user profile from memory → inject into CE
    # Phase 2B: Pass drive_memory_service reference for search_meetings
    # ================================================================
    try:
        user_profile = {}
        try:
            memory = drive_memory_service.get_memory()
            user_profile = memory.get("user_profile", {})
            if user_profile:
                print(f"👤 [Profile] Loaded user profile: {list(user_profile.keys())}")
            else:
                print("ℹ️  [Profile] No user profile found in memory")
        except Exception as profile_err:
            print(f"⚠️  [Profile] Could not load user profile: {profile_err}")

        conversation_engine.initialize(
            user_profile=user_profile,
            drive_memory_service=drive_memory_service
        )
        print("✅ [ConvEngine] Conversation Engine ready — LLM-First architecture active")
        if user_profile:
            print(f"   📋 Profile injected: {', '.join(k for k in user_profile.keys() if k != 'chat_history')}")
        print(f"   🔧 Tools: search_person, get_reports, save_fact, list_org_stats, search_meetings")
    except Exception as ce_error:
        print(f"⚠️  Conversation Engine initialization error: {ce_error}")
        import traceback
        traceback.print_exc()
    
    # Start the APScheduler for weekly architecture audit
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from app.services.architecture_audit_service import architecture_audit_service
        from app.services.meta_whatsapp_service import meta_whatsapp_service
        
        def run_scheduled_audit():
            """Run the weekly architecture audit and send report via WhatsApp."""
            print("⏰ SCHEDULED AUDIT TRIGGERED (Friday 08:00 AM)")
            try:
                result = architecture_audit_service.run_weekly_architecture_audit(
                    drive_service=drive_memory_service
                )
                
                if result.get('success'):
                    report = result.get('report', 'לא נוצר דו"ח')
                    
                    # Send via WhatsApp
                    if meta_whatsapp_service.is_configured:
                        meta_whatsapp_service.send_whatsapp(report)
                        print("✅ Scheduled audit report sent via WhatsApp")
                    elif twilio_service.is_configured:
                        twilio_service.send_whatsapp(report)
                        print("✅ Scheduled audit report sent via Twilio")
                    else:
                        print("⚠️  No WhatsApp provider configured for scheduled report")
                else:
                    print(f"❌ Scheduled audit failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Scheduled audit error: {e}")
                import traceback
                traceback.print_exc()
        
        scheduler = AsyncIOScheduler()
        
        # Schedule for every Friday at 13:00 (1 PM) Israel time (UTC+2/+3)
        # Using UTC: Friday 11:00 (summer) or 10:00 (winter) - using 11:00 as middle ground
        scheduler.add_job(
            run_scheduled_audit,
            CronTrigger(day_of_week='fri', hour=11, minute=0),  # 11:00 UTC = 13:00 Israel
            id='weekly_architecture_audit',
            name='Weekly Architecture Audit (Friday 13:00)',
            replace_existing=True
        )
        
        scheduler.start()
        print("📅 Scheduler started: Weekly Architecture Audit (Friday 13:00 / 1 PM)")
        
    except Exception as e:
        print(f"⚠️  Failed to start scheduler: {e}")
        import traceback
        traceback.print_exc()

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


@app.post("/notify-cursor-started")
async def notify_cursor_started(request: Request):
    """
    Receive notification from the local Cursor bridge that it has started working.
    Sends Message 2: "ברגעים אלה Cursor החל את עבודת הפיתוח..."
    Also stores the prompt in Google Drive for use in deployment notification (Message 3).
    
    Called by local_cursor_bridge.py after activating Cursor and injecting the prompt.
    """
    try:
        data = await request.json()
        task_preview = data.get('task_preview', '')
        success = data.get('success', True)
        save_to_drive = data.get('save_to_drive', False)
        
        print(f"📥 Cursor STARTED notification received:")
        print(f"   Task: {task_preview[:80]}...")
        print(f"   Save to Drive: {save_to_drive}")
        
        if not success:
            # Bridge failed to inject the prompt
            message = f"❌ הזרקת הפקודה ל-Cursor נכשלה.\n\n📝 משימה: {task_preview}"
        else:
            # Store the prompt for Message 3 (deployment notification)
            # Save to Google Drive for persistence across deployments
            try:
                if drive_memory_service.is_configured:
                    # Save as a special "last_cursor_task" in memory
                    memory = drive_memory_service.get_memory()
                    memory['last_cursor_task'] = {
                        'prompt': task_preview[:500],
                        'timestamp': datetime.now().isoformat()
                    }
                    drive_memory_service.save_memory(memory)
                    print(f"💾 Saved last prompt to Google Drive for deployment notification")
                else:
                    print(f"⚠️  Drive not configured - cannot persist prompt")
            except Exception as save_error:
                print(f"⚠️  Could not save last prompt to Drive: {save_error}")
            
            # Message 2: Cursor started working (RTL-friendly text)
            message = "🛠️ הוא על זה"
        
        # Send via Meta WhatsApp (primary) or Twilio (fallback)
        from app.services.meta_whatsapp_service import meta_whatsapp_service
        
        if meta_whatsapp_service.is_configured:
            result = meta_whatsapp_service.send_whatsapp(message)
        elif twilio_service.is_configured:
            result = twilio_service.send_whatsapp(message)
        else:
            result = {"success": False, "error": "No WhatsApp provider configured"}
        
        if result.get('success'):
            print(f"✅ WhatsApp notification sent (Message 2)")
            return {"status": "ok", "message": "Notification sent"}
        else:
            print(f"⚠️  Failed to send WhatsApp notification: {result.get('error')}")
            return {"status": "warning", "message": "Task started but notification failed"}
            
    except Exception as e:
        print(f"❌ Error in notify-cursor-started: {e}")
        import traceback
        traceback.print_exc()
        # Return success anyway - don't fail the bridge
        return {"status": "error", "message": str(e)}


# Keep old endpoint for backwards compatibility
@app.post("/notify-cursor-complete")
async def notify_cursor_complete(request: Request):
    """Backwards compatibility - redirects to notify-cursor-started."""
    return await notify_cursor_started(request)


@app.post("/notify-deployment")
async def notify_deployment(request: Request):
    """
    Receive notification from Render/GitHub Actions that a deployment was successful.
    Sends a WhatsApp message with the new version and changes.
    
    Expected JSON body:
    {
        "version": "3.1.0",
        "changes": "Description of main changes",
        "status": "success" | "failed"
    }
    """
    try:
        data = await request.json()
        version = data.get('version', 'unknown')
        changes = data.get('changes', 'לא צוינו שינויים')
        status = data.get('status', 'success')
        
        print(f"📥 Deployment notification received:")
        print(f"   Version: {version}")
        print(f"   Status: {status}")
        print(f"   Changes: {changes[:100]}...")
        
        # Construct the WhatsApp message
        if status == 'success':
            message = f"🚀 גרסה חדשה שוחררה!\n\n📦 גרסה: {version}\n\n📝 שינויים עיקריים:\n{changes}"
        else:
            message = f"❌ שחרור גרסה נכשל\n\n📦 גרסה: {version}\n\n⚠️ סיבה: {changes}"
        
        # Send via Meta WhatsApp (primary) or Twilio (fallback)
        from app.services.meta_whatsapp_service import meta_whatsapp_service
        
        if meta_whatsapp_service.is_configured:
            result = meta_whatsapp_service.send_whatsapp(message)
        elif twilio_service.is_configured:
            result = twilio_service.send_whatsapp(message)
        else:
            result = {"success": False, "error": "No WhatsApp provider configured"}
        
        if result.get('success'):
            print(f"✅ Deployment notification sent via WhatsApp")
            return {"status": "ok", "message": "Notification sent"}
        else:
            print(f"⚠️  Failed to send deployment notification: {result.get('error')}")
            return {"status": "warning", "message": "Deployment succeeded but notification failed"}
            
    except Exception as e:
        print(f"❌ Error in notify-deployment: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


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


# ============================================================================
# BACKGROUND AUDIO PROCESSING FUNCTION
# This runs in the background to avoid 502 timeouts on WhatsApp webhooks
# ============================================================================

def process_audio_in_background(
    message_id: str,
    from_number: str,
    media_id: str,
    access_token: str,
    phone_number_id: str
):
    """
    Process audio message in background to avoid webhook timeout.
    This function handles all audio downloading, archiving, and Gemini processing.
    """
    import requests
    import tempfile
    import traceback
    
    print(f"\n{'='*60}")
    print(f"🎤 BACKGROUND AUDIO PROCESSING STARTED")
    print(f"   Message ID: {message_id}")
    print(f"   From: {from_number}")
    print(f"   Max voice signatures: {settings.max_voice_signatures}")
    print(f"   Multimodal enabled: {settings.enable_multimodal_voice}")
    print(f"{'='*60}\n")
    
    # Initialize cleanup list - CRITICAL for memory management on Render
    temp_files_to_cleanup = []
    reference_voices = []
    slice_files_to_cleanup = []  # Track audio slices separately
    
    # Send immediate "Processing..." message to manage user expectations
    try:
        if whatsapp_provider:
            processing_msg = "🎙️ קיבלתי, אני על זה."
            whatsapp_provider.send_whatsapp(
                message=processing_msg,
                to=f"+{from_number}"
            )
            print("📤 Sent 'Processing...' notification")
    except Exception as notify_error:
        print(f"⚠️  Failed to send processing notification: {notify_error}")
    
    try:
        # Step 1: Get media URL from WhatsApp API
        print("🔐 Downloading media from WhatsApp...")
        media_url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        media_response = requests.get(media_url, headers=headers, timeout=30)
        if media_response.status_code != 200:
            print(f"❌ Failed to get media URL. Status: {media_response.status_code}")
            _send_error_to_user(from_number, "שגיאה בהורדת האודיו מווטסאפ")
            return
        
        media_info = media_response.json()
        download_url = media_info.get("url")
        if not download_url:
            print("❌ No download URL in media response")
            _send_error_to_user(from_number, "שגיאה בהורדת האודיו מווטסאפ")
            return
        
        # Step 2: Download actual audio file
        print(f"📥 Downloading audio file...")
        audio_response = requests.get(download_url, headers=headers, timeout=60)
        if audio_response.status_code != 200:
            print(f"❌ Failed to download audio. Status: {audio_response.status_code}")
            _send_error_to_user(from_number, "שגיאה בהורדת האודיו")
            return
        
        audio_bytes = audio_response.content
        print(f"✅ Media downloaded: {len(audio_bytes)} bytes")
        
        # Step 3: Upload to Drive archive
        print("📤 Uploading to Google Drive...")
        file_stream = io.BytesIO(audio_bytes)
        audio_metadata = drive_memory_service.upload_audio_to_archive(
            audio_file_obj=file_stream,
            filename=f"whatsapp_audio_{message_id}.ogg",
            mime_type="audio/ogg"
        )
        
        if not audio_metadata:
            print("❌ Failed to upload to Drive")
            _send_error_to_user(from_number, "שגיאה בשמירת האודיו לדרייב")
            return
        
        print(f"✅ Audio archived. File ID: {audio_metadata.get('file_id')}")
        
        # Step 4: Save to temp file for Gemini processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
            temp_files_to_cleanup.append(tmp_path)
        
        # ============================================================
        # 🎯 SMART VOICE ROUTER
        # Short voice notes (≤30s) = voice COMMANDS → Conversation Engine
        #   (save_fact, KB queries, search_person, etc.)
        # Long recordings (>30s) = meetings → Full Analysis Pipeline
        #   (diarization, expert analysis, speaker ID, VAD, etc.)
        # ============================================================
        VOICE_COMMAND_THRESHOLD_SEC = 30
        
        try:
            from pydub import AudioSegment as RouteCheckSegment
            voice_check = RouteCheckSegment.from_file(tmp_path)
            duration_sec = len(voice_check) / 1000.0
            print(f"⏱️  [Voice Router] Audio duration: {duration_sec:.1f}s (threshold: {VOICE_COMMAND_THRESHOLD_SEC}s)")
            
            if duration_sec <= VOICE_COMMAND_THRESHOLD_SEC:
                print(f"💬 [Voice Router] SHORT voice note ({duration_sec:.1f}s) → Conversation Engine")
                print(f"   Skipping: diarization, expert analysis, speaker ID, VAD")
                
                # ── Quick transcription with Gemini Flash ──
                try:
                    from app.services.model_discovery import MODEL_MAPPING, configure_genai as md_configure
                    import google.generativeai as genai_voice
                    import time as route_time
                    
                    md_configure(settings.google_api_key)
                    flash_model = genai_voice.GenerativeModel(MODEL_MAPPING["flash"])
                    
                    # Upload audio for transcription
                    print(f"   📤 Uploading for quick transcription (Flash)...")
                    file_ref = genai_voice.upload_file(
                        path=tmp_path,
                        display_name=f"voice_cmd_{message_id}.ogg",
                        mime_type="audio/ogg"
                    )
                    
                    # Wait for file to be ready
                    max_upload_wait = 30
                    wait_start = route_time.time()
                    while route_time.time() - wait_start < max_upload_wait:
                        file_ref = genai_voice.get_file(file_ref.name)
                        state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                        if state == "ACTIVE":
                            break
                        elif state == "FAILED":
                            raise Exception(f"Gemini file processing failed: {file_ref.name}")
                        route_time.sleep(1)
                    
                    # Simple STT prompt — no diarization, no analysis, just the text
                    transcription_response = flash_model.generate_content([
                        file_ref,
                        "תמלל את ההקלטה הקולית הזאת. "
                        "החזר אך ורק את הטקסט שנאמר, בשפה המקורית. "
                        "אל תוסיף כותרות, תיאורים, שמות דוברים או הערות. רק הטקסט עצמו."
                    ])
                    
                    transcribed_text = ""
                    if transcription_response and transcription_response.text:
                        transcribed_text = transcription_response.text.strip()
                    
                    print(f"   📝 Transcription: \"{transcribed_text[:200]}{'...' if len(transcribed_text) > 200 else ''}\"")
                    
                    # Cleanup uploaded Gemini file
                    try:
                        genai_voice.delete_file(file_ref.name)
                    except Exception:
                        pass
                    
                    if not transcribed_text:
                        print(f"   ⚠️  Empty transcription — falling through to full pipeline")
                        # Fall through to full pipeline below
                    else:
                        # ── Route to Conversation Engine (same as text messages) ──
                        print(f"   🧠 Routing to Conversation Engine...")
                        
                        ai_response = conversation_engine.process_message(
                            phone=from_number,
                            message=transcribed_text
                        )
                        
                        print(f"   🤖 Response: {ai_response[:200]}{'...' if len(ai_response) > 200 else ''}")
                        
                        # Send response via WhatsApp
                        if whatsapp_provider and ai_response:
                            reply_result = whatsapp_provider.send_whatsapp(
                                message=ai_response,
                                to=f"+{from_number}"
                            )
                            if reply_result.get('success'):
                                print(f"   ✅ [Voice Router] Response sent successfully")
                            else:
                                print(f"   ⚠️  [Voice Router] Send failed: {reply_result.get('error')}")
                        
                        print(f"\n{'='*60}")
                        print(f"✅ [Voice Router] Short voice note processed via Conversation Engine — DONE")
                        print(f"{'='*60}\n")
                        return  # SKIP full meeting pipeline
                    
                except Exception as transcription_err:
                    print(f"   ❌ [Voice Router] Quick transcription failed: {transcription_err}")
                    traceback.print_exc()
                    print(f"   ↩️  Falling through to full audio pipeline as fallback...")
                    # Fall through to full pipeline
            else:
                print(f"📊 [Voice Router] LONG recording ({duration_sec:.1f}s > {VOICE_COMMAND_THRESHOLD_SEC}s) → Full Analysis Pipeline")
        
        except ImportError:
            print(f"⚠️  [Voice Router] pydub not available — using full pipeline for all audio")
        except Exception as router_err:
            print(f"⚠️  [Voice Router] Duration check failed: {router_err} — using full pipeline")
        
        # ============================================================
        # FULL MEETING ANALYSIS PIPELINE (for recordings >30s)
        # ============================================================
        
        # Step 5: Retrieve voice signatures (memory optimized)
        known_speaker_names = []
        if drive_memory_service.is_configured and settings.enable_multimodal_voice:
            try:
                max_sigs = settings.max_voice_signatures
                print(f"🎤 Retrieving voice signatures (max: {max_sigs})...")
                reference_voices = drive_memory_service.get_voice_signatures(max_signatures=max_sigs)
                known_speaker_names = [rv['name'].lower() for rv in reference_voices]
                if reference_voices:
                    print(f"✅ Retrieved {len(reference_voices)} voice signature(s)")
            except Exception as e:
                print(f"⚠️  Error retrieving voice signatures: {e}")
                reference_voices = []
        
        # Step 6: Process with Gemini (COMBINED Diarization + Expert Analysis)
        # This uses a single Gemini call with COMBINED_DIARIZATION_EXPERT_PROMPT
        # Same approach as process_meetings.py which works reliably
        print("🤖 [Combined Analysis] Processing audio with Gemini...")
        print(f"   Stage: COMBINED - Diarization + Expert Analysis in ONE call")
        result = gemini_service.analyze_day(
            audio_paths=[tmp_path],
            audio_file_metadata=[audio_metadata],
            reference_voices=reference_voices
        )
        
        print("✅ [Combined Analysis] Gemini analysis complete")
        
        # Extract transcript, segments, and expert summary from SINGLE Gemini call
        transcript_json = result.get('transcript', {})
        segments = transcript_json.get('segments', [])
        summary_text = result.get('summary', '')
        expert_summary = result.get('expert_summary', '')  # NEW: From combined prompt
        
        # Debug: Log what we got
        print(f"📊 [Combined Analysis] Results:")
        print(f"   Segments: {len(segments)}")
        print(f"   Expert Summary: {len(expert_summary)} chars")
        
        if segments:
            first_seg = segments[0]
            print(f"   First segment: {first_seg.get('speaker', 'N/A')} - {first_seg.get('text', 'N/A')[:50]}...")
            unique_speakers = set(seg.get('speaker', 'Unknown') for seg in segments)
            print(f"   Unique speakers: {unique_speakers}")
        
        if expert_summary:
            print(f"   Expert preview: {expert_summary[:100]}...")
        else:
            print("   ⚠️  NO EXPERT SUMMARY - using basic summary as fallback")
        
        # ============================================================
        # BUILD EXPERT ANALYSIS RESULT
        # The expert_summary comes directly from the combined Gemini call
        # No need for a separate second call!
        # ============================================================
        expert_analysis_result = None
        
        if expert_summary and len(expert_summary.strip()) > 50:
            # Success - we have expert summary from combined prompt
            from datetime import timezone, timedelta
            israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
            
            expert_analysis_result = {
                "success": True,
                "raw_analysis": expert_summary,
                "source": "combined",  # Mark as coming from combined prompt
                "timestamp": israel_time.isoformat(),
                "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
            }
            print(f"✅ [Expert Analysis] SUCCESS from combined prompt: {len(expert_summary)} chars")
        else:
            # Fallback: Use basic summary if expert summary is empty
            print(f"⚠️  [Expert Analysis] No expert summary - using basic fallback")
            expert_analysis_result = {
                "success": False,
                "error": "Expert summary not generated",
                "source": "combined"
            }
        
        # Validate segments
        valid_segments = []
        for seg in segments:
            start = seg.get('start')
            end = seg.get('end')
            if start is not None and end is not None:
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    if end > start and start >= 0:
                        valid_segments.append(seg)
        segments = valid_segments
        
        # Extract speaker names
        speaker_names = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker and not speaker.lower().startswith('speaker '):
                speaker_names.add(speaker)
        speaker_names = list(speaker_names)
        
        # ============================================================
        # Step 7: Save transcript + memory (Phase 2A + Phase 4)
        # ============================================================
        
        # Phase 2A: Save FULL transcript as separate file in Transcripts/
        transcript_file_id = None
        try:
            transcript_save_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "segments": segments,
                "summary": summary_text,
                "speakers": speaker_names,
                "audio_file_id": audio_metadata.get('file_id', ''),
                "duration_segments": len(segments),
            }
            if expert_analysis_result and expert_analysis_result.get('success'):
                transcript_save_data["expert_analysis"] = expert_analysis_result.get("raw_analysis", "")
                transcript_save_data["persona"] = expert_analysis_result.get("persona", "")
            
            transcript_file_id = drive_memory_service.save_transcript(
                transcript_data=transcript_save_data,
                speakers=speaker_names
            )
            if transcript_file_id:
                print(f"📄 [Transcript] Saved to Transcripts/ folder (ID: {transcript_file_id})")
            else:
                print("⚠️  [Transcript] Failed to save to Transcripts/ — continuing anyway")
        except Exception as transcript_err:
            print(f"⚠️  [Transcript] Error saving: {transcript_err}")
        
        # Phase 4: Save SLIM entry to memory.json (summary + reference only)
        print("💾 [Drive Upload] Saving slim audio interaction to memory...")
        audio_interaction = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "audio",
            "file_id": audio_metadata.get('file_id', ''),
            "web_content_link": audio_metadata.get('web_content_link', ''),
            "web_view_link": audio_metadata.get('web_view_link', ''),
            "filename": audio_metadata.get('filename', ''),
            "summary": summary_text,
            "speakers": speaker_names,
            "segment_count": len(segments),
            "transcript_file_id": transcript_file_id,  # Pointer to Transcripts/ file
            "message_id": message_id,
            "from_number": from_number
        }
        
        # Include expert analysis SUMMARY (not full raw_analysis)
        if expert_analysis_result and expert_analysis_result.get('success'):
            audio_interaction["expert_analysis"] = {
                "persona": expert_analysis_result.get("persona"),
                "persona_keys": expert_analysis_result.get("persona_keys"),
                "context": expert_analysis_result.get("context"),
                "speakers": expert_analysis_result.get("speakers"),
                "raw_analysis": expert_analysis_result.get("raw_analysis", "")[:1000],  # Truncated
                "timestamp": expert_analysis_result.get("timestamp")
            }
            print(f"📊 Including expert analysis summary in memory (persona: {expert_analysis_result.get('persona')})")
        
        drive_memory_service.update_memory(audio_interaction)
        print("✅ Saved slim audio interaction to memory")
        
        # UPDATE WORKING MEMORY for Zero Latency RAG
        # This enables text queries to access the conversation that just ended IMMEDIATELY
        # without waiting for Drive sync
        update_last_session_context(
            summary=summary_text,
            speakers=list(speaker_names),
            timestamp=datetime.utcnow().isoformat() + "Z",
            transcript_file_id=audio_metadata.get('file_id', ''),
            segments=segments,
            full_transcript=transcript_json,
            identified_speakers=_voice_map_cache.copy(),
            expert_analysis=expert_analysis_result if expert_analysis_result and expert_analysis_result.get('success') else None
        )
        
        # Phase 3: Inject Working Memory into Conversation Engine
        # So user can immediately ask "what did we talk about?" after a recording
        try:
            expert_snippet = ""
            if expert_analysis_result and expert_analysis_result.get('success'):
                expert_snippet = expert_analysis_result.get("raw_analysis", "")[:500]
            
            conversation_engine.inject_session_context(
                phone=from_number,
                summary=summary_text,
                speakers=speaker_names,
                segments=segments,
                expert_analysis=expert_snippet
            )
            print("💾 [ConvEngine] Working memory injected for next chat interaction")
        except Exception as wm_err:
            print(f"⚠️  [ConvEngine] Working memory injection failed: {wm_err}")
        
        # Step 7.5: PROACTIVE FACT IDENTIFICATION
        # Scan transcript for new facts about known people and ask user for confirmation
        try:
            from app.services.context_writer_service import context_writer
            
            print("🧠 [FactID] Scanning transcript for new facts...")
            new_facts = context_writer.identify_facts(summary_text, segments)
            
            if new_facts:
                confirmation_msg = context_writer.format_fact_confirmation(new_facts)
                if confirmation_msg and whatsapp_provider:
                    send_result = whatsapp_provider.send_whatsapp(
                        message=confirmation_msg,
                        to=f"+{from_number}"
                    )
                    msg_id = send_result.get("message_id", "")
                    context_writer.store_pending(from_number, new_facts, msg_id)
                    print(f"   ✅ [FactID] Sent {len(new_facts)} fact(s) for confirmation")
            else:
                print("   ℹ️ [FactID] No new facts detected")
        except Exception as fact_err:
            print(f"   ⚠️ [FactID] Error: {fact_err}")
            import traceback
            traceback.print_exc()
        
        # Step 8: Detect unknown speakers and send "Who is this?" messages
        # This triggers the voice imprinting flow
        unknown_speakers_processed = []
        
        # SELF-IDENTIFICATION SKIP: Names to never ask about (user/owner)
        # These are considered "self" - the person using the bot
        self_names = {'itzik', 'itzhak', 'איציק', 'יצחק', 'speaker 1', 'speaker a', 'דובר 1'}
        
        # Add known speaker names from reference voices (these are already identified)
        for rv in reference_voices:
            self_names.add(rv['name'].lower())
        
        print(f"🔇 Self-identification skip list: {self_names}")
        
        try:
            from pydub import AudioSegment
            
            # Load audio for slicing
            audio_segment = AudioSegment.from_file(tmp_path)
            print(f"✅ Loaded audio for slicing: {len(audio_segment)}ms")
            
            # ============================================================
            # SMART SLICING ENGINE v3 — WebRTC VAD
            # Professional Voice Activity Detection + overlap-safe padding
            # Goal: 5-7 seconds of VERIFIED speech for unknown speakers
            # ============================================================
            
            TARGET_MIN_MS = 5000      # Target minimum: 5 seconds
            TARGET_MAX_MS = 7000      # Target maximum: 7 seconds
            ABS_MIN_MS = 1500         # Absolute minimum for a speech cluster
            PAD_BUFFER_MS = 500       # 0.5s buffer for natural sound
            FADE_MS = 40              # Fade in/out for clean cuts
            OVERLAP_MARGIN_MS = 300   # Safety margin around other speakers
            VAD_AGGRESSIVENESS = 1    # WebRTC VAD: 0=permissive, 3=strict. 1=forgiving for noisy envs
            VAD_FRAME_MS = 30         # Frame size for VAD analysis (10, 20, or 30ms)
            VAD_SAMPLE_RATE = 16000   # Sample rate for VAD (must be 8k/16k/32k/48k)
            MIN_SPEECH_CLUSTER_MS = 1500  # Min continuous speech block (1.5 seconds — short replies OK)
            MIN_SPEECH_RATIO = 0.40   # At least 40% of frames in cluster must be speech
            MAX_SCAN_MS = 30000       # Only scan first 30s of each turn
            FALLBACK_SLICE_MS = 5000  # Fallback: first 5s of longest segment
            MAX_VAD_RETRIES = 2       # Try 2 turns with VAD before falling back
            
            # ──────────────────────────────────────────────────────────────
            # STEP A: Build segment map for ALL speakers
            # ──────────────────────────────────────────────────────────────
            all_segments_by_speaker = {}
            unknown_speakers = set()
            
            for segment in segments:
                speaker = segment.get('speaker', '')
                if not speaker:
                    continue
                
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                    continue
                if end <= start:
                    continue
                
                if speaker not in all_segments_by_speaker:
                    all_segments_by_speaker[speaker] = []
                all_segments_by_speaker[speaker].append({
                    'speaker': speaker,
                    'start': start,
                    'end': end,
                    'start_ms': int(start * 1000),
                    'end_ms': int(end * 1000),
                    'text': segment.get('text', '')
                })
                
                speaker_lower = speaker.lower()
                is_unknown = (
                    speaker_lower.startswith('speaker ') or
                    speaker.startswith('דובר ') or
                    'unknown' in speaker_lower or
                    speaker_lower == 'speaker'
                )
                
                if is_unknown and speaker_lower not in self_names:
                    unknown_speakers.add(speaker)
            
            print(f"📊 All speakers: {list(all_segments_by_speaker.keys())}")
            print(f"📊 Unknown speakers needing ID: {list(unknown_speakers)}")
            
            if not unknown_speakers and summary_text:
                print("⚠️  No unknown speakers detected - all identified or skipped.")
            
            # ──────────────────────────────────────────────────────────────
            # STEP B: WebRTC VAD helpers
            # ──────────────────────────────────────────────────────────────
            
            # Initialize WebRTC VAD (with graceful fallback)
            vad = None
            try:
                import webrtcvad
                vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
                print(f"✅ [VAD] WebRTC VAD initialized (aggressiveness={VAD_AGGRESSIVENESS})")
            except ImportError:
                print("⚠️  [VAD] webrtcvad not installed — falling back to RMS-based detection")
            except Exception as vad_init_err:
                print(f"⚠️  [VAD] WebRTC VAD init failed ({vad_init_err}) — falling back to RMS")
            
            def get_other_segments(target_speaker):
                """Get all segments from speakers other than target."""
                other = []
                for spk, segs in all_segments_by_speaker.items():
                    if spk != target_speaker:
                        other.extend(segs)
                return other
            
            def calc_overlap_ms(seg_start_ms, seg_end_ms, other_segs):
                """Calculate total ms of overlap with other speakers' segments."""
                total = 0
                for o in other_segs:
                    o_start = o['start_ms'] - OVERLAP_MARGIN_MS
                    o_end = o['end_ms'] + OVERLAP_MARGIN_MS
                    overlap_start = max(seg_start_ms, o_start)
                    overlap_end = min(seg_end_ms, o_end)
                    if overlap_end > overlap_start:
                        total += (overlap_end - overlap_start)
                return total
            
            def calc_safe_padding(start_ms, end_ms, other_segs, audio_len_ms):
                """Add 0.5s buffer but stop at other speaker boundaries."""
                safe_start = max(0, start_ms - PAD_BUFFER_MS)
                safe_end = min(audio_len_ms, end_ms + PAD_BUFFER_MS)
                
                for o in other_segs:
                    if o['end_ms'] > safe_start and o['end_ms'] <= start_ms:
                        safe_start = max(safe_start, o['end_ms'] + 100)
                for o in other_segs:
                    if o['start_ms'] >= end_ms and o['start_ms'] < safe_end:
                        safe_end = min(safe_end, o['start_ms'] - 100)
                
                return safe_start, safe_end
            
            def vad_analyze_clip(audio_clip, log_format=False):
                """
                Run WebRTC VAD frame-by-frame on an audio clip.
                
                webrtcvad REQUIRES: 16-bit PCM, mono, 8000/16000/32000/48000 Hz.
                We explicitly convert and verify before passing frames.
                
                Returns: list of (frame_offset_ms, is_speech) tuples, or None on failure.
                """
                if vad is None:
                    return None  # Signal to use RMS fallback
                
                try:
                    # ── MANDATORY CONVERSION to VAD-compatible format ──
                    # webrtcvad will return False for ALL frames if format is wrong
                    pcm_clip = audio_clip.set_frame_rate(VAD_SAMPLE_RATE).set_channels(1).set_sample_width(2)
                    raw_data = pcm_clip.raw_data
                    
                    if log_format:
                        print(f"      📐 [VAD] Audio format: {pcm_clip.frame_rate}Hz, {pcm_clip.channels}ch, {pcm_clip.sample_width*8}-bit, {len(raw_data)} bytes")
                    
                    # Verify format is correct
                    if pcm_clip.frame_rate != VAD_SAMPLE_RATE:
                        print(f"      ❌ [VAD] ERROR: frame_rate={pcm_clip.frame_rate} (expected {VAD_SAMPLE_RATE})")
                        return None
                    if pcm_clip.channels != 1:
                        print(f"      ❌ [VAD] ERROR: channels={pcm_clip.channels} (expected 1)")
                        return None
                    if pcm_clip.sample_width != 2:
                        print(f"      ❌ [VAD] ERROR: sample_width={pcm_clip.sample_width} (expected 2)")
                        return None
                    
                    bytes_per_frame = VAD_SAMPLE_RATE * 2 * VAD_FRAME_MS // 1000  # 16-bit = 2 bytes/sample
                    total_frames = len(raw_data) // bytes_per_frame
                    
                    if total_frames == 0:
                        print(f"      ⚠️  [VAD] No complete frames in {len(raw_data)} bytes")
                        return None
                    
                    results = []
                    for i in range(total_frames):
                        offset = i * bytes_per_frame
                        frame = raw_data[offset:offset + bytes_per_frame]
                        if len(frame) < bytes_per_frame:
                            break
                        is_speech = vad.is_speech(frame, VAD_SAMPLE_RATE)
                        frame_offset_ms = i * VAD_FRAME_MS
                        results.append((frame_offset_ms, is_speech))
                    
                    return results
                except Exception as vad_err:
                    print(f"      ⚠️  [VAD] Frame analysis failed: {vad_err}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            def find_best_speech_cluster(vad_results, clip_duration_ms):
                """
                Find the longest continuous block where majority of frames
                are speech. A 'cluster' is a contiguous run where ≥50% of
                frames in any sliding window are speech.
                
                Returns: (cluster_start_ms, cluster_end_ms, speech_ratio, confidence)
                         or None if no valid cluster found.
                """
                if not vad_results:
                    return None
                
                total_frames = len(vad_results)
                speech_flags = [is_speech for (_, is_speech) in vad_results]
                
                # ── Find all speech "runs" (consecutive speech frames) ──
                # Allow small gaps (up to 3 frames = 90ms) inside a cluster
                # This handles natural micro-pauses mid-sentence
                GAP_TOLERANCE = 3  # frames (~90ms)
                
                # Smooth: fill small gaps between speech frames
                smoothed = list(speech_flags)
                for i in range(len(smoothed)):
                    if not smoothed[i]:
                        # Check if there's speech within GAP_TOLERANCE on both sides
                        left_speech = any(smoothed[max(0, i-GAP_TOLERANCE):i])
                        right_speech = any(smoothed[i+1:min(len(smoothed), i+1+GAP_TOLERANCE)])
                        if left_speech and right_speech:
                            smoothed[i] = True
                
                # ── Find contiguous speech clusters ──
                clusters = []
                cluster_start = None
                
                for i, is_speech in enumerate(smoothed):
                    if is_speech and cluster_start is None:
                        cluster_start = i
                    elif not is_speech and cluster_start is not None:
                        cluster_end = i
                        clusters.append((cluster_start, cluster_end))
                        cluster_start = None
                
                if cluster_start is not None:
                    clusters.append((cluster_start, len(smoothed)))
                
                if not clusters:
                    return None
                
                # ── Score each cluster ──
                best = None
                best_score = -1
                
                for c_start, c_end in clusters:
                    c_len_frames = c_end - c_start
                    c_duration_ms = c_len_frames * VAD_FRAME_MS
                    
                    if c_duration_ms < MIN_SPEECH_CLUSTER_MS:
                        continue  # Skip clusters shorter than 2s
                    
                    # Calculate actual speech ratio (from original, not smoothed)
                    actual_speech = sum(1 for f in speech_flags[c_start:c_end] if f)
                    ratio = actual_speech / c_len_frames if c_len_frames > 0 else 0
                    
                    if ratio < MIN_SPEECH_RATIO:
                        continue  # Not enough speech in this cluster
                    
                    # Score: prefer longer clusters with higher speech ratio
                    score = c_duration_ms * ratio
                    
                    if score > best_score:
                        best_score = score
                        start_ms = vad_results[c_start][0]
                        end_ms = vad_results[min(c_end, total_frames) - 1][0] + VAD_FRAME_MS
                        confidence = 'High' if ratio >= 0.75 else 'Low'
                        best = (start_ms, end_ms, ratio, confidence)
                
                return best
            
            def rms_fallback_check(audio_clip):
                """RMS-based speech check as fallback when webrtcvad is unavailable."""
                clip_rms = audio_clip.rms
                if clip_rms < 200:
                    return False, 0.0, 'None'
                
                window_ms = 500
                total_windows = max(1, len(audio_clip) // window_ms)
                active = sum(1 for i in range(total_windows)
                             if audio_clip[i*window_ms:min((i+1)*window_ms, len(audio_clip))].rms >= 200)
                ratio = active / total_windows
                
                if ratio < 0.3:
                    return False, ratio, 'None'
                
                confidence = 'High' if ratio >= 0.6 else 'Low'
                return True, ratio, confidence
            
            # ──────────────────────────────────────────────────────────────
            # STEP C: Process each unknown speaker with VAD SMART SLICING
            # ──────────────────────────────────────────────────────────────
            
            def export_and_send_clip(audio_slice, speaker, clip_label):
                """
                Export audio clip and send via WhatsApp.
                Returns True if successfully sent, False otherwise.
                """
                import tempfile as tf
                slice_path = None
                
                try:
                    with tf.NamedTemporaryFile(delete=False, suffix='.ogg') as slice_file:
                        audio_slice.export(
                            slice_file.name, 
                            format='ogg',
                            codec='libopus',
                            parameters=['-b:a', '64k', '-ar', '48000']
                        )
                        slice_path = slice_file.name
                        slice_size = os.path.getsize(slice_path)
                        print(f"   💾 Exported: OGG/Opus ({slice_size} bytes) [{clip_label}]")
                except Exception as ogg_err:
                    print(f"   ⚠️  OGG export failed ({ogg_err}), falling back to MP3...")
                    with tf.NamedTemporaryFile(delete=False, suffix='.mp3') as slice_file:
                        audio_slice.export(
                            slice_file.name, 
                            format='mp3',
                            bitrate='128k',
                            parameters=['-ar', '44100']
                        )
                        slice_path = slice_file.name
                        slice_size = os.path.getsize(slice_path)
                        print(f"   💾 Exported: MP3/128k ({slice_size} bytes) [{clip_label}]")
                
                slice_files_to_cleanup.append(slice_path)
                
                if whatsapp_provider and hasattr(whatsapp_provider, 'send_audio'):
                    caption = f"🔊 זוהה דובר חדש: *{speaker}*\nמי זה/זו? (הגב עם השם)"
                    
                    audio_result = whatsapp_provider.send_audio(
                        audio_path=slice_path,
                        caption=caption,
                        to=f"+{from_number}"
                    )
                    
                    if audio_result.get('success'):
                        sent_msg_id = audio_result.get('caption_message_id') or audio_result.get('wam_id') or audio_result.get('message_id')
                        if sent_msg_id:
                            pending_identifications[sent_msg_id] = {
                                'file_path': slice_path,
                                'speaker_id': speaker
                            }
                            print(f"   📝 Pending identification stored: {sent_msg_id} -> {speaker}")
                            unknown_speakers_processed.append(speaker)
                            if slice_path in slice_files_to_cleanup:
                                slice_files_to_cleanup.remove(slice_path)
                        return True
                    else:
                        print(f"   ⚠️  Failed to send audio slice: {audio_result.get('error')}")
                        return False
                return False
            
            for speaker in unknown_speakers:
                print(f"\n{'═'*60}")
                print(f"❓ [VAD] SMART SLICING for unknown speaker: {speaker}")
                print(f"{'═'*60}")
                
                other_segs = get_other_segments(speaker)
                target_segs = all_segments_by_speaker.get(speaker, [])
                
                if not target_segs:
                    print(f"   ⚠️  No segments found for {speaker} - SKIPPING")
                    continue
                
                # Sort segments by start time (process in conversation order)
                target_segs_sorted = sorted(target_segs, key=lambda s: s['start_ms'])
                
                print(f"   📋 Speaker has {len(target_segs_sorted)} turn(s):")
                for idx, s in enumerate(target_segs_sorted):
                    dur = s['end_ms'] - s['start_ms']
                    overlap = calc_overlap_ms(s['start_ms'], s['end_ms'], other_segs)
                    print(f"      Turn {idx}: {s['start']:.1f}s-{s['end']:.1f}s ({dur}ms) overlap={overlap}ms")
                
                clip_sent = False
                vad_rejections = 0  # Count VAD rejections for fallback trigger
                
                # ── Iterate through turns until we find clear speech ──
                for turn_idx, turn_seg in enumerate(target_segs_sorted):
                    if clip_sent:
                        break
                    
                    turn_start_ms = turn_seg['start_ms']
                    turn_end_ms = turn_seg['end_ms']
                    turn_duration = turn_end_ms - turn_start_ms
                    
                    if turn_duration < 500:  # Lowered from 1000 — even short replies matter
                        print(f"\n   ⏭️  Turn {turn_idx}: too short ({turn_duration}ms) - skipping")
                        continue
                    
                    # Cap scan to first 30 seconds of this turn
                    scan_end_ms = min(turn_end_ms, turn_start_ms + MAX_SCAN_MS)
                    
                    print(f"\n   🔍 [VAD] Analyzing Turn {turn_idx}: {turn_start_ms}ms → {scan_end_ms}ms ({scan_end_ms - turn_start_ms}ms)")
                    
                    # Extract the audio for this turn
                    turn_audio = audio_segment[turn_start_ms:scan_end_ms]
                    
                    if len(turn_audio) < 500:
                        print(f"      ⏭️  Audio too short after extraction - skipping")
                        continue
                    
                    # ── WebRTC VAD Frame-by-Frame Analysis ──
                    vad_results = vad_analyze_clip(turn_audio, log_format=(turn_idx == 0))
                    
                    speech_cluster = None
                    vad_confidence = 'None'
                    
                    if vad_results is not None:
                        total_frames = len(vad_results)
                        speech_frames = sum(1 for _, is_speech in vad_results if is_speech)
                        overall_ratio = speech_frames / total_frames if total_frames > 0 else 0
                        
                        print(f"      📊 [VAD] Frames: {total_frames} total, {speech_frames} speech ({overall_ratio:.0%})")
                        
                        # Find best continuous speech cluster
                        speech_cluster = find_best_speech_cluster(vad_results, len(turn_audio))
                        
                        if speech_cluster:
                            cl_start, cl_end, cl_ratio, vad_confidence = speech_cluster
                            print(f"      🎯 [VAD] Best speech cluster: {cl_start}ms-{cl_end}ms ({cl_end-cl_start}ms, {cl_ratio:.0%} speech, confidence={vad_confidence})")
                        else:
                            vad_rejections += 1
                            print(f"      ❌ [VAD] Rejected clip for {speaker} (No speech cluster ≥{MIN_SPEECH_CLUSTER_MS}ms found, rejection #{vad_rejections})")
                            
                            # Check if we should trigger fallback
                            if vad_rejections >= MAX_VAD_RETRIES:
                                print(f"      🔄 [VAD] {MAX_VAD_RETRIES} rejections reached — triggering FALLBACK SLICER")
                                break  # Exit turn loop, fallback will handle it
                            continue
                    else:
                        # ── RMS Fallback (webrtcvad not available) ──
                        print(f"      📊 [RMS Fallback] Running RMS-based check...")
                        rms_passed, rms_ratio, vad_confidence = rms_fallback_check(turn_audio)
                        
                        if not rms_passed:
                            vad_rejections += 1
                            print(f"      ❌ [VAD] Rejected clip for {speaker} (RMS confidence too low: {rms_ratio:.0%}, rejection #{vad_rejections})")
                            if vad_rejections >= MAX_VAD_RETRIES:
                                print(f"      🔄 [VAD] {MAX_VAD_RETRIES} rejections reached — triggering FALLBACK SLICER")
                                break
                            continue
                        
                        print(f"      ✅ [RMS] Passed: speech ratio={rms_ratio:.0%}, confidence={vad_confidence}")
                        speech_cluster = (0, len(turn_audio), rms_ratio, vad_confidence)
                    
                    # ── DYNAMIC SLICING around the speech cluster ──
                    cluster_start_in_turn, cluster_end_in_turn, cluster_ratio, confidence = speech_cluster
                    
                    # Convert cluster offsets to absolute audio positions
                    abs_cluster_start = turn_start_ms + cluster_start_in_turn
                    abs_cluster_end = turn_start_ms + cluster_end_in_turn
                    cluster_duration = abs_cluster_end - abs_cluster_start
                    
                    print(f"      📍 Cluster in absolute audio: {abs_cluster_start}ms → {abs_cluster_end}ms ({cluster_duration}ms)")
                    
                    # Determine slice window: 5-7s centered on the speech cluster
                    if cluster_duration >= TARGET_MIN_MS:
                        if cluster_duration > TARGET_MAX_MS:
                            center = (abs_cluster_start + abs_cluster_end) // 2
                            slice_start = center - TARGET_MAX_MS // 2
                            slice_end = center + TARGET_MAX_MS // 2
                        else:
                            slice_start = abs_cluster_start
                            slice_end = abs_cluster_end
                    else:
                        center = (abs_cluster_start + abs_cluster_end) // 2
                        slice_start = center - TARGET_MIN_MS // 2
                        slice_end = center + TARGET_MIN_MS // 2
                    
                    # Apply overlap-safe padding (500ms natural buffer)
                    slice_start, slice_end = calc_safe_padding(
                        slice_start, slice_end, other_segs, len(audio_segment)
                    )
                    
                    # Clamp to audio bounds
                    slice_start = max(0, slice_start)
                    slice_end = min(len(audio_segment), slice_end)
                    
                    # Ensure minimum duration
                    if (slice_end - slice_start) < ABS_MIN_MS:
                        print(f"      ⚠️  Slice too short after padding ({slice_end - slice_start}ms) - skipping turn")
                        vad_rejections += 1
                        if vad_rejections >= MAX_VAD_RETRIES:
                            break
                        continue
                    
                    # Cap at 7s max
                    if (slice_end - slice_start) > TARGET_MAX_MS:
                        slice_end = slice_start + TARGET_MAX_MS
                    
                    print(f"      ✂️  Slice window: {slice_start}ms → {slice_end}ms ({slice_end - slice_start}ms)")
                    
                    # ── SLICE AUDIO ──
                    audio_slice = audio_segment[slice_start:slice_end]
                    
                    # ── FINAL VAD VERIFICATION (lenient — 20% speech is OK) ──
                    if vad is not None:
                        final_vad = vad_analyze_clip(audio_slice)
                        if final_vad:
                            final_speech = sum(1 for _, s in final_vad if s)
                            final_ratio = final_speech / len(final_vad) if final_vad else 0
                            if final_ratio < 0.20:
                                vad_rejections += 1
                                print(f"      ❌ [VAD] Final clip verification FAILED: only {final_ratio:.0%} speech (rejection #{vad_rejections})")
                                print(f"      ❌ [VAD] Rejected clip for {speaker} (Confidence too low: {final_ratio:.0%})")
                                if vad_rejections >= MAX_VAD_RETRIES:
                                    break
                                continue
                            print(f"      ✅ [VAD] Final clip verified: {final_ratio:.0%} speech ({final_speech}/{len(final_vad)} frames)")
                    
                    # ── AUDIO ENHANCEMENTS ──
                    try:
                        target_dbfs = -16.0
                        current_dbfs = audio_slice.dBFS
                        if current_dbfs != float('-inf') and current_dbfs < 0:
                            gain = target_dbfs - current_dbfs
                            gain = max(min(gain, 20.0), -10.0)
                            audio_slice = audio_slice.apply_gain(gain)
                        audio_slice = audio_slice.fade_in(FADE_MS).fade_out(FADE_MS)
                    except Exception as enhance_err:
                        print(f"      ⚠️  Enhancement failed: {enhance_err}")
                    
                    # ── [VAD] VERIFICATION LOG ──
                    final_duration = len(audio_slice)
                    print(f"\n   ✂️  ═══ [VAD] FINAL CLIP for {speaker} ═══")
                    print(f"      📍 Turn {turn_idx}: {turn_start_ms}ms → {turn_end_ms}ms")
                    print(f"      📍 Speech cluster: {abs_cluster_start}ms → {abs_cluster_end}ms ({cluster_duration}ms)")
                    print(f"      📍 Final slice: {slice_start}ms → {slice_end}ms ({final_duration}ms / {final_duration/1000:.1f}s)")
                    print(f"      🔊 Volume: {audio_slice.dBFS:.1f} dBFS")
                    print(f"      🎯 Speech ratio: {cluster_ratio:.0%} | Confidence: {confidence}")
                    print(f"      💬 Text: \"{turn_seg.get('text', '')[:80]}\"")
                    print(f"   [VAD] Clip generated for {speaker} at {slice_start}ms-{slice_end}ms with confidence {confidence}")
                    
                    # ── EXPORT & SEND ──
                    if export_and_send_clip(audio_slice, speaker, f"VAD-{confidence}"):
                        clip_sent = True
                        break
                
                # ══════════════════════════════════════════════════════════
                # FALLBACK SLICER: If VAD failed after retries, send the
                # first 5 seconds of the LONGEST segment regardless.
                # A slightly noisy clip is better than NO clip.
                # ══════════════════════════════════════════════════════════
                if not clip_sent and target_segs_sorted:
                    print(f"\n   🔄 ═══ FALLBACK SLICER for {speaker} ═══")
                    print(f"      VAD rejected {vad_rejections} clip(s). Using brute-force slice.")
                    
                    # Pick the LONGEST segment
                    longest_seg = max(target_segs_sorted, key=lambda s: s['end_ms'] - s['start_ms'])
                    fb_start = longest_seg['start_ms']
                    fb_end = min(longest_seg['end_ms'], fb_start + FALLBACK_SLICE_MS)
                    fb_duration = fb_end - fb_start
                    
                    print(f"      📍 Longest segment: {longest_seg['start']:.1f}s-{longest_seg['end']:.1f}s ({longest_seg['end_ms'] - longest_seg['start_ms']}ms)")
                    print(f"      📍 Fallback slice: {fb_start}ms → {fb_end}ms ({fb_duration}ms)")
                    
                    if fb_duration >= 500:
                        # Apply safe padding
                        fb_start, fb_end = calc_safe_padding(fb_start, fb_end, other_segs, len(audio_segment))
                        fb_start = max(0, fb_start)
                        fb_end = min(len(audio_segment), fb_end)
                        
                        fallback_slice = audio_segment[fb_start:fb_end]
                        
                        # Enhance
                        try:
                            target_dbfs = -16.0
                            current_dbfs = fallback_slice.dBFS
                            if current_dbfs != float('-inf') and current_dbfs < 0:
                                gain = target_dbfs - current_dbfs
                                gain = max(min(gain, 20.0), -10.0)
                                fallback_slice = fallback_slice.apply_gain(gain)
                            fallback_slice = fallback_slice.fade_in(FADE_MS).fade_out(FADE_MS)
                        except Exception:
                            pass
                        
                        print(f"      🔊 Fallback volume: {fallback_slice.dBFS:.1f} dBFS | Duration: {len(fallback_slice)}ms")
                        print(f"   [VAD] Clip generated for {speaker} at {fb_start}ms-{fb_end}ms with confidence Fallback")
                        
                        if export_and_send_clip(fallback_slice, speaker, "FALLBACK"):
                            clip_sent = True
                    
                    if not clip_sent:
                        print(f"      ❌ Fallback also failed for {speaker}")
                
                # ── Final status ──
                if not clip_sent:
                    print(f"\n   🚫 [VAD] No clear speech detected for {speaker}")
                    print(f"      Scanned {len(target_segs_sorted)} turn(s), {vad_rejections} VAD rejection(s).")
                    print(f"      ❌ NOT sending 'מי זה?' — no valid audio clip available.")
                
        except ImportError:
            print("⚠️  pydub not installed - cannot slice audio for speaker identification")
        except Exception as slice_error:
            print(f"⚠️  Error during speaker identification slicing: {slice_error}")
            import traceback
            traceback.print_exc()
        
        print(f"✅ [Diarization] Speaker identification: {len(unknown_speakers_processed)} unknown speakers queued")
        
        # ============================================================
        # SMART NOTIFICATION SEQUENCE
        # Message 1: Expert Summary (Sentiment, Analysis, Action Items)
        # Message 2: Unknown Speaker Queries (if any) - sent above
        # ============================================================
        print("📱 [WhatsApp Notification] Building smart notification sequence...")
        
        # Count speakers
        all_speakers = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker:
                all_speakers.add(speaker)
        
        identified_speakers = []
        unidentified_count = 0
        
        for speaker in all_speakers:
            speaker_lower = speaker.lower()
            is_unknown = (
                speaker_lower.startswith('speaker ') or
                speaker.startswith('דובר ') or
                'unknown' in speaker_lower or
                speaker_lower == 'speaker' or
                speaker_lower == 'unknown' or
                speaker == ''
            )
            if is_unknown:
                unidentified_count += 1
            else:
                identified_speakers.append(speaker)
        
        # ============================================================
        # MESSAGE 1: EXPERT SUMMARY (Primary notification)
        # ============================================================
        # DEBUG: Log what we have before deciding which message to send
        print(f"📊 [WhatsApp] Decision point:")
        print(f"   expert_analysis_result is None: {expert_analysis_result is None}")
        if expert_analysis_result:
            print(f"   expert_analysis_result.get('success'): {expert_analysis_result.get('success')}")
            print(f"   expert_analysis_result.get('persona'): {expert_analysis_result.get('persona')}")
            raw_len = len(expert_analysis_result.get('raw_analysis', ''))
            print(f"   raw_analysis length: {raw_len} chars")
        
        if whatsapp_provider:
            if expert_analysis_result and expert_analysis_result.get('success'):
                # Use expert analysis as primary message
                from app.services.expert_analysis_service import expert_analysis_service
                expert_message = expert_analysis_service.format_for_whatsapp(expert_analysis_result)
                print(f"   📝 Expert message length: {len(expert_message)} chars")
                
                # Add speaker info header
                header = "✅ *ההקלטה נשמרה ונותחה!*\n\n"
                header += "👥 *משתתפים:* "
                if identified_speakers:
                    header += ", ".join(sorted(identified_speakers))
                if unidentified_count > 0:
                    header += f" (+{unidentified_count} לא מזוהים)"
                if not identified_speakers and unidentified_count == 0:
                    header += "(לא זוהו)"
                header += "\n\n"
                
                full_message = header + expert_message
                print(f"   📤 Total message length: {len(full_message)} chars")
                
                # Messages are now limited to ~1600 chars by expert_analysis_service
                # No splitting needed
                reply_result = whatsapp_provider.send_whatsapp(
                    message=full_message,
                    to=f"+{from_number}"
                )
                if reply_result.get('success'):
                    print("✅ [WhatsApp] Message 1 (Expert Summary) sent")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send expert summary: {reply_result.get('error')}")
            else:
                # Fallback: Basic summary if expert analysis failed
                print(f"   ⚠️  [CRITICAL] Using FALLBACK - expert analysis failed!")
                if expert_analysis_result:
                    print(f"   Error details: {expert_analysis_result.get('error', 'unknown')}")
                
                reply_message = "✅ *ההקלטה נשמרה!*\n\n"
                reply_message += "👥 *משתתפים:* "
                
                if identified_speakers:
                    reply_message += ", ".join(sorted(identified_speakers))
                if unidentified_count > 0:
                    if identified_speakers:
                        reply_message += f" (+{unidentified_count} לא מזוהים)"
                    else:
                        reply_message += f"{unidentified_count} דוברים לא מזוהים"
                if not identified_speakers and unidentified_count == 0:
                    reply_message += "(לא זוהו)"
                
                reply_message += "\n\n"
                
                # Use summary_text as fallback content
                if summary_text and len(summary_text.strip()) > 20:
                    # Truncate if too long
                    if len(summary_text) > 1200:
                        summary_text = summary_text[:1000] + "..."
                    reply_message += f"📝 *סיכום:*\n{summary_text}\n\n"
                else:
                    reply_message += "📝 *סיכום:* לא הצלחתי לייצר סיכום מפורט.\n\n"
                
                # Add Kaizen placeholder
                reply_message += "📈 *קאיזן:*\n"
                reply_message += "✓ לשימור: השיחה התקיימה והוקלטה\n"
                reply_message += "→ לשיפור: בדוק את איכות ההקלטה\n\n"
                
                reply_message += "📄 התמלול המלא זמין בדרייב."
                
                reply_result = whatsapp_provider.send_whatsapp(
                    message=reply_message,
                    to=f"+{from_number}"
                )
                if reply_result.get('success'):
                    print("✅ [WhatsApp] Message 1 (Fallback Summary) sent")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send fallback: {reply_result.get('error')}")
        
        # ============================================================
        # MESSAGE 2: UNKNOWN SPEAKER QUERIES
        # Already sent above during speaker processing loop
        # ============================================================
        if unknown_speakers_processed:
            print(f"✅ [WhatsApp] Message 2 (Speaker ID queries) sent for: {unknown_speakers_processed}")
        
        print(f"\n{'='*60}")
        print(f"✅ BACKGROUND AUDIO PROCESSING COMPLETED")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ BACKGROUND AUDIO ERROR: {e}")
        traceback.print_exc()
        _send_error_to_user(from_number, "שגיאה בעיבוד האודיו. נסה שוב מאוחר יותר.")
        
    finally:
        # ============================================================
        # CRITICAL CLEANUP - Prevents memory leaks on Render
        # ============================================================
        cleanup_count = 0
        
        # 1. Cleanup main temp files (audio downloads)
        for tmp_path in temp_files_to_cleanup:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    cleanup_count += 1
            except:
                pass
        
        # 2. Cleanup reference voice files
        for rv in reference_voices:
            try:
                file_path = rv.get('file_path', '')
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    cleanup_count += 1
            except:
                pass
        
        # 3. Cleanup audio slice files (from speaker identification)
        for slice_path in slice_files_to_cleanup:
            try:
                if os.path.exists(slice_path):
                    os.unlink(slice_path)
                    cleanup_count += 1
            except:
                pass
        
        print(f"🗑️  Cleanup complete: {cleanup_count} temp files deleted")


def _send_error_to_user(from_number: str, error_msg: str):
    """Send error message to user via WhatsApp."""
    if whatsapp_provider:
        try:
            whatsapp_provider.send_whatsapp(
                message=f"⚠️ {error_msg}",
                to=f"+{from_number}"
            )
        except:
            pass


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
                                
                                # ================================================================
                                # VOICE IMPRINTING INTERCEPTOR (THE WALL)
                                # Separates "Management" from "Chat" - 100% surgical
                                # ================================================================
                                if message_type == "text" and replied_message_id and replied_message_id in pending_identifications:
                                    print(f"\n{'='*60}")
                                    print(f"🎤 STRICT REPLY INTERCEPTOR ACTIVATED")
                                    print(f"{'='*60}")
                                    print(f"   This is a MANAGEMENT message, NOT a chat message!")
                                    print(f"   Replying to: {replied_message_id}")
                                    
                                    # Extract data from pending identification
                                    pending_data = pending_identifications.pop(replied_message_id)
                                    
                                    # Support both old format (string) and new format (dict)
                                    if isinstance(pending_data, str):
                                        file_path = pending_data
                                        speaker_id = "Unknown Speaker"
                                    else:
                                        file_path = pending_data.get('file_path', '')
                                        speaker_id = pending_data.get('speaker_id', 'Unknown Speaker')
                                    
                                    person_name = message_body_text.strip()
                                    
                                    print(f"   Speaker ID: {speaker_id}")
                                    print(f"   Real Name: {person_name}")
                                    print(f"   Audio file: {file_path}")
                                    
                                    # Mark message as processed to prevent duplicate processing
                                    mark_message_processed(message_id)
                                    
                                    # Step 1: Update Voice Map (Speaker ID -> Real Name)
                                    update_voice_map(speaker_id, person_name)
                                    print(f"✅ Voice map updated: {speaker_id} -> {person_name}")
                                    
                                    # Step 2: Upload voice signature to Drive (if file exists)
                                    upload_success = False
                                    if file_path and os.path.exists(file_path):
                                        file_id = drive_memory_service.upload_voice_signature(
                                            file_path=file_path,
                                            person_name=person_name
                                        )
                                        
                                        if file_id:
                                            upload_success = True
                                            print(f"✅ Voice signature saved (File ID: {file_id})")
                                        else:
                                            print(f"⚠️  Failed to upload voice signature")
                                        
                                        # Cleanup temp file
                                        try:
                                            os.unlink(file_path)
                                            print(f"🗑️  Cleaned up temp audio file")
                                        except:
                                            pass
                                    else:
                                        print(f"⚠️  Audio file no longer exists (may have timed out)")
                                    
                                    # Step 3: RETROACTIVE TRANSCRIPT UPDATE
                                    # Replace generic speaker ID with real name in recent transcripts
                                    try:
                                        updated_count = drive_memory_service.update_transcript_speaker(
                                            speaker_id=speaker_id,
                                            real_name=person_name,
                                            limit=5  # Update last 5 transcripts
                                        )
                                        if updated_count > 0:
                                            print(f"📝 Retroactive update: {updated_count} transcript(s) updated with '{person_name}'")
                                    except Exception as transcript_error:
                                        print(f"⚠️  Failed to update transcripts: {transcript_error}")
                                    
                                    # Step 3.5: RETROACTIVE SUMMARY UPDATE
                                    # Update expert analysis summaries in memory for RAG queries
                                    try:
                                        summary_updated = drive_memory_service.update_summary_speaker(
                                            speaker_id=speaker_id,
                                            real_name=person_name,
                                            limit=5  # Update last 5 audio entries in memory
                                        )
                                        if summary_updated > 0:
                                            print(f"📝 Retroactive summary update: {summary_updated} memory entries updated with '{person_name}'")
                                    except Exception as summary_error:
                                        print(f"⚠️  Failed to update summaries: {summary_error}")
                                    
                                    # Step 4: Send confirmation (surgical, no chat)
                                    if whatsapp_provider:
                                        confirmation = f"✅ למדתי, זה *{person_name}*. מעכשיו אזהה אותו/ה אוטומטית."
                                        whatsapp_provider.send_whatsapp(
                                            message=confirmation,
                                            to=f"+{from_number}"
                                        )
                                    
                                    print(f"🛑 INTERCEPTOR COMPLETE - Returning immediately (NO Gemini)")
                                    print(f"{'='*60}\n")
                                    
                                    # CRITICAL: STOP HERE. No chatting. No Gemini.
                                    continue
                                
                                # IDEMPOTENCY CHECK: Prevent duplicate processing due to webhook retries
                                if is_message_processed(message_id):
                                    print(f"⚠️  Duplicate message received (ID: {message_id}). Ignoring.")
                                    continue  # Skip processing, but return 200 OK to WhatsApp
                                
                                # Mark message as processed BEFORE processing (prevents race conditions)
                                mark_message_processed(message_id)
                                
                                # Handle audio messages - BACKGROUND PROCESSING to avoid 502 timeout
                                if message_type == "audio":
                                    print("🎤 Audio message detected - queuing for background processing...")
                                    
                                    # Get audio media info from message
                                    audio_data = message.get("audio", {})
                                    media_id = audio_data.get("id")
                                    
                                    if not media_id:
                                        print("❌ No media ID found in audio message")
                                        continue
                                    
                                    # Get WhatsApp API credentials
                                    from app.services.meta_whatsapp_service import meta_whatsapp_service
                                    if not meta_whatsapp_service.is_configured:
                                        print("❌ Meta WhatsApp service not configured")
                                        continue
                                    
                                    access_token = meta_whatsapp_service.access_token
                                    phone_number_id = meta_whatsapp_service.phone_number_id
                                    
                                    if not access_token:
                                        print("❌ WhatsApp API token not available")
                                        continue
                                    
                                    # NOTE: Acknowledgment moved to process_audio_in_background 
                                    # to avoid duplicate messages
                                    
                                    # Queue background processing - PREVENTS 502 TIMEOUT
                                    background_tasks.add_task(
                                        process_audio_in_background,
                                        message_id=message_id,
                                        from_number=from_number,
                                        media_id=media_id,
                                        access_token=access_token,
                                        phone_number_id=phone_number_id
                                    )
                                    
                                    print(f"✅ Audio processing queued in background for message {message_id}")
                                    # Return immediately - processing continues in background
                                    continue
                                
                                # NOTE: All audio processing moved to process_audio_in_background()
                                # The orphaned code below was the old inline audio processing - REMOVED
                                
                                # LEGACY AUDIO CODE REMOVED - See process_audio_in_background()
                                # All audio downloading, Gemini processing, and response sending
                                # now happens in the background to avoid 502 timeouts
                                
                                # Text message handling follows (elif block)
                                # Process message with memory
                                elif whatsapp_provider and message_type == "text" and message_body_text:
                                    
                                    # ================================================================
                                    # CURSOR COMMAND INTERCEPTOR: Remote Execution via WhatsApp
                                    # If message starts with "הרץ בקרסר", save to Drive for local Mac bridge
                                    # ================================================================
                                    CURSOR_COMMAND_PREFIXES = ["הרץ בקרסר", "שלח לקרסר"]
                                    matched_prefix = next((p for p in CURSOR_COMMAND_PREFIXES if message_body_text.strip().startswith(p)), None)
                                    if matched_prefix:
                                        print(f"\n{'='*60}")
                                        print(f"🎮 CURSOR COMMAND INTERCEPTOR ACTIVATED")
                                        print(f"{'='*60}")
                                        
                                        # Extract the prompt content (everything after the prefix)
                                        prompt_content = message_body_text[len(matched_prefix):].strip()
                                        
                                        if not prompt_content:
                                            # No content after prefix
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message="⚠️ לא קיבלתי תוכן לביצוע. שלח: 'הרץ בקרסר [הפקודה שלך]' או 'שלח לקרסר [הפקודה שלך]'",
                                                    to=f"+{from_number}"
                                                )
                                            continue
                                        
                                        print(f"📝 Prompt content: {prompt_content[:100]}...")
                                        
                                        # Save to Google Drive Cursor_Inbox folder
                                        try:
                                            file_id = drive_memory_service.save_cursor_command(prompt_content)
                                            
                                            if file_id:
                                                print(f"✅ Cursor command saved to Drive (file_id: {file_id})")
                                                
                                                # Send confirmation to user (Message 1)
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message="🚀 שלחתי לו",
                                                        to=f"+{from_number}"
                                                    )
                                            else:
                                                print(f"❌ Failed to save Cursor command")
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message="❌ נכשל בשמירת הפקודה. נסה שוב.",
                                                        to=f"+{from_number}"
                                                    )
                                        except Exception as cursor_error:
                                            print(f"❌ Cursor command error: {cursor_error}")
                                            import traceback
                                            traceback.print_exc()
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message=f"❌ שגיאה: {str(cursor_error)[:100]}",
                                                    to=f"+{from_number}"
                                                )
                                        
                                        print(f"🛑 CURSOR INTERCEPTOR COMPLETE - Returning immediately")
                                        print(f"{'='*60}\n")
                                        continue
                                    
                                    # ================================================================
                                    # ARCHITECTURE AUDIT INTERCEPTOR: Weekly Stack Analysis
                                    # Trigger: "בדוק את הסטאק" - runs the same function as Friday cron
                                    # ================================================================
                                    AUDIT_TRIGGER_PHRASES = ["בדוק את הסטאק", "סרוק את המערכת", "דוח ארכיטקטורה"]
                                    if any(phrase in message_body_text.strip() for phrase in AUDIT_TRIGGER_PHRASES):
                                        print(f"\n{'='*60}")
                                        print(f"🏗️ ARCHITECTURE AUDIT INTERCEPTOR ACTIVATED")
                                        print(f"{'='*60}")
                                        
                                        try:
                                            from app.services.architecture_audit_service import architecture_audit_service
                                            
                                            # Send "working on it" message
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message="🏗️ מריץ בדיקת ארכיטקטורה... זה עשוי לקחת כדקה.",
                                                    to=f"+{from_number}"
                                                )
                                            
                                            # Run the audit
                                            audit_result = architecture_audit_service.run_weekly_architecture_audit(
                                                drive_service=drive_memory_service
                                            )
                                            
                                            if audit_result.get('success'):
                                                report = audit_result.get('report', 'לא נוצר דו"ח')
                                                
                                                # Send the report via WhatsApp
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message=report,
                                                        to=f"+{from_number}"
                                                    )
                                                print(f"✅ Audit report sent ({len(report)} chars)")
                                            else:
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message=f"❌ בדיקת ארכיטקטורה נכשלה: {audit_result.get('error', 'Unknown error')}",
                                                        to=f"+{from_number}"
                                                    )
                                                    
                                        except Exception as audit_error:
                                            print(f"❌ Audit error: {audit_error}")
                                            import traceback
                                            traceback.print_exc()
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message=f"❌ שגיאה בבדיקה: {str(audit_error)[:100]}",
                                                    to=f"+{from_number}"
                                                )
                                        
                                        print(f"🛑 AUDIT INTERCEPTOR COMPLETE - Returning immediately")
                                        print(f"{'='*60}\n")
                                        continue
                                    
                                    # ================================================================
                                    # SMART IDENTITY RESOLVER: Digit Selection Handler
                                    # If user replies "1"-"9" and there's a pending options list,
                                    # resolve to the selected person and re-execute the query.
                                    # ================================================================
                                    from app.services.identity_resolver_service import identity_resolver
                                    
                                    resolved_selection = identity_resolver.try_resolve_digit(from_number, message_body_text)
                                    if resolved_selection:
                                        print(f"\n{'='*60}")
                                        print(f"🎯 IDENTITY RESOLVER: Digit selection → {resolved_selection.display_name}")
                                        print(f"   Re-executing query: {resolved_selection.pending_query}")
                                        print(f"{'='*60}")
                                        
                                        try:
                                            from app.services.knowledge_base_service import get_kb_query_context
                                            
                                            kb_context = get_kb_query_context()
                                            if kb_context:
                                                # Re-execute the original query with the resolved person name
                                                resolved_name = resolved_selection.display_name
                                                original_q = resolved_selection.pending_query
                                                # Inject the resolved name into context hint for Gemini
                                                enhanced_query = (
                                                    f"{original_q}\n\n"
                                                    f"[SYSTEM: The user selected '{resolved_name}' from an ambiguity menu. "
                                                    f"Answer ONLY about {resolved_name}.]"
                                                )
                                                
                                                kb_answer = gemini_service.answer_kb_query(
                                                    user_query=enhanced_query,
                                                    kb_context=kb_context
                                                )
                                                
                                                formatted_answer = f"📚 *תשובה מבסיס הידע:*\n\n{kb_answer}"
                                                
                                                if whatsapp_provider:
                                                    whatsapp_provider.send_whatsapp(
                                                        message=formatted_answer,
                                                        to=f"+{from_number}"
                                                    )
                                                    print(f"   ✅ Resolved KB answer sent ({len(formatted_answer)} chars)")
                                                
                                                # Update session context from the answer
                                                person = resolved_selection.person
                                                identity_resolver.update_context(
                                                    phone=from_number,
                                                    department=person.get("department", ""),
                                                    manager=person.get("reports_to", ""),
                                                    entity=person,
                                                )
                                                
                                                # Save interaction to memory
                                                new_interaction = {
                                                    "user_message": message_body_text,
                                                    "ai_response": formatted_answer,
                                                    "timestamp": datetime.utcnow().isoformat() + "Z",
                                                    "message_id": message_id,
                                                    "from_number": from_number,
                                                    "type": "kb_query_resolved"
                                                }
                                                drive_memory_service.update_memory(new_interaction, background_tasks=background_tasks)
                                        
                                        except Exception as resolve_err:
                                            print(f"   ❌ Resolver error: {resolve_err}")
                                            import traceback
                                            traceback.print_exc()
                                        
                                        print(f"🛑 IDENTITY RESOLVER COMPLETE")
                                        print(f"{'='*60}\n")
                                        continue
                                    
                                    # ================================================================
                                    # CONTEXT WRITER: Fact Confirmation Handler
                                    # If user replies "כן"/"לא"/digits after a fact-confirmation msg,
                                    # apply or reject the pending facts.
                                    # ================================================================
                                    from app.services.context_writer_service import context_writer
                                    
                                    if context_writer.has_pending(from_number):
                                        confirmation_result = context_writer.try_confirm_facts(from_number, message_body_text)
                                        if confirmation_result is not None:
                                            print(f"\n{'='*60}")
                                            print(f"🧠 CONTEXT WRITER: Fact confirmation received")
                                            print(f"{'='*60}")
                                            
                                            confirmed = confirmation_result.confirmed_facts
                                            rejected = confirmation_result.rejected_facts
                                            
                                            if confirmed:
                                                success_count, errors = context_writer.apply_facts(confirmed)
                                                reply = f"✅ עודכנו {success_count} עובדות בבסיס הידע."
                                                if errors:
                                                    reply += f"\n⚠️ {len(errors)} שגיאות: {'; '.join(errors[:3])}"
                                            else:
                                                reply = "👍 בוטל — לא עודכן דבר."
                                            
                                            if whatsapp_provider:
                                                whatsapp_provider.send_whatsapp(
                                                    message=reply,
                                                    to=f"+{from_number}"
                                                )
                                            
                                            print(f"   Confirmed: {len(confirmed)}, Rejected: {len(rejected)}")
                                            print(f"🛑 CONTEXT WRITER COMPLETE")
                                            print(f"{'='*60}\n")
                                            continue
                                    
                                    # ================================================================
                                    # CONVERSATION ENGINE — LLM-First Architecture
                                    # Replaces: regex intent detection, pronoun resolution,
                                    #           entity extraction, KB query routing, regular chat.
                                    # Gemini Chat Session handles ALL of it natively.
                                    # ================================================================
                                    try:
                                        # Single entry point — Gemini decides everything
                                        ai_response = conversation_engine.process_message(
                                            phone=from_number,
                                            message=message_body_text
                                        )
                                        
                                        print(f"🤖 Generated AI response: {ai_response[:100]}...")
                                        
                                        # Send AI response via WhatsApp
                                        reply_result = whatsapp_provider.send_whatsapp(
                                            message=ai_response,
                                            to=f"+{from_number}"
                                        )
                                        
                                        if reply_result.get('success'):
                                            print(f"✅ AI response sent successfully")
                                            
                                            # Save interaction to memory
                                            new_interaction = {
                                                "user_message": message_body_text,
                                                "ai_response": ai_response,
                                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                                "message_id": message_id,
                                                "from_number": from_number,
                                                "type": "conversation_engine"
                                            }
                                            drive_memory_service.update_memory(new_interaction, background_tasks=background_tasks)
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
                
                # Get session context and recent transcripts for RAG
                session_context = get_last_session_context()
                
                recent_transcripts = []
                search_keywords = ['מה', 'איך', 'מתי', 'למה', 'מי', 'החלטנו', 'דיברנו', 'אמר']
                if any(keyword in message_body for keyword in search_keywords):
                    try:
                        recent_transcripts = drive_memory_service.get_recent_transcripts(limit=2)
                        print(f"📚 Loaded {len(recent_transcripts)} recent transcripts for RAG")
                    except Exception as e:
                        print(f"⚠️  Failed to load recent transcripts: {e}")
                
                # Generate AI response with context, user profile, and RAG context
                ai_response = gemini_service.chat_with_memory(
                    user_message=message_body,
                    chat_history=chat_history,
                    user_profile=user_profile,
                    current_session=session_context,
                    recent_transcripts=recent_transcripts
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
        # MEMORY OPTIMIZATION: Use settings to limit signatures
        reference_voices = []
        if audio_paths and drive_memory_service.is_configured and settings.enable_multimodal_voice:
            try:
                max_sigs = settings.max_voice_signatures
                print(f"🎤 Retrieving voice signatures (max: {max_sigs})...")
                reference_voices = drive_memory_service.get_voice_signatures(max_signatures=max_sigs)
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
        elif audio_paths and not settings.enable_multimodal_voice:
            print("ℹ️  Multimodal voice comparison disabled (ENABLE_MULTIMODAL_VOICE=false)")
        
        # Initialize expert_analysis_result at top level for scope
        expert_analysis_result = None
        
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
                    
                    # ============================================================
                    # EXPERT ANALYSIS: Same analysis as WhatsApp flow
                    # ============================================================
                    expert_analysis_result = None
                    try:
                        from app.services.expert_analysis_service import expert_analysis_service
                        import asyncio
                        
                        if expert_analysis_service.is_configured and segments:
                            print(f"🧠 [/analyze] Running Expert Analysis on {len(segments)} segments...")
                            
                            # Load voice map
                            current_voice_map = {}
                            try:
                                memory = drive_memory_service.get_memory()
                                user_profile = memory.get('user_profile', {})
                                current_voice_map = user_profile.get('voice_map', {})
                            except:
                                pass
                            
                            # Run expert analysis
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                expert_analysis_result = loop.run_until_complete(
                                    expert_analysis_service.analyze_transcript(
                                        segments=segments,
                                        voice_map=current_voice_map
                                    )
                                )
                            finally:
                                loop.close()
                            
                            if expert_analysis_result and expert_analysis_result.get('success'):
                                print(f"✅ [/analyze] Expert Analysis complete - Persona: {expert_analysis_result.get('persona')}")
                            else:
                                print(f"⚠️  [/analyze] Expert Analysis failed: {expert_analysis_result.get('error') if expert_analysis_result else 'No result'}")
                    except Exception as expert_err:
                        print(f"⚠️  [/analyze] Expert Analysis error: {expert_err}")
                    
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
                        
                        # Include expert analysis in memory
                        if i == 0 and expert_analysis_result and expert_analysis_result.get('success'):
                            audio_interaction["expert_analysis"] = {
                                "persona": expert_analysis_result.get("persona"),
                                "persona_keys": expert_analysis_result.get("persona_keys"),
                                "context": expert_analysis_result.get("context"),
                                "speakers": expert_analysis_result.get("speakers"),
                                "raw_analysis": expert_analysis_result.get("raw_analysis"),
                                "timestamp": expert_analysis_result.get("timestamp")
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
                # Use Expert Analysis if available, otherwise fall back to basic formatting
                if expert_analysis_result and expert_analysis_result.get('success'):
                    from app.services.expert_analysis_service import expert_analysis_service
                    formatted_message = "✅ *ההקלטה נשמרה ונותחה!*\n\n"
                    formatted_message += expert_analysis_service.format_for_whatsapp(expert_analysis_result)
                    print("📊 Using Expert Analysis format for WhatsApp")
                else:
                    # Fallback: Format the summary message (using TwilioService formatter)
                    formatted_message = twilio_service.format_summary_message(result)
                    print("📊 Using basic format for WhatsApp (no expert analysis available)")
                
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
