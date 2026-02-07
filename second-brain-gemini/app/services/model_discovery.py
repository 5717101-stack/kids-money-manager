"""
Model Discovery Service — Dynamic Gemini Model Selection

╔══════════════════════════════════════════════════════════════════╗
║  SINGLE SOURCE OF TRUTH FOR ALL MODEL NAMES                     ║
║                                                                  ║
║  To change models, ONLY edit MODEL_MAPPING below                ║
║  (or set GEMINI_PRO_MODEL / GEMINI_FLASH_MODEL in .env)         ║
║                                                                  ║
║  NO other file should contain hardcoded model name strings!      ║
╚══════════════════════════════════════════════════════════════════╝

This module provides:
1. MODEL_MAPPING — central dict: {"pro": "...", "flash": "..."}
2. resolve_model(alias) — converts "pro"/"flash" to actual model string
3. configure_genai() — sets up SDK transport
4. discover_models() — lists available models from the API
5. get_best_model() — finds best match from discovered models
6. gemini_v1_generate() — direct HTTP calls bypassing SDK
7. startup_connection_test() — verifies API connectivity at boot

Usage (in ANY service):
    from app.services.model_discovery import MODEL_MAPPING, resolve_model
    
    model = genai.GenerativeModel(MODEL_MAPPING["pro"])
    # or
    model_name = resolve_model("flash")
"""

import json
import logging
import os
import time
from typing import List, Optional, Dict, Any, Tuple
from threading import Lock

import google.generativeai as genai

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# SINGLE SOURCE OF TRUTH — Model names
# ═══════════════════════════════════════════════════════════════════════
# Defaults here. Override via env vars without touching code:
#   GEMINI_PRO_MODEL=gemini-2.5-pro-preview-06-05
#   GEMINI_FLASH_MODEL=gemini-2.0-flash
#
# NOTE: No "models/" prefix — the SDK adds it automatically.
_DEFAULT_PRO = "gemini-2.5-pro"
_DEFAULT_FLASH = "gemini-2.0-flash"

MODEL_MAPPING = {
    "pro":   os.environ.get("GEMINI_PRO_MODEL",   _DEFAULT_PRO),
    "flash": os.environ.get("GEMINI_FLASH_MODEL", _DEFAULT_FLASH),
}

# Log on import so it's visible in every startup
print(f"🤖 [Model Mapping] pro  = {MODEL_MAPPING['pro']}"
      f"{' (env override)' if os.environ.get('GEMINI_PRO_MODEL') else ''}")
print(f"🤖 [Model Mapping] flash = {MODEL_MAPPING['flash']}"
      f"{' (env override)' if os.environ.get('GEMINI_FLASH_MODEL') else ''}")


def resolve_model(alias: str) -> str:
    """Resolve a model alias ('pro', 'flash') to the exact API model string.
    
    Returns the alias itself if not found in MODEL_MAPPING (pass-through).
    """
    return MODEL_MAPPING.get(alias, alias)


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL API CONFIGURATION — Force stable REST transport (no v1beta)
# ═══════════════════════════════════════════════════════════════════════
_configured = False


def configure_genai(api_key: str = None):
    """
    Configure the Google Generative AI client with stable v1 REST transport.
    
    Uses transport='rest' to avoid gRPC issues, and explicitly sets the
    client_options api_endpoint to the stable v1 endpoint to prevent
    the SDK from defaulting to v1beta (which causes 404 errors).
    
    Safe to call multiple times — only configures once.
    """
    global _configured
    if _configured:
        return
    
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
    
    if not api_key:
        print("⚠️ [Model Discovery] No API key for configure_genai()")
        return
    
    genai.configure(
        api_key=api_key,
        transport="rest",
        client_options={"api_endpoint": "generativelanguage.googleapis.com"},
    )
    _configured = True
    print("✅ [Model Discovery] genai configured: transport=rest, endpoint=generativelanguage.googleapis.com (stable v1, no v1beta)")


