"""
Knowledge Base Service — Dynamic Personal Context Loader

Scans app/knowledge_base/ for .txt, .json, and .pdf files,
extracts text content, and caches it in memory for injection
into Gemini system instructions.

Supported file types:
  .txt  — read as-is (UTF-8)
  .json — pretty-printed key/value extraction
  .pdf  — text extraction via reportlab or fallback to binary skip

Cache is loaded ONCE on startup (or first access) and stays in memory.
Replacing files in the folder takes effect on next restart/deployment.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Path to the knowledge_base folder ──
# Works both locally and in deployed environments
_KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ── In-memory cache ──
_cached_context: Optional[str] = None
_cached_file_list: list = []


def _extract_text_from_txt(filepath: Path) -> str:
    """Read a plain text file."""
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return filepath.read_text(encoding="latin-1")
        except Exception as e:
            logger.warning(f"[KB] Could not read {filepath.name}: {e}")
            return ""


def _extract_text_from_json(filepath: Path) -> str:
    """Extract readable text from a JSON file."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[KB] Could not parse JSON {filepath.name}: {e}")
        return ""


def _extract_text_from_pdf(filepath: Path) -> str:
    """
    Extract text from a PDF file.
    Uses PyPDF2 if available, otherwise skips with a warning.
    """
    try:
        import PyPDF2
        text_parts = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        logger.info(f"[KB] PyPDF2 not installed — skipping PDF: {filepath.name}")
        return f"[PDF file: {filepath.name} — install PyPDF2 to extract text]"
    except Exception as e:
        logger.warning(f"[KB] Could not extract PDF {filepath.name}: {e}")
        return f"[PDF file: {filepath.name} — extraction failed: {e}]"


# ── File type handlers ──
_EXTRACTORS = {
    ".txt": _extract_text_from_txt,
    ".text": _extract_text_from_txt,
    ".md": _extract_text_from_txt,
    ".json": _extract_text_from_json,
    ".pdf": _extract_text_from_pdf,
}


def load_context(force_reload: bool = False) -> str:
    """
    Scan all files in app/knowledge_base/ and return their combined text.
    
    Results are cached in memory. Call with force_reload=True to re-read.
    On deployment/restart, the cache is naturally cleared (new process).
    
    Returns:
        Combined text from all knowledge base files, formatted for
        injection into Gemini system instructions.
    """
    global _cached_context, _cached_file_list
    
    if _cached_context is not None and not force_reload:
        return _cached_context
    
    if not _KB_DIR.exists():
        logger.info(f"[KB] Knowledge base directory not found: {_KB_DIR}")
        _cached_context = ""
        _cached_file_list = []
        return ""
    
    # Scan for supported files
    files = sorted([
        f for f in _KB_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in _EXTRACTORS and f.name != ".gitkeep"
    ])
    
    if not files:
        logger.info("[KB] No knowledge base files found")
        _cached_context = ""
        _cached_file_list = []
        return ""
    
    # Extract text from each file
    sections = []
    loaded_names = []
    
    for filepath in files:
        extractor = _EXTRACTORS.get(filepath.suffix.lower())
        if not extractor:
            continue
        
        text = extractor(filepath)
        if not text or not text.strip():
            continue
        
        # Add section header
        sections.append(f"── {filepath.name} ──\n{text.strip()}")
        loaded_names.append(filepath.name)
    
    if sections:
        combined = "\n\n".join(sections)
        # Truncate if too large (keep under 4000 chars to leave room for prompts)
        if len(combined) > 4000:
            combined = combined[:4000] + "\n\n[...truncated — knowledge base too large]"
        _cached_context = combined
    else:
        _cached_context = ""
    
    _cached_file_list = loaded_names
    
    file_count = len(loaded_names)
    char_count = len(_cached_context)
    print(f"📚 [Knowledge Base] Loaded {file_count} file(s): {loaded_names} ({char_count} chars)")
    logger.info(f"[KB] Loaded {file_count} file(s): {loaded_names} ({char_count} chars)")
    
    return _cached_context


def get_system_instruction_block() -> str:
    """
    Returns a formatted block ready to inject into Gemini system instructions.
    
    If the knowledge base is empty, returns an empty string (no injection).
    """
    context = load_context()
    
    if not context:
        return ""
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
USER'S PERSONAL KNOWLEDGE BASE
═══════════════════════════════════════════════════════════════════════════════
You have access to the user's personal knowledge base below.
Reference the roles, relationships, and identities found in these documents
to provide 100% accurate analysis. Use this information to:
- Correctly identify speakers by their roles and relationships
- Understand organizational hierarchy and family structure
- Provide contextually relevant insights based on known dynamics

{context}
═══════════════════════════════════════════════════════════════════════════════
"""


def get_loaded_files() -> list:
    """Return list of loaded file names (for debugging/status)."""
    load_context()  # Ensure loaded
    return list(_cached_file_list)


# ── Auto-load on import (runs once on startup/deployment) ──
try:
    load_context()
except Exception as e:
    logger.error(f"[KB] Failed to load knowledge base on startup: {e}")
    print(f"⚠️ [Knowledge Base] Failed to load on startup: {e}")
