"""
Knowledge Base Service — Google Drive Personal Context Loader

Connects to a dedicated Google Drive folder (Second_Brain_Context)
and loads all files (.txt, .json, .pdf, .md) as personal context
for injection into Gemini system instructions.

Features:
  - Google Drive integration via OAuth 2.0 (reuses existing credentials)
  - 1-hour in-memory cache to avoid excessive Drive API calls
  - Force-refresh when new files are detected
  - Graceful fallback to local app/knowledge_base/ if Drive is unavailable
  - Text extraction for TXT, JSON, PDF, and Markdown files

Cache lifecycle:
  - Loaded on first access (lazy init)
  - Cached for 1 hour (CACHE_TTL_SECONDS)
  - Force-refreshed if file count changes (new file detected)
  - Naturally cleared on restart/deployment (new process)
"""

import json
import os
import io
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

# ── Configuration ──
CACHE_TTL_SECONDS = 3600  # 1 hour cache
MAX_CONTEXT_CHARS = 5000  # Max chars to inject into prompts
LOCAL_KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ── In-memory cache (thread-safe) ──
_cache_lock = Lock()
_cached_context: Optional[str] = None
_cached_file_list: List[str] = []
_cached_file_count: int = 0
_cache_timestamp: float = 0  # Unix timestamp of last cache refresh
_drive_connected: bool = False