# ── Cache (populated once on first call) ──
_discovery_lock = Lock()
_available_models: Optional[List[str]] = None
_model_details: Optional[List[Dict[str, Any]]] = None

# ── Dynamic PRIMARY_KB_MODEL (set by health check, read by KB/Gemini services) ──
PRIMARY_KB_MODEL: Optional[str] = None


def discover_models(force: bool = False) -> List[str]:
    """
    Discover all available models from the Gemini API.
    Results are cached for the lifetime of the process.
    
    Returns:
        List of model name strings (e.g. ["models/gemini-1.5-pro-002", ...])
    """
    global _available_models, _model_details
    
    with _discovery_lock:
        if _available_models is not None and not force:
            return _available_models
        
        try:
            print("\n🔍 ══════════════════════════════════════════════")
            print("🔍  GEMINI MODEL DISCOVERY (genai.list_models)")
            print("🔍 ══════════════════════════════════════════════")
            
            raw_models = list(genai.list_models())
            
            all_names = []
            details = []
            
            # Filter to models that support generateContent
            for m in raw_models:
                name = m.name if hasattr(m, 'name') else str(m)
                supported = []
                if hasattr(m, 'supported_generation_methods'):
                    supported = list(m.supported_generation_methods)
                
                if 'generateContent' in supported:
                    all_names.append(name)
                    detail = {
                        "name": name,
                        "display_name": getattr(m, 'display_name', ''),
                        "methods": supported,
                    }
                    details.append(detail)
            
            # Sort for readability
            all_names.sort()
            
            # Log everything
            print(f"🔍  Found {len(all_names)} models with generateContent support:")
            for n in all_names:
                # Mark Pro vs Flash for easy scanning
                tag = "🟢 PRO" if "pro" in n.lower() else ("⚡ FLASH" if "flash" in n.lower() else "  ")
                print(f"   {tag}  {n}")
            
            if not all_names:
                print("   ❌ NO models found! Check API key permissions.")
                # Also log all raw models for debugging
                print(f"   📋 Raw models returned: {len(raw_models)}")
                for m in raw_models[:20]:
                    name = m.name if hasattr(m, 'name') else str(m)
                    methods = list(m.supported_generation_methods) if hasattr(m, 'supported_generation_methods') else []
                    print(f"      {name} → {methods}")
            
            print("🔍 ══════════════════════════════════════════════\n")
            
            _available_models = all_names
            _model_details = details
            return _available_models
            
        except Exception as e:
            print(f"❌ [Model Discovery] Failed to list models: {e}")
            logger.error(f"[Model Discovery] genai.list_models() failed: {e}")
            import traceback
            traceback.print_exc()
            _available_models = []
            _model_details = []
            return []


def startup_connection_test():
    """
    Perform a direct HTTP call at startup to verify connectivity.
    Tests both Pro and Flash models via the v1 endpoint.
    
    Call this AFTER configure_genai() and discover_models().
    """
    print("\n🧪 ══════════════════════════════════════════════")
    print("🧪  CONNECTION TEST (direct HTTP v1beta endpoint)")
    print("🧪 ══════════════════════════════════════════════")
    
    for alias, model_name in MODEL_MAPPING.items():
        url = f"{GEMINI_API_BASE_URL}/{model_name}:generateContent?key={_get_api_key()}"
        print(f"   🔗 CONNECTION TEST: {alias.upper()} model [{model_name}] on {GEMINI_API_BASE_URL}")
        try:
            start = time.time()
            result = gemini_v1_generate("Say 'OK' in one word.", model_name=model_name, max_output_tokens=10)
            elapsed_ms = int((time.time() - start) * 1000)
            reply = result[:30] if result else "(empty)"
            print(f"   ✅ CONNECTION TEST: {alias.upper()} model [{model_name}] → {elapsed_ms}ms — reply: \"{reply}\"")
        except Exception as e:
            err_str = str(e)[:150]
            print(f"   ❌ CONNECTION TEST: {alias.upper()} model [{model_name}] → FAILED: {err_str}")
    
    print("🧪 ══════════════════════════════════════════════\n")


