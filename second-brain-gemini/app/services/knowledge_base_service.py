"""
Knowledge Base Service — Vision-Powered Organizational Intelligence

v4.20 — Multi-Modal Vision Analysis + Semantic Identity Resolver

Architecture:
  1. Vision-Based PDF Analysis: Uses Gemini Pro to visually examine
     org charts as graph images, identifying nodes and connecting lines.
  2. Unified Identity Graph: Merges org chart + family_tree.json into
     a single identity space with cross-context resolution.
  3. Semantic Identity Resolver: Hebrew ↔ English phonetic matching,
     nickname resolution, and contextual identity linking.
  4. Hierarchical Graph: Recursive sub-tree traversal for reporting lines.

Cache lifecycle:
  - Raw files: 1-hour cache (CACHE_TTL_SECONDS)
  - Vision-parsed graph JSON: 24-hour cache (separate)
  - Unified identity graph: rebuilt when either source changes
  - Cleared on restart/deployment
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
CACHE_TTL_SECONDS = 3600     # 1 hour cache for raw files
MAX_CONTEXT_CHARS = 80000    # Gemini 2.5 Pro supports 1M+ tokens — 80K chars is safe
LOCAL_KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ── In-memory cache (thread-safe) ──
_cache_lock = Lock()
_cached_context: Optional[str] = None
_cached_file_list: List[str] = []
_cached_file_count: int = 0
_cache_timestamp: float = 0
_drive_connected: bool = False

# ── Vision-parsed graph cache (24h, cleared on restart) ──
# Key: file_id, Value: {"graph_json": str, "parsed_data": dict, "timestamp": float}
_vision_graph_cache: Dict[str, Dict[str, Any]] = {}
VISION_CACHE_TTL = 86400  # 24 hours
# NOTE: Cache is empty on process start → first request always triggers fresh vision analysis
# This ensures new deployments always get the latest parsing from the forced model

# ── Unified Identity Graph (built from all sources) ──
_identity_graph: Optional[Dict[str, Any]] = None
_identity_graph_timestamp: float = 0

# ── Structured JSON Data Cache (raw parsed org_structure + family_tree) ──
_org_structure_data: Optional[Dict[str, Any]] = None
_family_tree_data: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE ACCESS
# ═══════════════════════════════════════════════════════════════════════

def _get_drive_service():
    """Build Google Drive API service using OAuth 2.0 credentials."""
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
        
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning(f"[KB] Could not build Drive service: {e}")
        return None


def _get_context_folder_id() -> Optional[str]:
    return os.environ.get("CONTEXT_FOLDER_ID")


def _list_drive_files(service, folder_id: str) -> List[Dict[str, Any]]:
    """List ALL files in the Knowledge Base Drive folder."""
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime, size)",
            orderBy="name",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        print(f"📚 [KB] Listed {len(files)} file(s) in Drive folder")
        for f in files:
            print(f"   📄 {f.get('name')} ({f.get('mimeType')}) [{f.get('size', '?')} bytes]")
        return files
    except Exception as e:
        logger.error(f"[KB] Error listing Drive files: {e}")
        return []


def _download_raw_bytes(service, file_id: str, mime_type: str) -> bytes:
    """Download raw bytes from Drive. Handles Google native formats via export."""
    from googleapiclient.http import MediaIoBaseDownload
    
    if mime_type == 'application/vnd.google-apps.document':
        request = service.files().export_media(fileId=file_id, mimeType='text/plain')
        content = request.execute()
        return content if isinstance(content, bytes) else content.encode('utf-8')
    
    elif mime_type == 'application/vnd.google-apps.spreadsheet':
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        content = request.execute()
        return content if isinstance(content, bytes) else content.encode('utf-8')
    
    else:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()


def _download_file_content(service, file_id: str, file_name: str, mime_type: str) -> str:
    """Download and extract text content from a Drive file."""
    try:
        raw_bytes = _download_raw_bytes(service, file_id, mime_type)
        
        if mime_type == 'application/pdf':
            return _extract_pdf_with_vision(raw_bytes, file_id, file_name)
        elif mime_type == 'application/json':
            return _extract_json_text(raw_bytes, file_name=file_name)
        elif mime_type in ('application/vnd.google-apps.document',
                           'application/vnd.google-apps.spreadsheet'):
            return raw_bytes.decode('utf-8', errors='replace')
        elif mime_type.startswith('image/'):
            return _extract_image_with_vision(raw_bytes, file_id, file_name, mime_type)
        else:
            try:
                return raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return raw_bytes.decode('latin-1', errors='replace')
    except Exception as e:
        logger.warning(f"[KB] Error downloading file {file_name}: {e}")
        print(f"   ❌ Error downloading {file_name}: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════
# MULTI-MODAL VISION ANALYSIS (Source of Truth for PDFs)
# ═══════════════════════════════════════════════════════════════════════

def _extract_pdf_with_vision(raw_bytes: bytes, file_id: str = "", file_name: str = "") -> str:
    """
    Primary: Vision-based analysis using Gemini 1.5 Pro (forced model).
    The PDF is uploaded as a visual document and Gemini examines
    the layout, nodes, and connecting lines to build a graph.
    
    Strategy:
    - Cache hit → return cached vision graph (NO text extraction)
    - Cache miss → run vision analysis with MODEL_MAPPING["pro"]
    - If vision fails → fallback to text extraction
    
    The vision-parsed graph is the SOURCE OF TRUTH for org structure.
    Text extraction is ONLY used as a last resort if vision fails entirely.
    """
    # ── Step 1: Check vision cache (permanent until restart or 24h) ──
    if file_id:
        cached = _get_cached_vision_graph(file_id)
        if cached:
            print(f"   📋 [Vision] Using cached vision graph for {file_name} (no re-extraction)")
            return f"── Vision-Parsed Organizational Graph (Source of Truth) ──\n{cached}"
    
    # ── Step 2: Vision analysis with Gemini 1.5 Pro (forced) ──
    vision_result = _vision_analyze_pdf(raw_bytes, file_id, file_name)
    
    if vision_result:
        return f"── Vision-Parsed Organizational Graph (Source of Truth) ──\n{vision_result}"
    
    # ── Step 3: Text extraction ONLY as last resort ──
    print(f"   ⚠️ [Vision] Vision analysis failed, falling back to text extraction")
    text_fallback = _text_extract_pdf(raw_bytes)
    if text_fallback:
        return f"── Text Extract (fallback — vision unavailable) ──\n{text_fallback}"
    
    return "[PDF — could not extract content via vision or text]"


def _get_cached_vision_graph(file_id: str) -> Optional[str]:
    """Get cached vision-parsed graph JSON."""
    if file_id in _vision_graph_cache:
        entry = _vision_graph_cache[file_id]
        if time.time() - entry.get('timestamp', 0) < VISION_CACHE_TTL:
            return entry.get('graph_json', '')
    return None


def _vision_analyze_pdf(raw_bytes: bytes, file_id: str = "", file_name: str = "") -> str:
    """
    Upload PDF to Gemini 1.5 Pro (FORCED) and use VISION to analyze the
    visual layout of the organizational chart.
    
    Uses MODEL_MAPPING["pro"] for accurate vision. Falls back to MODEL_MAPPING["flash"]
    with a warning if Pro is unavailable.
    
    Returns structured JSON graph. Cached for 24 hours.
    """
    try:
        import google.generativeai as genai
        import tempfile
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print(f"   ⚠️ [Vision] No API key, skipping vision analysis")
            return ""
        
        from app.services.model_discovery import configure_genai, MODEL_MAPPING  # noqa
        configure_genai(api_key)
        
        # Save PDF to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name
        
        try:
            # Upload to Gemini
            print(f"   👁️ [Vision] Uploading PDF for visual analysis: {file_name}")
            file_ref = genai.upload_file(
                path=tmp_path,
                display_name=file_name or "document.pdf",
                mime_type="application/pdf"
            )
            
            # Wait for processing
            max_wait = 90
            start = time.time()
            while time.time() - start < max_wait:
                file_ref = genai.get_file(file_ref.name)
                state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                if state == "ACTIVE":
                    break
                elif state == "FAILED":
                    print(f"   ❌ [Vision] File processing failed")
                    return ""
                time.sleep(2)
            
            # ── Model selection: use MODEL_MAPPING static aliases (no models/ prefix) ──
            # Vision analysis still uses the SDK for file upload + generate_content
            # because file_ref objects require the SDK pipeline.
            # But we fall back to Flash via direct HTTP if Pro 404s.
            model_name = MODEL_MAPPING["pro"]   # latest pro model
            print(f"   👁️ [Vision] Using MODEL_MAPPING['pro']: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            vision_prompt = """Analyze this organizational chart IMAGE visually. This is a VISION task.

