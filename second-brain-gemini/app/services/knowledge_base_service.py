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
  - Robust PDF parsing: PyMuPDF (preserves layout) -> PyPDF2 fallback
  - Gemini-based PDF-to-JSON conversion for complex org charts (cached)
  - No content truncation for org-critical files

Cache lifecycle:
  - Loaded on first access (lazy init)
  - Cached for 1 hour (CACHE_TTL_SECONDS)
  - Force-refreshed if file count changes (new file detected)
  - Naturally cleared on restart/deployment (new process)
  - Structured JSON from Gemini PDF parsing cached separately
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
MAX_CONTEXT_CHARS = 30000  # Increased significantly — org charts need room
LOCAL_KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ── In-memory cache (thread-safe) ──
_cache_lock = Lock()
_cached_context: Optional[str] = None
_cached_file_list: List[str] = []
_cached_file_count: int = 0
_cache_timestamp: float = 0  # Unix timestamp of last cache refresh
_drive_connected: bool = False

# ── Cached structured JSON from Gemini PDF parsing ──
# Key: file_id, Value: {"json_text": str, "timestamp": float}
_pdf_json_cache: Dict[str, Dict[str, Any]] = {}
PDF_JSON_CACHE_TTL = 86400  # 24 hours — PDF doesn't change often


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
            pageSize=100  # Increased from 50 to ensure all files are listed
        ).execute()
        
        files = results.get('files', [])
        print(f"📚 [KB] Listed {len(files)} file(s) in Drive folder")
        for f in files:
            print(f"   📄 {f.get('name')} ({f.get('mimeType')}) [{f.get('size', '?')} bytes]")
        return files
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
                return _extract_pdf_text(raw_bytes, file_id)
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


def _extract_pdf_text(raw_bytes: bytes, file_id: str = "") -> str:
    """
    Extract text from PDF bytes using multiple strategies:
    
    Strategy 1: PyMuPDF (fitz) — preserves visual structure/layout
    Strategy 2: pdfplumber — good for tables
    Strategy 3: PyPDF2 — basic fallback
    Strategy 4: Gemini Flash — converts PDF to structured JSON (for org charts)
    
    If all text extraction produces less than 100 chars, triggers Gemini parsing.
    """
    extracted_text = ""
    
    # ── Strategy 1: PyMuPDF (best for preserving layout) ──
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        text_parts = []
        for page_num, page in enumerate(doc):
            # Use "text" mode which preserves reading order and layout
            page_text = page.get_text("text")
            if page_text and page_text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{page_text.strip()}")
        doc.close()
        
        if text_parts:
            extracted_text = "\n\n".join(text_parts)
            print(f"   ✅ [PDF] PyMuPDF extracted {len(extracted_text)} chars ({len(text_parts)} pages)")
    except ImportError:
        print(f"   ⚠️ [PDF] PyMuPDF not available, trying fallbacks...")
    except Exception as e:
        print(f"   ⚠️ [PDF] PyMuPDF failed: {e}")
    
    # ── Strategy 2: pdfplumber (good for tables) ──
    if not extracted_text or len(extracted_text.strip()) < 100:
        try:
            import pdfplumber
            pdf = pdfplumber.open(io.BytesIO(raw_bytes))
            text_parts = []
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text.strip()}")
                
                # Also extract tables if present
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = "\n".join([" | ".join([str(cell or "") for cell in row]) for row in table])
                        text_parts.append(f"[Table on Page {page_num + 1}]\n{table_text}")
            pdf.close()
            
            if text_parts:
                plumber_text = "\n\n".join(text_parts)
                # Use pdfplumber result if it's better
                if len(plumber_text) > len(extracted_text):
                    extracted_text = plumber_text
                    print(f"   ✅ [PDF] pdfplumber extracted {len(extracted_text)} chars")
        except ImportError:
            print(f"   ⚠️ [PDF] pdfplumber not available")
        except Exception as e:
            print(f"   ⚠️ [PDF] pdfplumber failed: {e}")
    
    # ── Strategy 3: PyPDF2 (basic fallback) ──
    if not extracted_text or len(extracted_text.strip()) < 100:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            if text_parts:
                pypdf2_text = "\n".join(text_parts)
                if len(pypdf2_text) > len(extracted_text):
                    extracted_text = pypdf2_text
                    print(f"   ✅ [PDF] PyPDF2 extracted {len(extracted_text)} chars")
        except ImportError:
            print(f"   ⚠️ [PDF] PyPDF2 not available")
        except Exception as e:
            print(f"   ⚠️ [PDF] PyPDF2 failed: {e}")
    
    # ── Strategy 4: Gemini Flash — convert PDF to structured JSON ──
    # If text extraction is too short or messy, use Gemini to parse the PDF
    if len(extracted_text.strip()) < 100:
        print(f"   🤖 [PDF] Text extraction too short ({len(extracted_text)} chars), trying Gemini parsing...")
        gemini_json = _parse_pdf_with_gemini(raw_bytes, file_id)
        if gemini_json:
            extracted_text = gemini_json
    elif file_id:
        # Even if we got text, check if we have a cached Gemini-parsed JSON version
        cached_json = _get_cached_pdf_json(file_id)
        if cached_json:
            # Append the structured JSON to the raw text for better answers
            extracted_text += "\n\n── Structured Organizational Data (Gemini-parsed) ──\n" + cached_json
            print(f"   📋 [PDF] Appended cached Gemini JSON ({len(cached_json)} chars)")
    
    if not extracted_text:
        extracted_text = "[PDF file — could not extract any text]"
        print(f"   ❌ [PDF] No text could be extracted from PDF")
    
    return extracted_text