# ═══════════════════════════════════════════════════════════════════════
# DIRECT HTTP API — v1beta endpoint (has ALL model names incl. aliases)
# ═══════════════════════════════════════════════════════════════════════
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_api_key() -> str:
    """Get the API key from environment."""
    return os.environ.get("GOOGLE_API_KEY", "")


def gemini_v1_generate(
    prompt: str,
    model_name: str = None,
    temperature: float = 0.1,
    max_output_tokens: int = 1500,
    is_kb_query: bool = False,
    timeout: int = 90,
) -> str:
    """
    Direct HTTP POST to Gemini API — completely bypasses the SDK.
    
    URL: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...
    Uses v1beta which supports ALL model names (incl. aliases like gemini-2.5-pro).
    
    Args:
        prompt: The text prompt to send
        model_name: Model name (e.g. "gemini-2.5-pro"). If None, auto-selects based on is_kb_query.
        temperature: Sampling temperature (0.0-1.0)
        max_output_tokens: Maximum response length
        is_kb_query: If True, uses Pro model; otherwise Flash
        timeout: Request timeout in seconds
    
    Returns:
        The generated text response
        
    Raises:
        Exception with full error details if the request fails
    """
    import requests as http_requests
    
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    
    # ── Manual model selection ──
    if model_name is None:
        model_name = MODEL_MAPPING["pro"] if is_kb_query else MODEL_MAPPING["flash"]
    
    url = f"{GEMINI_API_BASE_URL}/{model_name}:generateContent?key={api_key}"
    
    # ── Payload (Gemini v1 format) ──
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"🌐 [Direct HTTP] POST {GEMINI_API_BASE_URL}/{model_name}:generateContent")
    
    resp = http_requests.post(url, json=payload, headers=headers, timeout=timeout)
    
    # ── Strict error handling: print FULL response on failure ──
    if resp.status_code != 200:
        body = resp.text[:2000]
        print(f"❌ [Direct HTTP] Status {resp.status_code} from {model_name}:")
        print(f"❌ [Direct HTTP] FULL RESPONSE BODY:\n{body}")
        
        # If Pro failed, try Flash automatically
        if model_name == MODEL_MAPPING["pro"]:
            fallback = MODEL_MAPPING["flash"]
            print(f"⚠️ [Direct HTTP] Pro failed ({resp.status_code}), falling back to Flash: {fallback}")
            fallback_url = f"{GEMINI_API_BASE_URL}/{fallback}:generateContent?key={api_key}"
            resp = http_requests.post(fallback_url, json=payload, headers=headers, timeout=timeout)
            model_name = fallback
            if resp.status_code != 200:
                body2 = resp.text[:2000]
                print(f"❌ [Direct HTTP] Flash also failed! Status {resp.status_code}:")
                print(f"❌ [Direct HTTP] FULL RESPONSE BODY:\n{body2}")
                raise Exception(f"Both Pro and Flash failed. Last status: {resp.status_code}. Body: {body2[:500]}")
        else:
            raise Exception(f"Gemini v1 API error {resp.status_code}: {body[:500]}")
    
    # ── Parse response ──
    data = resp.json()
    
    candidates = data.get("candidates", [])
    if not candidates:
        # Check for prompt feedback (blocked)
        feedback = data.get("promptFeedback", {})
        block_reason = feedback.get("blockReason", "")
        if block_reason:
            print(f"⚠️ [Direct HTTP] Prompt blocked: {block_reason}")
            raise Exception(f"Prompt blocked by safety: {block_reason}")
        print(f"⚠️ [Direct HTTP] No candidates in response: {json.dumps(data)[:500]}")
        return ""
    
    # Extract text from first candidate
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    result = "".join(text_parts).strip()
    
    print(f"✅ [Direct HTTP] {model_name} → {len(result)} chars")
    return result


