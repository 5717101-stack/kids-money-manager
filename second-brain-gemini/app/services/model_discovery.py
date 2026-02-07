"""
Model Discovery Service — Dynamic Gemini Model Selection

Instead of hardcoding model names that may 404, this module:
1. Calls genai.list_models() at startup to discover what's actually available
2. Caches the result so it only runs once per process
3. Provides get_best_model() to find the best match for a preferred name
4. Logs the exact available models for debugging

Usage:
    from app.services.model_discovery import get_best_model, get_available_models
    
    model_name = get_best_model("gemini-1.5-pro")  # Returns actual available model
    model = genai.GenerativeModel(model_name)
"""

import logging
from typing import List, Optional, Dict, Any
from threading import Lock

import google.generativeai as genai

logger = logging.getLogger(__name__)

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
    return get_best_model("gemini-1.5-pro", category="pro")


def get_best_flash_model() -> Optional[str]:
    """Shorthand: get the best available Flash model for audit/lightweight tasks."""
    return get_best_model("gemini-2.0-flash", category="flash")


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