def _get_cached_pdf_json(file_id: str) -> Optional[str]:
    """Get cached Gemini-parsed JSON for a PDF file."""
    if file_id in _pdf_json_cache:
        entry = _pdf_json_cache[file_id]
        age = time.time() - entry.get('timestamp', 0)
        if age < PDF_JSON_CACHE_TTL:
            return entry.get('json_text', '')
    return None


def _parse_pdf_with_gemini(raw_bytes: bytes, file_id: str = "") -> str:
    """
    Use Gemini Flash to convert a PDF (especially org charts) into
    structured JSON mapping every person to their manager and team.
    
    Result is cached for 24 hours.
    """
    # Check cache first
    if file_id:
        cached = _get_cached_pdf_json(file_id)
        if cached:
            print(f"   📋 [PDF→Gemini] Using cached JSON for {file_id[:20]}...")
            return cached
    
    try:
        import google.generativeai as genai
        import tempfile
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print(f"   ⚠️ [PDF→Gemini] No API key, skipping Gemini parsing")
            return ""
        
        genai.configure(api_key=api_key)
        
        # Save PDF to temp file for upload
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name
        
        try:
            # Upload PDF to Gemini
            file_ref = genai.upload_file(
                path=tmp_path,
                display_name="org_chart.pdf",
                mime_type="application/pdf"
            )
            
            # Wait for processing
            max_wait = 60
            start = time.time()
            while time.time() - start < max_wait:
                file_ref = genai.get_file(file_ref.name)
                state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                if state == "ACTIVE":
                    break
                elif state == "FAILED":
                    print(f"   ❌ [PDF→Gemini] File processing failed")
                    return ""
                time.sleep(2)
            
            # Use Gemini Flash to parse the PDF into structured JSON
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = """Analyze this document (likely an Org Chart or organizational document).

Convert ALL the information into a structured JSON format with the following schema:

{
  "organization": "Company/Organization Name",
  "people": [
    {
      "name": "Full Name",
      "role": "Job Title / Role",
      "department": "Department Name",
      "reports_to": "Manager's Full Name or null if top-level",
      "direct_reports": ["Name1", "Name2"],
      "team": "Team Name if applicable"
    }
  ],
  "hierarchy": {
    "CEO/Top Person Name": {
      "role": "CEO",
      "subordinates": {
        "VP Name": {
          "role": "VP",
          "subordinates": {
            "Manager Name": {
              "role": "Manager",
              "subordinates": {}
            }
          }
        }
      }
    }
  }
}

CRITICAL RULES:
- Extract EVERY person visible in the document
- Preserve ALL reporting relationships
- Include EVERY name, even if the role is unclear
- If the document is in Hebrew, keep names in Hebrew
- Output valid JSON only, no markdown code blocks
- Be thorough — missing a person means the user can't find them later"""
            
            response = model.generate_content(
                [prompt, file_ref],
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 4096
                }
            )
            
            result_text = ""
            try:
                result_text = response.text.strip() if response.text else ""
            except (ValueError, AttributeError):
                if hasattr(response, 'candidates') and response.candidates:
                    parts = response.candidates[0].content.parts
                    result_text = "".join(p.text for p in parts if hasattr(p, 'text'))
            
            # Clean up markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            # Validate it's valid JSON
            try:
                parsed = json.loads(result_text)
                # Re-serialize with nice formatting
                formatted_json = json.dumps(parsed, ensure_ascii=False, indent=2)
                
                # Cache the result
                if file_id:
                    _pdf_json_cache[file_id] = {
                        'json_text': formatted_json,
                        'timestamp': time.time()
                    }
                
                print(f"   ✅ [PDF→Gemini] Parsed PDF into structured JSON ({len(formatted_json)} chars)")
                return formatted_json
            except json.JSONDecodeError:
                # Not valid JSON but might still be useful text
                if len(result_text) > 50:
                    if file_id:
                        _pdf_json_cache[file_id] = {
                            'json_text': result_text,
                            'timestamp': time.time()
                        }
                    print(f"   ⚠️ [PDF→Gemini] Got text (not JSON) from Gemini ({len(result_text)} chars)")
                    return result_text
                return ""
            
            # Clean up uploaded file
            try:
                genai.delete_file(file_ref.name)
            except Exception:
                pass
        
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    except Exception as e:
        print(f"   ❌ [PDF→Gemini] Error: {e}")
        logger.error(f"[KB] Gemini PDF parsing failed: {e}")
        return ""


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
                        
                        print(f"   📥 Downloading: {file_name} ({mime_type})")
                        text = _download_file_content(service, file_id, mime_type)
                        
                        if text and text.strip():
                            # For PDFs that look like org charts, trigger Gemini parsing proactively
                            is_org_chart = any(kw in file_name.lower() for kw in [
                                'org', 'chart', 'hierarchy', 'structure', 'מבנה', 'ארגוני', 'היררכ'
                            ])
                            
                            if mime_type == 'application/pdf' and is_org_chart:
                                # Check if we need to parse with Gemini
                                cached_json = _get_cached_pdf_json(file_id)
                                if not cached_json:
                                    print(f"   🤖 [KB] Org chart detected — triggering Gemini parsing for: {file_name}")
                                    # Re-download raw bytes for Gemini
                                    try:
                                        from googleapiclient.http import MediaIoBaseDownload
                                        req = service.files().get_media(fileId=file_id)
                                        buf = io.BytesIO()
                                        dl = MediaIoBaseDownload(buf, req)
                                        done = False
                                        while not done:
                                            _, done = dl.next_chunk()
                                        gemini_result = _parse_pdf_with_gemini(buf.getvalue(), file_id)
                                        if gemini_result:
                                            text += "\n\n── Structured Organizational Data (Gemini-parsed) ──\n" + gemini_result
                                    except Exception as gemini_err:
                                        print(f"   ⚠️ [KB] Gemini PDF parsing failed: {gemini_err}")
                            
                            sections.append(f"══ {file_name} ══\n{text.strip()}")
                            loaded_names.append(file_name)
                            print(f"   ✅ Loaded: {file_name} ({len(text)} chars)")
                        else:
                            print(f"   ⚠️ Empty content from: {file_name}")
                    
                    # Combine and cache — NO truncation for critical org data
                    if sections:
                        combined = "\n\n".join(sections)
                        if len(combined) > MAX_CONTEXT_CHARS:
                            print(f"   ⚠️ [KB] Total context ({len(combined)} chars) exceeds limit ({MAX_CONTEXT_CHARS}). Trimming non-essential files.")
                            # Prioritize JSON and org chart files — trim others
                            combined = _smart_truncate(sections, MAX_CONTEXT_CHARS)
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
                    import traceback
                    traceback.print_exc()
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