def get_available_models() -> List[str]:
    """Get cached list of available model names."""
    if _available_models is None:
        return discover_models()
    return _available_models


def get_best_model(
    preferred: str,
    fallback_keywords: List[str] = None,
    category: str = "general"
) -> Optional[str]:
    """
    Find the best available model matching a preferred name.
    
    Strategy:
    1. Exact match: check if "models/{preferred}" is available
    2. Contains match: find any model containing the preferred string
    3. Fallback: search for models matching fallback_keywords
    4. Last resort: first available flash model
    
    Args:
        preferred: Preferred model name (e.g. "gemini-1.5-pro")
        fallback_keywords: List of fallback search terms (e.g. ["flash", "pro"])
        category: "pro" for KB/vision, "flash" for audit, "general" for main
    
    Returns:
        Best matching model name, or None if nothing found
    """
    available = get_available_models()
    
    if not available:
        print(f"   ⚠️ [Model Discovery] No models available, returning '{preferred}' as-is (may 404)")
        return preferred
    
    if fallback_keywords is None:
        if category == "pro":
            fallback_keywords = ["pro", "flash"]
        elif category == "flash":
            fallback_keywords = ["flash", "pro"]
        else:
            fallback_keywords = ["pro", "flash"]
    
    # Normalize preferred name
    preferred_lower = preferred.lower()
    preferred_full = f"models/{preferred}" if not preferred.startswith("models/") else preferred
    
    # ── Strategy 1: Exact match ──
    if preferred_full in available:
        print(f"   ✅ [Model Discovery] Exact match: {preferred_full}")
        return preferred_full
    
    # Also try without "models/" prefix
    for model in available:
        if model == preferred or model.endswith(f"/{preferred}"):
            print(f"   ✅ [Model Discovery] Exact match: {model}")
            return model
    
    # ── Strategy 2: Contains match (e.g. "gemini-1.5-pro" → "models/gemini-1.5-pro-002") ──
    contains_matches = [m for m in available if preferred_lower in m.lower()]
    if contains_matches:
        # Prefer the shortest match (most specific), or latest version
        best = sorted(contains_matches, key=lambda x: (-x.count('latest'), len(x)))[0]
        print(f"   ✅ [Model Discovery] Contains match for '{preferred}': {best}")
        return best
    
    # ── Strategy 3: Fallback keywords ──
    for keyword in fallback_keywords:
        keyword_matches = [m for m in available if keyword.lower() in m.lower()]
        if keyword_matches:
            # Prefer latest/newest versions
            best = sorted(keyword_matches, key=lambda x: (-x.count('latest'), -x.count('exp'), len(x)))[0]
            print(f"   ⚠️ [Model Discovery] Fallback '{keyword}' match for '{preferred}': {best}")
            return best
    
    # ── Strategy 4: First available model ──
    if available:
        first = available[0]
        print(f"   ⚠️ [Model Discovery] Last resort for '{preferred}': {first}")
        return first
    
    print(f"   ❌ [Model Discovery] No model found for '{preferred}'")
    return None


def get_best_pro_model() -> Optional[str]:
    """Shorthand: get the best available Pro model for KB/vision tasks."""
    return get_best_model(MODEL_MAPPING["pro"], category="pro")


def get_best_flash_model() -> Optional[str]:
    """Shorthand: get the best available Flash model for audit/lightweight tasks."""
    return get_best_model(MODEL_MAPPING["flash"], category="flash")


def get_model_status_report() -> Dict[str, Any]:
    """
    Generate a status report of model availability.
    Used by the health check.
    """
    available = get_available_models()
    
    pro_models = [m for m in available if 'pro' in m.lower()]
    flash_models = [m for m in available if 'flash' in m.lower()]
    other_models = [m for m in available if 'pro' not in m.lower() and 'flash' not in m.lower()]
    
    return {
        "total_available": len(available),
        "pro_models": pro_models,
        "flash_models": flash_models,
        "other_models": other_models,
        "all_models": available,
    }