═══════════════════════════════════════════════════════════════════════
PHASE 1 — STRICT LINE-FOLLOWING PROTOCOL (trace lines BEFORE assigning roles)
═══════════════════════════════════════════════════════════════════════
1. Identify every BOX in the image. Each box contains a person's NAME and TITLE.
2. Trace every SOLID LINE connecting boxes:
   • A VERTICAL line going DOWN from Box A to Box B means B reports to A.
   • A HORIZONTAL branching line connecting multiple boxes at the same level
     means those boxes are PEERS — they share the same manager above the branch.
   • PEERS do NOT report to each other! They are equals.
3. Example: If Asaf Peled's box has a line going down to a horizontal branch,
   and that branch connects to Amber, Ofir, and Maylin — then all three report
   to Asaf Peled. Amber does NOT manage Ofir or Maylin; they are peers.
4. Only assign "manages" relationship when a DIRECT VERTICAL line descends
   from one box to another. No assumptions based on proximity.

═══════════════════════════════════════════════════════════════════════
PHASE 2 — TITLE ANCHOR RULE (read ONLY text inside each specific box)
═══════════════════════════════════════════════════════════════════════
1. For each person, read ONLY the text that is INSIDE their own box.
2. Do NOT mix titles from adjacent or nearby boxes.
   • WRONG: Giving Asaf Peled the title "Director, Market Success" (belongs to Itai Cohen's box)
   • CORRECT: Asaf Peled → "VP Product & Support" (text inside HIS box only)
3. If a box contains multiple lines of text, the NAME is usually the top line
   and the TITLE is the line(s) below the name.
4. Before finalizing each node: double-check that the title you assigned
   actually appears INSIDE that person's visual box boundary.

═══════════════════════════════════════════════════════════════════════
PHASE 3 — PEER RECOGNITION RULE
═══════════════════════════════════════════════════════════════════════
People whose boxes connect to the SAME horizontal branch line are PEERS:
• They share the same manager (the box ABOVE the branch).
• They do NOT manage each other.
• In direct_report_names of the manager above, list ALL peers equally.
• In edges, each peer gets a separate edge from the manager, with relationship "manages".
• None of the peers should have edges managing each other.

═══════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (strict JSON):
═══════════════════════════════════════════════════════════════════════
{
  "organization_name": "Company name if visible",
  "analysis_method": "vision_graph",
  "total_people_found": <number>,
  "nodes": [
    {
      "id": 1,
      "full_name": "Full Name exactly as written",
      "full_name_hebrew": "שם בעברית (if visible)",
      "full_name_english": "Name in English (if visible)",
      "title": "EXACT title as written INSIDE this person's box — NOT from adjacent boxes",
      "department": "Department if visible",
      "level": 0,
      "reports_to_id": null,
      "reports_to_name": null,
      "direct_report_names": [],
      "is_peer_with": []
    }
  ],
  "edges": [
    {
      "from_id": 1,
      "to_id": 2,
      "relationship": "manages"
    }
  ],
  "hierarchy_tree": {
    "Top Person Name": {
      "title": "Their exact title",
      "direct_reports": {
        "Person Name": {
          "title": "Their exact title",
          "direct_reports": {}
        }
      }
    }
  },
  "name_mappings": {
    "יובל לייקין": "Yuval Leikin",
    "hebrew_name": "english_transliteration"
  }
}

═══════════════════════════════════════════════════════════════════════
CRITICAL RULES — READ CAREFULLY:
═══════════════════════════════════════════════════════════════════════
1. TITLE ANCHOR: Read the EXACT title text INSIDE each person's box.
   Do NOT copy a title from an adjacent box. Verify visually.
   "VP Product & Support" must stay "VP Product & Support" — NOT mixed with nearby titles.
2. LINE-FOLLOWING: Only create "manages" edges where a SOLID LINE visually connects.
   No line = no relationship. Proximity alone is NOT evidence of reporting.
3. PEER DETECTION: Boxes branching from the same horizontal line are PEERS.
   They report to the box ABOVE the branch — not to each other.
4. Count direct reports by counting lines going DOWN from a box.
5. Include BOTH Hebrew AND English names when visible. Add transliterations to name_mappings.
6. Level 0 = top of chart, Level 1 = direct reports to top, etc.
7. Output ONLY valid JSON — no markdown, no explanation, no code blocks.
8. Be EXHAUSTIVE — every missing person or wrong title is a critical failure.
9. If a person has subordinates, list them ALL in "direct_report_names".
10. Fill "is_peer_with" with names of people who share the same branch line (same manager)."""
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # ── generate_content with cascading fallback ──
            # Try: Pro SDK → Flash SDK → Flash Direct HTTP (text-only, no file_ref)
            gen_config = {
                'temperature': 0.05,  # Near-zero for maximum accuracy
                'max_output_tokens': 8192
            }
            response = None
            try:
                response = model.generate_content(
                    [vision_prompt, file_ref],
                    generation_config=gen_config,
                    safety_settings=safety_settings
                )
            except Exception as gen_err:
                err_str = str(gen_err)
                print(f"   ⚠️ [Vision] Pro SDK failed: {err_str[:200]}")
                # Fallback 1: Flash via SDK (still supports file_ref)
                try:
                    fallback_name = MODEL_MAPPING["flash"]
                    print(f"   ⚠️ [Vision] Falling back to Flash SDK: {fallback_name}")
                    model = genai.GenerativeModel(fallback_name)
                    model_name = fallback_name
                    response = model.generate_content(
                        [vision_prompt, file_ref],
                        generation_config=gen_config,
                        safety_settings=safety_settings
                    )
                except Exception as flash_err:
                    print(f"   ⚠️ [Vision] Flash SDK also failed: {str(flash_err)[:200]}")
                    print(f"   ⚠️ [Vision] All SDK calls failed — falling back to text extraction")
                    return ""
            
            result_text = ""
            try:
                result_text = response.text.strip() if response.text else ""
            except (ValueError, AttributeError):
                if hasattr(response, 'candidates') and response.candidates:
                    parts = response.candidates[0].content.parts
                    result_text = "".join(p.text for p in parts if hasattr(p, 'text'))
            
            # Clean markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json", 1)[1]
                if "```" in result_text:
                    result_text = result_text.split("```", 1)[0]
            elif result_text.startswith("```"):
                result_text = result_text[3:]
                if "```" in result_text:
                    result_text = result_text.split("```", 1)[0]
            result_text = result_text.strip()
            
            # Validate and format JSON
            try:
                parsed = json.loads(result_text)
                formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
                
                # Cache the vision graph
                if file_id:
                    _vision_graph_cache[file_id] = {
                        'graph_json': formatted,
                        'parsed_data': parsed,
                        'timestamp': time.time()
                    }
                
                # Also rebuild the unified identity graph
                _rebuild_identity_graph(parsed)
                
                node_count = len(parsed.get('nodes', []))
                edge_count = len(parsed.get('edges', []))
                print(f"   ✅ [Vision] Graph parsed: {node_count} nodes, {edge_count} edges ({len(formatted)} chars)")
                return formatted
                
            except json.JSONDecodeError:
                if len(result_text) > 100:
                    # Not valid JSON but might still be useful
                    if file_id:
                        _vision_graph_cache[file_id] = {
                            'graph_json': result_text,
                            'parsed_data': {},
                            'timestamp': time.time()
                        }
                    print(f"   ⚠️ [Vision] Got text (not valid JSON): {len(result_text)} chars")
                    return result_text
                print(f"   ❌ [Vision] Response too short or invalid")
                return ""
        
        finally:
            # Cleanup
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            try:
                genai.delete_file(file_ref.name)
            except Exception:
                pass
    
    except Exception as e:
        print(f"   ❌ [Vision] Error: {e}")
        logger.error(f"[KB] Vision analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return ""


def _extract_image_with_vision(raw_bytes: bytes, file_id: str = "", file_name: str = "", mime_type: str = "image/jpeg") -> str:
    """
    Use Gemini Vision to analyze an image (screenshot, photo, chart, etc.)
    and extract ALL text and structured data from it.
    
    This enables: schedule screenshots, receipts, diagrams, handwritten notes,
    or any visual data sent via WhatsApp to be fully queryable.
    
    Results are cached for 24 hours by file_id.
    """
    # ── Check vision cache ──
    if file_id:
        cached = _get_cached_vision_graph(file_id)
        if cached:
            print(f"   📋 [Vision] Using cached image analysis for {file_name}")
            return f"── Vision-Analyzed Image: {file_name} ──\n{cached}"
    
    try:
        import google.generativeai as genai
        import tempfile
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print(f"   ⚠️ [Vision] No API key, skipping image analysis")
            return ""
        
        from app.services.model_discovery import configure_genai, MODEL_MAPPING
        configure_genai(api_key)
        
        # Determine file extension from mime type
        ext_map = {
            "image/jpeg": ".jpg", "image/png": ".png",
            "image/webp": ".webp", "image/gif": ".gif",
        }
        ext = ext_map.get(mime_type, ".jpg")
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name
        
        try:
            print(f"   👁️ [Vision] Uploading image for analysis: {file_name}")
            file_ref = genai.upload_file(
                path=tmp_path,
                display_name=file_name or f"image{ext}",
                mime_type=mime_type
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
                    print(f"   ❌ [Vision] Image processing failed")
                    return ""
                time.sleep(2)
            
            model_name = MODEL_MAPPING["pro"]
            print(f"   👁️ [Vision] Using MODEL_MAPPING['pro']: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            vision_prompt = f"""Analyze this image thoroughly and extract ALL information from it.

The image file name is: "{file_name}"

YOUR TASK:
1. Read and transcribe ALL text visible in the image — every single word, number, header, label, cell.
2. Preserve the structure: if it's a table/schedule, output it as a structured table. If it's a chart, describe every node. If it's a document, transcribe it fully.
3. Identify WHO this data belongs to — look for names in the title, headers, or content.
4. Identify WHAT TYPE of document this is (schedule, receipt, org chart, notes, etc.)
5. Output in HEBREW if the content is in Hebrew.

OUTPUT FORMAT:
- Document type: [type]
- Belongs to: [person name if identifiable]
- Content: [Full structured extraction of all data]

CRITICAL RULES:
- Extract EVERY cell, row, column if it's a table
- Do NOT summarize — give the COMPLETE data
- Include day names, times, subject names, teacher names — everything visible
- If there are colors or highlights, mention them
- Output clean structured text that can be searched and queried later"""

            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            gen_config = {
                'temperature': 0.1,
                'max_output_tokens': 8192
            }
            
            response = None
            try:
                response = model.generate_content(
                    [vision_prompt, file_ref],
                    generation_config=gen_config,
                    safety_settings=safety_settings
                )
            except Exception as pro_err:
                print(f"   ⚠️ [Vision] Pro failed for image: {pro_err}")
                # Fallback to Flash
                flash_model = genai.GenerativeModel(MODEL_MAPPING["flash"])
                print(f"   🔄 [Vision] Falling back to Flash: {MODEL_MAPPING['flash']}")
                try:
                    response = flash_model.generate_content(
                        [vision_prompt, file_ref],
                        generation_config=gen_config,
                        safety_settings=safety_settings
                    )
                except Exception as flash_err:
                    print(f"   ❌ [Vision] Flash also failed: {flash_err}")
            
            if response:
                # Extract text safely
                text = ""
                try:
                    text = response.text
                except (ValueError, AttributeError):
                    if response.candidates:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'text'):
                                text += part.text
                
                if text and text.strip():
                    result = text.strip()
                    print(f"   ✅ [Vision] Image analyzed: {len(result)} chars extracted from {file_name}")
                    
                    # Cache the result
                    if file_id:
                        _vision_cache[file_id] = {
                            'timestamp': time.time(),
                            'graph': result
                        }
                    
                    return f"── Vision-Analyzed Image: {file_name} ──\n{result}"
            
            print(f"   ⚠️ [Vision] No content extracted from image")
            return ""
        
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    except Exception as e:
        print(f"   ❌ [Vision] Image analysis error: {e}")
        logger.error(f"[KB] Image vision analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return ""


def _text_extract_pdf(raw_bytes: bytes) -> str:
    """Fallback text extraction from PDF (PyMuPDF → pdfplumber → PyPDF2)."""
    extracted = ""
    
    # Strategy 1: PyMuPDF
    try:
        import fitz
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        parts = []
        for page in doc:
            t = page.get_text("text")
            if t and t.strip():
                parts.append(t.strip())
        doc.close()
        if parts:
            extracted = "\n\n".join(parts)
    except (ImportError, Exception):
        pass
    
    # Strategy 2: pdfplumber
    if not extracted or len(extracted) < 50:
        try:
            import pdfplumber
            pdf = pdfplumber.open(io.BytesIO(raw_bytes))
            parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t.strip())
                for table in page.extract_tables():
                    if table:
                        parts.append("\n".join(" | ".join(str(c or "") for c in row) for row in table))
            pdf.close()
            if parts and len("\n".join(parts)) > len(extracted):
                extracted = "\n\n".join(parts)
        except (ImportError, Exception):
            pass
    
    # Strategy 3: PyPDF2
    if not extracted or len(extracted) < 50:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            parts = [p.extract_text() for p in reader.pages if p.extract_text()]
            if parts and len("\n".join(parts)) > len(extracted):
                extracted = "\n".join(parts)
        except (ImportError, Exception):
            pass
    
    return extracted


# ═══════════════════════════════════════════════════════════════════════
# UNIFIED IDENTITY GRAPH (Org + Family merged)
# ═══════════════════════════════════════════════════════════════════════

def _rebuild_identity_graph(org_data: Dict[str, Any] = None):
    """
    Build a unified identity graph that merges:
    - Org chart data (from vision analysis)
    - Family tree data (from family_tree.json)
    - Personal context files
    
    The graph enables cross-context identity resolution:
    - Same person can appear in both 'Work' and 'Family' contexts
    - Hebrew ↔ English name mappings
    - Nickname resolution
    """
    global _identity_graph, _identity_graph_timestamp
    
    graph = {
        "people": {},        # name -> {roles, contexts, aliases}
        "name_map": {},      # any_name_variant -> canonical_name
        "work_hierarchy": {},
        "family_tree": {},
    }
    
    # ── Merge org chart data ──
    if org_data:
        # Process nodes
        for node in org_data.get('nodes', []):
            name_en = (node.get('full_name_english') or node.get('full_name') or '').strip()
            name_he = (node.get('full_name_hebrew') or '').strip()
            title = node.get('title', '')
            dept = node.get('department', '')
            reports_to = node.get('reports_to_name', '')
            node_id = node.get('id')
            
            canonical = name_en or name_he
            if not canonical:
                continue
            
            person = graph["people"].setdefault(canonical, {
                "canonical_name": canonical,
                "aliases": set(),
                "contexts": [],
                "title": title,
                "department": dept,
                "reports_to": reports_to,
                "direct_reports": [],
                "node_id": node_id,
            })
            
            person["title"] = title or person.get("title", "")
            person["department"] = dept or person.get("department", "")
            person["reports_to"] = reports_to or person.get("reports_to", "")
            
            if "work" not in person["contexts"]:
                person["contexts"].append("work")
            
            # Build name mappings
            for variant in [name_en, name_he]:
                if variant:
                    graph["name_map"][variant.lower()] = canonical
                    person["aliases"].add(variant)
                    # Also add first name only
                    first = variant.split()[0] if ' ' in variant else variant
                    graph["name_map"][first.lower()] = canonical
        
        # Process name_mappings from vision
        for k, v in org_data.get('name_mappings', {}).items():
            graph["name_map"][k.lower()] = v
            graph["name_map"][v.lower()] = v
        
        # Process edges to build direct_reports
        for edge in org_data.get('edges', []):
            from_id = edge.get('from_id')
            to_id = edge.get('to_id')
            # Find names by node_id
            from_name = None
            to_name = None
            for node in org_data.get('nodes', []):
                if node.get('id') == from_id:
                    from_name = node.get('full_name_english') or node.get('full_name')
                if node.get('id') == to_id:
                    to_name = node.get('full_name_english') or node.get('full_name')
            
            if from_name and to_name and from_name in graph["people"]:
                if to_name not in graph["people"][from_name].get("direct_reports", []):
                    graph["people"][from_name].setdefault("direct_reports", []).append(to_name)
        
        graph["work_hierarchy"] = org_data.get('hierarchy_tree', {})
    
    # Convert sets to lists for JSON serialization
    for person in graph["people"].values():
        if isinstance(person.get("aliases"), set):
            person["aliases"] = list(person["aliases"])
    
    _identity_graph = graph
    _identity_graph_timestamp = time.time()
    
    people_count = len(graph["people"])
    alias_count = len(graph["name_map"])
    print(f"   🔗 [Identity Graph] Built: {people_count} people, {alias_count} name mappings")


def get_identity_graph() -> Optional[Dict[str, Any]]:
    """Get the unified identity graph for use in queries."""
    return _identity_graph


# ═══════════════════════════════════════════════════════════════════════
# FILE CONTENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def _extract_json_text(raw_bytes: bytes, file_name: str = "") -> str:
    """Extract readable text from JSON bytes and integrate into identity graph."""
    try:
        data = json.loads(raw_bytes.decode('utf-8'))
        
        # If this looks like a family tree or identity context, merge into identity graph
        if isinstance(data, dict):
            _merge_json_into_identity_graph(data, source_file_name=file_name)
        elif isinstance(data, list):
            _merge_json_into_identity_graph({"people": data}, source_file_name=file_name)
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[JSON parse failed: {e}]"


def _merge_json_into_identity_graph(data: Dict[str, Any], source_file_name: str = ""):
    """
    Merge JSON data (org_structure.json, family_tree.json, identity_context.json)
    into the unified identity graph.
    
    Also caches the raw structured data for financial/hierarchy queries.
    """
    global _identity_graph, _org_structure_data, _family_tree_data
    
    if _identity_graph is None:
        _identity_graph = {
            "people": {},
            "name_map": {},
            "work_hierarchy": {},
            "family_tree": {},
        }
    
    # ── Cache raw structured data by source type ──
    source_lower = source_file_name.lower() if source_file_name else ""
    if 'org_structure' in source_lower or 'org_chart' in source_lower or 'employees' in source_lower:
        _org_structure_data = data
        print(f"   💾 [Identity] Cached org_structure data from {source_file_name}")
    elif 'family' in source_lower:
        _family_tree_data = data
        print(f"   💾 [Identity] Cached family_tree data from {source_file_name}")
    
    # Look for people/members/family arrays
    people_arrays = []
    for key in ['people', 'members', 'family', 'employees', 'team', 'contacts', 'persons']:
        if key in data and isinstance(data[key], list):
            people_arrays.extend(data[key])
    
    # Also check if data itself is a list
    if isinstance(data, list):
        people_arrays = data
    
    # Check for nested family tree structure
    if 'family_tree' in data:
        _identity_graph["family_tree"] = data['family_tree']
    
    for person_data in people_arrays:
        if not isinstance(person_data, dict):
            continue
        
        name = (person_data.get('name') or person_data.get('full_name') or 
                person_data.get('שם') or '').strip()
        if not name:
            continue
        
        person = _identity_graph["people"].setdefault(name, {
            "canonical_name": name,
            "aliases": [],
            "contexts": [],
            "title": "",
            "department": "",
            "reports_to": "",
            "direct_reports": [],
        })
        
        # Merge fields
        for field in ['title', 'role', 'תפקיד']:
            if person_data.get(field):
                person["title"] = person_data[field]
        
        for field in ['department', 'מחלקה']:
            if person_data.get(field):
                person["department"] = person_data[field]
        
        for field in ['reports_to', 'manager', 'מדווח_ל']:
            if person_data.get(field):
                person["reports_to"] = person_data[field]
        
        # ── Financial fields (salary, rating, individual_factor, etc.) ──
        for fin_field in ['salary', 'base_salary', 'total_comp', 'compensation',
                          'rating', 'performance_rating', 'review',
                          'individual_factor', 'bonus', 'equity',
                          'start_date', 'hire_date', 'location', 'level']:
            if person_data.get(fin_field) is not None:
                person[fin_field] = person_data[fin_field]
        
        # Context — distinguish work vs family
        context = person_data.get('context', '')
        if not context:
            # Auto-detect context based on source file
            if 'family' in source_lower:
                context = 'family'
            elif any(k in source_lower for k in ['org', 'employee', 'structure']):
                context = 'work'
            else:
                context = 'unknown'
        
        if context not in person.get("contexts", []):
            person.setdefault("contexts", []).append(context)
        
        # Name mappings
        _identity_graph["name_map"][name.lower()] = name
        for alias_field in ['aliases', 'nicknames', 'כינויים', 'english_name', 'hebrew_name']:
            aliases = person_data.get(alias_field, [])
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                if alias:
                    _identity_graph["name_map"][alias.lower()] = name
                    if alias not in person.get("aliases", []):
                        person.setdefault("aliases", []).append(alias)
        
        # First name mapping
        first = name.split()[0] if ' ' in name else name
        _identity_graph["name_map"][first.lower()] = name
    
    print(f"   🔗 [Identity Graph] Merged JSON data ({len(people_arrays)} people entries from {source_file_name or 'unknown'})")


# ═══════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK
# ═══════════════════════════════════════════════════════════════════════

def _load_from_local_fallback() -> str:
    """Fallback: Load from local app/knowledge_base/ folder."""
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
                text = _extract_json_text(filepath.read_bytes(), file_name=filepath.name)
            elif filepath.suffix.lower() == '.pdf':
                text = _extract_pdf_with_vision(filepath.read_bytes(), file_name=filepath.name)
            else:
                continue
            
            if text and text.strip():
                sections.append(f"── {filepath.name} ──\n{text.strip()}")
        except Exception as e:
            logger.warning(f"[KB] Could not read local file {filepath.name}: {e}")
    
    return "\n\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════
# MAIN CONTEXT LOADER
# ═══════════════════════════════════════════════════════════════════════

def load_context(force_reload: bool = False) -> str:
    """
    Load all files from Second_Brain_Context and build unified context.
    
    Order of operations:
    1. List all files in Drive folder
    2. Download each file:
       - PDFs → Vision analysis (Gemini Pro) + text fallback
       - JSONs → Parse + merge into identity graph
       - TXT/MD → Raw text
    3. Build unified identity graph
    4. Cache everything
    """
    global _cached_context, _cached_file_list, _cached_file_count
    global _cache_timestamp, _drive_connected
    
    with _cache_lock:
        now = time.time()
        cache_age = now - _cache_timestamp
        
        if not force_reload and _cached_context is not None and cache_age < CACHE_TTL_SECONDS:
            return _cached_context
        
        folder_id = _get_context_folder_id()
        
        if folder_id:
            service = _get_drive_service()
            
            if service:
                try:
                    files = _list_drive_files(service, folder_id)
                    
                    if not force_reload and _cached_context is not None and len(files) == _cached_file_count:
                        if cache_age < CACHE_TTL_SECONDS:
                            return _cached_context
                    
                    if not files:
                        print(f"📚 [KB] Drive folder is empty (ID: {folder_id[:20]}...)")
                        _cached_context = ""
                        _cached_file_list = []
                        _cached_file_count = 0
                        _cache_timestamp = now
                        _drive_connected = True
                        return ""
                    
                    sections = []
                    loaded_names = []
                    
                    for f in files:
                        file_name = f.get('name', 'Unknown')
                        fid = f.get('id')
                        mime_type = f.get('mimeType', '')
                        
                        if mime_type == 'application/vnd.google-apps.folder':
                            continue
                        
                        print(f"   📥 Processing: {file_name} ({mime_type})")
                        text = _download_file_content(service, fid, file_name, mime_type)
                        
                        if text and text.strip():
                            sections.append(f"══ {file_name} ══\n{text.strip()}")
                            loaded_names.append(file_name)
                            print(f"   ✅ Loaded: {file_name} ({len(text)} chars)")
                        else:
                            print(f"   ⚠️ Empty content from: {file_name}")
                    
                    # ── Append Identity Graph summary ──
                    if _identity_graph and _identity_graph.get("people"):
                        graph_summary = _format_identity_graph_for_context()
                        if graph_summary:
                            sections.append(f"══ UNIFIED IDENTITY GRAPH (auto-generated) ══\n{graph_summary}")
                    
                    # ── Combine and cache ──
                    if sections:
                        combined = "\n\n".join(sections)
                        if len(combined) > MAX_CONTEXT_CHARS:
                            combined = _smart_truncate(sections, MAX_CONTEXT_CHARS)
                        _cached_context = combined
                    else:
                        _cached_context = ""
                    
                    _cached_file_list = loaded_names
                    _cached_file_count = len(files)
                    _cache_timestamp = now
                    _drive_connected = True
                    
                    print(f"📚 [KB] Loaded {len(loaded_names)} file(s): {loaded_names} ({len(_cached_context)} chars)")
                    return _cached_context
                    
                except Exception as e:
                    logger.error(f"[KB] Drive load failed: {e}")
                    print(f"⚠️ [KB] Drive load failed: {e}")
                    import traceback
                    traceback.print_exc()
                    _drive_connected = False
        
        # Fallback
        print(f"📚 [KB] Using local fallback")
        _drive_connected = False
        local = _load_from_local_fallback()
        _cached_context = local
        _cached_file_list = []
        _cached_file_count = 0
        _cache_timestamp = now
        
        if local:
            print(f"📚 [KB] Loaded from local ({len(local)} chars)")
        else:
            print(f"📚 [KB] No context files found")
        
        return _cached_context


def _format_identity_graph_for_context() -> str:
    """Format the identity graph as human-readable text for Gemini context."""
    if not _identity_graph:
        return ""
    
    lines = []
    lines.append("This is a unified identity graph merging all organizational and personal data.")
    lines.append("Use this for semantic name resolution, hierarchy navigation, and financial queries.\n")
    
    # Name mappings (critical for Hebrew ↔ English resolution)
    name_map = _identity_graph.get("name_map", {})
    if name_map:
        lines.append("── Name Mappings (Hebrew ↔ English, Nicknames) ──")
        # Deduplicate: group by canonical name
        canonical_to_aliases = {}
        for alias, canonical in name_map.items():
            canonical_to_aliases.setdefault(canonical, set()).add(alias)
        for canonical, aliases in sorted(canonical_to_aliases.items()):
            other = [a for a in aliases if a.lower() != canonical.lower()]
            if other:
                lines.append(f"  {canonical} ← {', '.join(sorted(other))}")
        lines.append("")
    
    # People with roles, reporting, and financial data
    people = _identity_graph.get("people", {})
    if people:
        lines.append("── People Directory (roles, hierarchy, financial data) ──")
        for name, info in sorted(people.items()):
            title = info.get('title', '')
            dept = info.get('department', '')
            reports_to = info.get('reports_to', '')
            direct_reports = info.get('direct_reports', [])
            contexts = info.get('contexts', [])
            
            parts = [f"  • {name}"]
            if title:
                parts.append(f"({title})")
            if dept:
                parts.append(f"[{dept}]")
            if contexts:
                parts.append(f"context: {', '.join(contexts)}")
            
            line = " ".join(parts)
            if reports_to:
                line += f"\n      ↑ reports to: {reports_to}"
            if direct_reports:
                line += f"\n      ↓ manages: {', '.join(direct_reports)}"
            
            # Financial fields
            fin_parts = []
            for fk, label in [('salary', 'Salary'), ('base_salary', 'Base Salary'),
                              ('total_comp', 'Total Comp'), ('compensation', 'Compensation'),
                              ('rating', 'Rating'), ('performance_rating', 'Performance'),
                              ('individual_factor', 'Individual Factor'),
                              ('bonus', 'Bonus'), ('level', 'Level'),
                              ('location', 'Location'), ('start_date', 'Start Date')]:
                if info.get(fk) is not None:
                    fin_parts.append(f"{label}: {info[fk]}")
            if fin_parts:
                line += f"\n      💰 {' | '.join(fin_parts)}"
            
            lines.append(line)
    
    # ── Hierarchy tree for recursive queries ──
    if people:
        lines.append("\n── Hierarchy Tree (reports_to chains) ──")
        # Build a flat manager→reports mapping
        manager_map: Dict[str, List[str]] = {}
        for name, info in people.items():
            mgr = info.get('reports_to', '')
            if mgr:
                manager_map.setdefault(mgr, []).append(name)
        
        # Find top-level (people who don't report to anyone, or whose manager isn't in people)
        top_level = [n for n, info in people.items() if not info.get('reports_to')]
        
        def _print_tree(person_name: str, indent: int = 0):
            prefix = "  " * indent + ("└─ " if indent > 0 else "")
            info = people.get(person_name, {})
            title = info.get('title', '')
            title_str = f" ({title})" if title else ""
            lines.append(f"{prefix}{person_name}{title_str}")
            for sub in sorted(manager_map.get(person_name, [])):
                _print_tree(sub, indent + 1)
        
        for top in sorted(top_level):
            _print_tree(top)
    
    return "\n".join(lines)


def get_all_reports_under(person_name: str) -> List[str]:
    """
    Recursive graph search: get ALL direct + indirect reports under a person.
    Uses the reports_to field in the identity graph.
    """
    if not _identity_graph:
        return []
    
    people = _identity_graph.get("people", {})
    
    # Build manager→reports mapping
    manager_map: Dict[str, List[str]] = {}
    for name, info in people.items():
        mgr = info.get('reports_to', '')
        if mgr:
            manager_map.setdefault(mgr, []).append(name)
    
    # Recursive collect
    result = []
    
    def _collect(mgr_name):
        for sub in manager_map.get(mgr_name, []):
            result.append(sub)
            _collect(sub)
    
    _collect(person_name)
    return result


def get_identity_context_summary() -> str:
    """
    Returns a startup verification summary of the loaded identity context.
    Called after load_context() to print verification log.
    """
    people_count = len(_identity_graph.get("people", {})) if _identity_graph else 0
    family_count = 0
    work_count = 0
    
    if _identity_graph:
        for info in _identity_graph.get("people", {}).values():
            contexts = info.get("contexts", [])
            if "family" in contexts:
                family_count += 1
            if "work" in contexts:
                work_count += 1
    
    has_org = _org_structure_data is not None
    has_family = _family_tree_data is not None
    
    parts = []
    if has_org:
        parts.append("org_structure.json ✅")
    if has_family:
        parts.append("family_tree.json ✅")
    
    sources = ", ".join(parts) if parts else "none loaded"
    
    return (
        f"SUCCESS: Identity Context active. API set to v1. "
        f"{people_count} identities loaded ({work_count} employees, {family_count} family). "
        f"Sources: {sources}."
    )


def _smart_truncate(sections: List[str], max_chars: int) -> str:
    """Prioritize JSON/org files, then images/vision, truncate others."""
    priority_high = []
    priority_medium = []
    priority_low = []
    
    for section in sections:
        header = section.split('\n')[0].lower()
        if any(kw in header for kw in ['.json', 'identity', 'org', 'graph', 'unified']):
            priority_high.append(section)
        elif any(kw in header for kw in ['.txt', '.md', 'context', 'family',
                                          'image', 'vision', 'מערכת', 'schedule',
                                          '.jpg', '.png', '.webp', '.gif']):
            priority_medium.append(section)
        else:
            priority_low.append(section)
    
    result = []
    remaining = max_chars
    
    for section in priority_high + priority_medium + priority_low:
        if remaining <= 500:
            break
        chunk = section[:remaining]
        result.append(chunk)
        remaining -= len(chunk)
    
    return "\n\n".join(result)


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def get_system_instruction_block() -> str:
    """Returns formatted KB block for Gemini system instructions."""
    context = load_context()
    if not context:
        return ""
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
ORGANIZATIONAL SOURCE OF TRUTH — Knowledge Base (Live from Google Drive)
═══════════════════════════════════════════════════════════════════════════════

**CRITICAL INSTRUCTION:**
The following documents are the user's AUTHORITATIVE Knowledge Base.
Treat ALL data below as the SINGLE SOURCE OF TRUTH for:
  • Organizational structure (who reports to whom)
  • Roles, titles, and departments
  • Team composition and hierarchy
  • Family relationships and personal context

**MANDATORY: DUAL-SOURCE SEARCH:**
For EVERY query about a person, role, or relationship, you MUST search
BOTH of these sources SIMULTANEOUSLY — never just one:
  1. The Org Chart data (parsed from "org chart 1.pdf") — contains
     work hierarchy, titles, departments, and reporting lines.
  2. The Family Tree data (from "family_tree.json") — contains
     family relationships, personal roles, and informal context.
Cross-reference BOTH sources before answering. A person may appear
in one or both. Combine all findings into a single unified answer.

**MANDATORY STEP 1 — HEBREW NAME RESOLUTION (must happen BEFORE answering):**
If any name in the query is in Hebrew or is a partial/nickname:
1. FIRST resolve it to the full English name found in the data files.
2. Use the "Name Mappings" and "aliases" sections.
3. Phonetic matching: "יובל" → "Yuval Laikin", "שי" → "Shey Heven", etc.
4. Only AFTER resolving the name, proceed to search the graph.
5. NEVER answer about a Hebrew name without first mapping it to the file data.

**HIERARCHY NAVIGATION:**
When asked about reporting lines:
1. Find the person in the graph (using resolved English name from Step 1)
2. Recursively traverse their sub-tree for all direct/indirect reports
3. Use the "edges", "direct_reports", and "hierarchy_tree" fields
4. Include BOTH direct and indirect reports in the answer

**CROSS-CONTEXT RESOLUTION:**
A person may appear in BOTH work (org chart) and family (family_tree.json)
contexts. Use ALL available data to give a complete answer about their identity.

**PRIORITY:** Knowledge Base data OVERRIDES any assumptions or general knowledge.

{context}
═══════════════════════════════════════════════════════════════════════════════
"""


def get_kb_query_context() -> str:
    """Returns raw KB content for direct organizational queries."""
    return load_context() or ""


def force_refresh_pdf_cache(file_id: str = None):
    """Force refresh vision-parsed PDF cache."""
    global _vision_graph_cache
    if file_id:
        _vision_graph_cache.pop(file_id, None)
    else:
        _vision_graph_cache.clear()
    print(f"🔄 [KB] Vision cache cleared")


def get_status() -> Dict[str, Any]:
    """Return KB status for health checks."""
    load_context()
    folder_id = _get_context_folder_id()
    cache_age = time.time() - _cache_timestamp if _cache_timestamp > 0 else -1
    
    identity_count = len(_identity_graph.get("people", {})) if _identity_graph else 0
    
    # Count work vs family contexts
    work_count = 0
    family_count = 0
    if _identity_graph:
        for info in _identity_graph.get("people", {}).values():
            ctxs = info.get("contexts", [])
            if "work" in ctxs:
                work_count += 1
            if "family" in ctxs:
                family_count += 1
    
    return {
        "connected": _drive_connected or bool(_cached_context),
        "source": "Google Drive" if _drive_connected else ("Local" if _cached_context else "None"),
        "folder_id": folder_id[:20] + "..." if folder_id and len(folder_id) > 20 else folder_id,
        "file_count": len(_cached_file_list),
        "files": list(_cached_file_list),
        "chars": len(_cached_context) if _cached_context else 0,
        "cache_age_minutes": round(cache_age / 60, 1) if cache_age >= 0 else -1,
        "vision_cache_count": len(_vision_graph_cache),
        "identity_graph_people": identity_count,
        "identity_work_count": work_count,
        "identity_family_count": family_count,
        "org_structure_loaded": _org_structure_data is not None,
        "family_tree_loaded": _family_tree_data is not None,
        "identity_summary": get_identity_context_summary(),
    }


def get_loaded_files() -> List[str]:
    """Return list of loaded file names."""
    load_context()
    return list(_cached_file_list)


def search_people(query: str) -> List[Dict[str, Any]]:
    """
    Search the identity graph for people matching a name query.
    
    Supports:
    - Exact canonical match
    - name_map lookup (Hebrew, nicknames, first-name)
    - Fuzzy substring match across all aliases
    
    Returns a list of person dicts, each with:
      canonical_name, title, department, reports_to, direct_reports, contexts, aliases, etc.
    """
    load_context()  # Ensure data is loaded
    
    if not _identity_graph:
        return []
    
    query_lower = query.strip().lower()
    if not query_lower:
        return []
    
    people = _identity_graph.get("people", {})
    name_map = _identity_graph.get("name_map", {})
    
    matches: List[Dict[str, Any]] = []
    seen_canonical: set = set()
    
    # ── Strategy 1: Exact name_map hit (resolves Hebrew/nickname → canonical) ──
    if query_lower in name_map:
        canonical = name_map[query_lower]
        if canonical in people:
            person = dict(people[canonical])
            # Convert set → list for JSON serialization
            if isinstance(person.get("aliases"), set):
                person["aliases"] = list(person["aliases"])
            matches.append(person)
            seen_canonical.add(canonical)
    
    # ── Strategy 2: Substring match on all name variants ──
    # Finds cases like "שי" matching "שיי הובן" and "שי אמיר" etc.
    for variant, canonical in name_map.items():
        if canonical in seen_canonical:
            continue
        # Substring match in either direction
        if query_lower in variant or variant in query_lower:
            if canonical in people:
                person = dict(people[canonical])
                if isinstance(person.get("aliases"), set):
                    person["aliases"] = list(person["aliases"])
                matches.append(person)
                seen_canonical.add(canonical)
    
    # ── Strategy 3: Substring match on canonical names ──
    for canonical, info in people.items():
        if canonical in seen_canonical:
            continue
        if query_lower in canonical.lower():
            person = dict(info)
            if isinstance(person.get("aliases"), set):
                person["aliases"] = list(person["aliases"])
            matches.append(person)
            seen_canonical.add(canonical)
    
    return matches