def _smart_truncate(sections: List[str], max_chars: int) -> str:
    """
    Intelligently truncate content to fit within max_chars.
    
    Priority order (kept in full):
    1. JSON files (identity_context, etc.)
    2. PDF files with Gemini-parsed JSON
    3. TXT/MD files
    4. Other files (truncated first)
    """
    # Categorize sections by priority
    priority_high = []   # JSON, org chart files
    priority_medium = [] # TXT, MD, other structured
    priority_low = []    # Everything else
    
    for section in sections:
        header_line = section.split('\n')[0].lower()
        if '.json' in header_line or 'identity' in header_line or 'org' in header_line:
            priority_high.append(section)
        elif '.txt' in header_line or '.md' in header_line or 'context' in header_line:
            priority_medium.append(section)
        else:
            priority_low.append(section)
    
    result_parts = []
    remaining = max_chars
    
    # Add high priority first (full)
    for section in priority_high:
        if remaining > 0:
            result_parts.append(section[:remaining])
            remaining -= len(section)
    
    # Add medium priority
    for section in priority_medium:
        if remaining > 500:
            result_parts.append(section[:remaining])
            remaining -= len(section)
    
    # Add low priority (truncated if needed)
    for section in priority_low:
        if remaining > 500:
            truncated = section[:min(len(section), remaining)]
            result_parts.append(truncated)
            remaining -= len(truncated)
    
    return "\n\n".join(result_parts)


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
ORGANIZATIONAL SOURCE OF TRUTH — Knowledge Base (Live from Google Drive)
═══════════════════════════════════════════════════════════════════════════════