def _get_drive_service():
    """
    Build a Google Drive API service using the same OAuth 2.0 credentials
    as DriveMemoryService (reuses GOOGLE_CLIENT_ID, etc.).
    
    Returns the Drive service object, or None if credentials are missing.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
        
        if not all([client_id, client_secret, refresh_token]):
            return None
        
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.warning(f"[KB] Could not build Drive service: {e}")
        return None


def _get_context_folder_id() -> Optional[str]:
    """Get the Knowledge Base folder ID from environment."""
    return os.environ.get("CONTEXT_FOLDER_ID")


def _list_drive_files(service, folder_id: str) -> List[Dict[str, Any]]:
    """
    List all files in the Knowledge Base Drive folder.
    Returns list of {id, name, mimeType, modifiedTime}.
    """
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime, size)",
            orderBy="name",
            pageSize=50
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        logger.error(f"[KB] Error listing Drive files: {e}")
        return []


def _download_file_content(service, file_id: str, mime_type: str) -> str:
    """
    Download and extract text content from a Drive file.
    Handles Google Docs (export as text) and binary files (direct download).
    """
    try:
        from googleapiclient.http import MediaIoBaseDownload
        
        # Google Docs types need to be exported
        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc as plain text
            request = service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            content = request.execute()
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='replace')
            return str(content)
        
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Export Google Sheet as CSV
            request = service.files().export_media(
                fileId=file_id,
                mimeType='text/csv'
            )
            content = request.execute()
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='replace')
            return str(content)
        
        else:
            # Regular file — direct download
            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            raw_bytes = buffer.getvalue()
            
            # Handle by file type
            if mime_type == 'application/pdf':
                return _extract_pdf_text(raw_bytes)
            elif mime_type == 'application/json':
                return _extract_json_text(raw_bytes)
            else:
                # Try as text (txt, md, etc.)
                try:
                    return raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    return raw_bytes.decode('latin-1', errors='replace')
    
    except Exception as e:
        logger.warning(f"[KB] Error downloading file {file_id}: {e}")
        return ""


def _extract_pdf_text(raw_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        return "[PDF file — install PyPDF2 to extract text]"
    except Exception as e:
        return f"[PDF extraction failed: {e}]"


def _extract_json_text(raw_bytes: bytes) -> str:
    """Extract readable text from JSON bytes."""
    try:
        data = json.loads(raw_bytes.decode('utf-8'))
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[JSON parse failed: {e}]"


def _load_from_local_fallback() -> str:
    """
    Fallback: Load from local app/knowledge_base/ folder
    if Google Drive is not configured.
    """
    if not LOCAL_KB_DIR.exists():
        return ""
    
    supported_ext = {'.txt', '.json', '.pdf', '.md', '.text'}
    files = sorted([
        f for f in LOCAL_KB_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in supported_ext and f.name != '.gitkeep'
    ])
    
    if not files:
        return ""
    
    sections = []
    for filepath in files:
        try:
            if filepath.suffix.lower() in ('.txt', '.md', '.text'):
                text = filepath.read_text(encoding='utf-8')
            elif filepath.suffix.lower() == '.json':
                data = json.loads(filepath.read_text(encoding='utf-8'))
                text = json.dumps(data, ensure_ascii=False, indent=2)
            elif filepath.suffix.lower() == '.pdf':
                text = _extract_pdf_text(filepath.read_bytes())
            else:
                continue
            
            if text and text.strip():
                sections.append(f"── {filepath.name} ──\n{text.strip()}")
        except Exception as e:
            logger.warning(f"[KB] Could not read local file {filepath.name}: {e}")
    
    return "\n\n".join(sections)


def load_context(force_reload: bool = False) -> str:
    """
    Load all files from the Second_Brain_Context Google Drive folder.
    
    Caching strategy:
      - Cache for 1 hour (CACHE_TTL_SECONDS)
      - Force-refresh if file count changed (new file detected)
      - Fallback to local files if Drive not configured
    
    Args:
        force_reload: If True, bypass cache and reload from Drive
    
    Returns:
        Combined text from all knowledge base files.
    """
    global _cached_context, _cached_file_list, _cached_file_count
    global _cache_timestamp, _drive_connected
    
    with _cache_lock:
        now = time.time()
        cache_age = now - _cache_timestamp
        
        # Check if cache is still valid
        if not force_reload and _cached_context is not None and cache_age < CACHE_TTL_SECONDS:
            return _cached_context
        
        # ── Try Google Drive first ──
        folder_id = _get_context_folder_id()
        
        if folder_id:
            service = _get_drive_service()
            
            if service:
                try:
                    files = _list_drive_files(service, folder_id)
                    
                    # Check if file count changed (force refresh trigger)
                    if not force_reload and _cached_context is not None and len(files) == _cached_file_count:
                        if cache_age < CACHE_TTL_SECONDS:
                            return _cached_context
                    
                    if not files:
                        print(f"📚 [Knowledge Base] Drive folder is empty (ID: {folder_id[:20]}...)")
                        _cached_context = ""
                        _cached_file_list = []
                        _cached_file_count = 0
                        _cache_timestamp = now
                        _drive_connected = True
                        return ""
                    
                    # Download and extract content from each file
                    sections = []
                    loaded_names = []
                    
                    for f in files:
                        file_name = f.get('name', 'Unknown')
                        file_id = f.get('id')
                        mime_type = f.get('mimeType', '')
                        
                        # Skip folders
                        if mime_type == 'application/vnd.google-apps.folder':
                            continue
                        
                        text = _download_file_content(service, file_id, mime_type)
                        
                        if text and text.strip():
                            sections.append(f"── {file_name} ──\n{text.strip()}")
                            loaded_names.append(file_name)
                    
                    # Combine and cache
                    if sections:
                        combined = "\n\n".join(sections)
                        if len(combined) > MAX_CONTEXT_CHARS:
                            combined = combined[:MAX_CONTEXT_CHARS] + "\n\n[...truncated — knowledge base too large]"
                        _cached_context = combined
                    else:
                        _cached_context = ""
                    
                    _cached_file_list = loaded_names
                    _cached_file_count = len(files)
                    _cache_timestamp = now
                    _drive_connected = True
                    
                    print(f"📚 [Knowledge Base] Loaded {len(loaded_names)} file(s) from Drive: {loaded_names} ({len(_cached_context)} chars)")
                    return _cached_context
                    
                except Exception as e:
                    logger.error(f"[KB] Drive load failed: {e}")
                    print(f"⚠️ [Knowledge Base] Drive load failed: {e}")
                    _drive_connected = False
        
        # ── Fallback to local files ──
        print(f"📚 [Knowledge Base] Using local fallback (CONTEXT_FOLDER_ID not set or Drive unavailable)")
        _drive_connected = False
        
        local_content = _load_from_local_fallback()
        _cached_context = local_content
        _cached_file_list = []
        _cached_file_count = 0
        _cache_timestamp = now
        
        if local_content:
            print(f"📚 [Knowledge Base] Loaded from local folder ({len(local_content)} chars)")
        else:
            print(f"📚 [Knowledge Base] No context files found (local or Drive)")
        
        return _cached_context


def get_system_instruction_block() -> str:
    """
    Returns a formatted block ready to inject into Gemini system instructions.
    If the knowledge base is empty, returns an empty string.
    """
    context = load_context()
    
    if not context:
        return ""
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
USER'S PERSONAL KNOWLEDGE BASE (Live from Google Drive)
═══════════════════════════════════════════════════════════════════════════════
You are an AI assistant with access to the user's live Knowledge Base from
Google Drive. Use the provided organizational chart, family roles, and
personal documents to ground your analysis. If a name in the transcript
matches a role in the context, prioritize that role's perspective.

Reference the roles, relationships, and identities found below to provide
100% accurate analysis.

{context}
═══════════════════════════════════════════════════════════════════════════════
"""


def get_status() -> Dict[str, Any]:
    """
    Return the current Knowledge Base status for health checks.
    
    Returns:
        Dict with connection status, file count, source, and cache age.
    """
    load_context()  # Ensure loaded
    
    folder_id = _get_context_folder_id()
    cache_age_sec = time.time() - _cache_timestamp if _cache_timestamp > 0 else -1
    
    return {
        "connected": _drive_connected or bool(_cached_context),
        "source": "Google Drive" if _drive_connected else ("Local" if _cached_context else "None"),
        "folder_id": folder_id[:20] + "..." if folder_id and len(folder_id) > 20 else folder_id,
        "file_count": len(_cached_file_list),
        "files": list(_cached_file_list),
        "chars": len(_cached_context) if _cached_context else 0,
        "cache_age_minutes": round(cache_age_sec / 60, 1) if cache_age_sec >= 0 else -1,
    }


def get_loaded_files() -> List[str]:
    """Return list of loaded file names (for debugging/status)."""
    load_context()
    return list(_cached_file_list)