**CRITICAL INSTRUCTION:**
The following documents are the user's AUTHORITATIVE Knowledge Base.
Treat ALL data below — especially identity_context.json, org charts, and
personal context files — as the SINGLE SOURCE OF TRUTH for:
  • Organizational structure (who reports to whom)
  • Roles and titles
  • Team composition and hierarchy
  • Family relationships and personal context

**HIERARCHY NAVIGATION RULES:**
When asked about reporting lines, teams, or organizational questions:
1. Look for fields such as "subordinates", "team", "reports_to",
   "manager", "direct_reports", "children" (in org context), "role".
2. Navigate the hierarchy tree: if a person is listed as a Manager,
   list everyone in their sub-branch (direct and indirect reports).
3. If a name in a transcript matches a name in these documents,
   ALWAYS use the role/title from the Knowledge Base.

**PRIORITY:** Knowledge Base data OVERRIDES any assumptions or general
knowledge. If there is a conflict between transcript content and the
Knowledge Base, the Knowledge Base wins.

{context}
═══════════════════════════════════════════════════════════════════════════════
"""


def get_kb_query_context() -> str:
    """
    Returns the raw Knowledge Base content for direct fact-based queries.
    Used by the KB Query Interceptor to answer organizational questions
    without going through the full audio/transcript flow.
    
    Returns:
        Raw context string from all KB files, or empty string if unavailable.
    """
    return load_context() or ""


def force_refresh_pdf_cache(file_id: str = None):
    """
    Force refresh the Gemini-parsed PDF cache.
    If file_id is provided, only refresh that file.
    Otherwise, clear all PDF caches.
    """
    global _pdf_json_cache
    if file_id:
        _pdf_json_cache.pop(file_id, None)
        print(f"🔄 [KB] Cleared PDF cache for {file_id[:20]}...")
    else:
        _pdf_json_cache.clear()
        print(f"🔄 [KB] Cleared all PDF caches")


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
        "pdf_cache_count": len(_pdf_json_cache),
    }


def get_loaded_files() -> List[str]:
    """Return list of loaded file names (for debugging/status)."""
    load_context()
    return list(_cached_file_list)
