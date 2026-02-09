"""
Infographic Image Generator
============================
Generates a beautiful PNG infographic from NotebookLM analysis data.
The image is designed for WhatsApp sharing — clean, modern, Hebrew RTL.

RTL Strategy (v5.9.3):
  On Linux (Render), Pillow's manylinux wheels bundle libraqm, which handles
  bidirectional text natively via direction="rtl" + anchor="ra".
  On macOS, raqm is usually absent, so we fall back to python-bidi's
  get_display() for visual reordering + manual right-alignment.

  CRITICAL: using get_display() WITH raqm causes double-reversal → LTR output.
  The code auto-detects raqm at import time and picks the correct path.

Font handling:
  1. System fonts (DejaVu Sans — supports Hebrew)
  2. Download Noto Sans Hebrew from Google Fonts (cached in /tmp)
  3. Pillow default font (ugly but functional)
"""

import os
import io
import tempfile
import textwrap
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy imports — only load when generating
_PIL_AVAILABLE = False
_BIDI_AVAILABLE = False
_HAS_RAQM = False  # True on Linux manylinux (Render), False on macOS


def _ensure_imports():
    """Lazy import PIL and bidi. Detect raqm for RTL strategy."""
    global _PIL_AVAILABLE, _BIDI_AVAILABLE, _HAS_RAQM
    global Image, ImageDraw, ImageFont, get_display

    if _PIL_AVAILABLE:
        return True

    try:
        from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont, features
        Image = _Image
        ImageDraw = _ImageDraw
        ImageFont = _ImageFont
        _PIL_AVAILABLE = True

        # Detect raqm — determines RTL rendering strategy
        _HAS_RAQM = bool(features.check_feature('raqm'))
        if _HAS_RAQM:
            logger.info("[Infographic] raqm available — using native direction='rtl' (NO get_display)")
            print("📓 [Infographic] raqm detected → native RTL mode")
        else:
            logger.info("[Infographic] raqm NOT available — using python-bidi get_display() for RTL")
            print("📓 [Infographic] no raqm → python-bidi fallback RTL mode")
    except ImportError:
        logger.error("[Infographic] Pillow not installed")
        return False

    try:
        from bidi.algorithm import get_display as _get_display
        get_display = _get_display
        _BIDI_AVAILABLE = True
    except ImportError:
        logger.warning("[Infographic] python-bidi not installed — Hebrew may render incorrectly")
        get_display = lambda x: x  # identity function as fallback
        _BIDI_AVAILABLE = True  # allow rendering even without bidi

    return True


# ═══════════════════════════════════════════════════════════════════════
# COLORS
# ═══════════════════════════════════════════════════════════════════════

COLORS = {
    "bg":               "#F0F2F5",      # light gray background
    "card_bg":          "#FFFFFF",      # white cards
    "header_bg":        "#1A1A2E",      # deep navy header
    "header_text":      "#FFFFFF",      # white header text
    "header_accent":    "#E94560",      # coral accent line
    "title":            "#1A1A2E",      # dark text
    "body":             "#333333",      # body text
    "muted":            "#888888",      # muted text
    "section_summary":  "#0F3460",      # navy
    "section_topics":   "#16697A",      # teal
    "section_actions":  "#E94560",      # coral/red
    "section_decisions":"#533483",      # purple
    "section_quotes":   "#0F3460",      # navy
    "section_speakers": "#16697A",      # teal
    "section_mood":     "#533483",      # purple
    "priority_high":    "#E94560",      # red
    "priority_medium":  "#F0A500",      # amber
    "priority_low":     "#2ECC71",      # green
    "divider":          "#E0E0E0",      # light gray divider
    "card_shadow":      "#D0D0D0",      # subtle shadow
}

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# ═══════════════════════════════════════════════════════════════════════
# FONT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

_font_cache: Dict[str, Any] = {}


def _find_font(size: int, bold: bool = False) -> Any:
    """Find a font that supports Hebrew, with caching and fallback."""
    cache_key = f"{size}_{bold}"
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    # Font search paths
    if bold:
        search_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansHebrew-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/tmp/_infographic_fonts/NotoSansHebrew-Bold.ttf",
        ]
    else:
        search_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/tmp/_infographic_fonts/NotoSansHebrew-Regular.ttf",
        ]

    for path in search_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[cache_key] = font
                return font
            except Exception:
                continue

    # Try downloading Noto Sans Hebrew
    _download_font()
    fallback_path = "/tmp/_infographic_fonts/NotoSansHebrew-Bold.ttf" if bold else "/tmp/_infographic_fonts/NotoSansHebrew-Regular.ttf"
    if os.path.exists(fallback_path):
        try:
            font = ImageFont.truetype(fallback_path, size)
            _font_cache[cache_key] = font
            return font
        except Exception:
            pass

    # Ultimate fallback
    logger.warning("[Infographic] No Hebrew font found — using default")
    font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def _download_font():
    """Download Noto Sans Hebrew from Google Fonts (one-time, cached in /tmp)."""
    target_dir = "/tmp/_infographic_fonts"
    if os.path.exists(os.path.join(target_dir, "NotoSansHebrew-Regular.ttf")):
        return  # Already downloaded

    try:
        import requests
        import zipfile

        os.makedirs(target_dir, exist_ok=True)
        print("📓 [Infographic] Downloading Noto Sans Hebrew font...")

        url = "https://fonts.google.com/download?family=Noto+Sans+Hebrew"
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                # Look for static regular and bold TTFs
                lower = name.lower()
                if "static" in lower or "notosanshebrew-" in lower:
                    if lower.endswith("regular.ttf"):
                        data = zf.read(name)
                        with open(os.path.join(target_dir, "NotoSansHebrew-Regular.ttf"), 'wb') as f:
                            f.write(data)
                    elif lower.endswith("bold.ttf"):
                        data = zf.read(name)
                        with open(os.path.join(target_dir, "NotoSansHebrew-Bold.ttf"), 'wb') as f:
                            f.write(data)

        print("✅ [Infographic] Font downloaded successfully")

    except Exception as e:
        logger.warning(f"[Infographic] Font download failed: {e}")
        print(f"⚠️ [Infographic] Font download failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# TEXT UTILITIES
# ═══════════════════════════════════════════════════════════════════════

def _bidi(text: str) -> str:
    """Apply bidi algorithm for visual Hebrew rendering.

    When raqm IS available: returns text unchanged (raqm handles bidi natively).
    When raqm is NOT available: uses python-bidi get_display() for visual reordering.
    """
    if not text:
        return ""
    if _HAS_RAQM:
        return text  # raqm handles bidirectional text natively — do NOT reorder
    try:
        return get_display(text)
    except Exception:
        return text


def _wrap_text(text: str, font, max_width: int, draw) -> List[str]:
    """Wrap text to fit within max_width pixels.
    Text stays in logical order — the caller handles visual rendering.
    """
    if not text:
        return []

    words = text.split()
    lines = []
    current_line = []

    # Use direction="rtl" for measurement when raqm is available
    extra_kwargs = {"direction": "rtl"} if _HAS_RAQM else {}

    for word in words:
        test = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test, font=font, **extra_kwargs)
        w = bbox[2] - bbox[0]
        if w <= max_width and current_line:
            current_line.append(word)
        elif not current_line:
            current_line = [word]
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def _draw_text_rtl(draw, x_right: int, y: int, text: str, font, fill, max_width: int = 0) -> int:
    """
    Draw RTL text right-aligned at x_right, y.
    Returns the y coordinate after the last line.
    If max_width > 0, wraps text.

    Dual-mode:
      raqm present  → direction="rtl", anchor="ra" (right-ascender)
      raqm absent   → get_display() + manual right-alignment
    """
    if not text:
        return y

    if max_width > 0:
        lines = _wrap_text(text, font, max_width, draw)
    else:
        lines = [text]

    line_height = font.size + 6  # approximate line height

    for line in lines:
        if _HAS_RAQM:
            # Native RTL — Pillow + raqm handle bidi natively
            draw.text((x_right, y), line, font=font, fill=fill,
                      direction="rtl", anchor="ra")
        else:
            # Manual RTL — python-bidi reorders, we right-align manually
            display_text = _bidi(line)
            bbox = draw.textbbox((0, 0), display_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = x_right - text_width
            draw.text((x, y), display_text, font=font, fill=fill)
        y += line_height

    return y


# ═══════════════════════════════════════════════════════════════════════
# DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _draw_rounded_rect(draw, xy, radius, fill, outline=None):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def _draw_section_header(draw, y: int, x_right: int, text: str, color: str,
                          font_bold, icon: str = "") -> int:
    """Draw a section header with icon and colored accent."""
    color_rgb = _hex_to_rgb(color)

    # Draw colored circle (icon indicator)
    circle_r = 8
    circle_x = x_right - circle_r
    circle_y = y + 4
    draw.ellipse(
        (circle_x - circle_r, circle_y - circle_r,
         circle_x + circle_r, circle_y + circle_r),
        fill=color_rgb
    )

    # Draw header text — right of the circle
    header_text = f"{icon} {text}" if icon else text
    text_anchor_x = circle_x - circle_r - 10  # left of the circle

    if _HAS_RAQM:
        # Native RTL — anchor="ra" means x is right edge of text
        draw.text((text_anchor_x, y), header_text, font=font_bold,
                  fill=color_rgb, direction="rtl", anchor="ra")
    else:
        # Manual RTL
        display_text = _bidi(header_text)
        bbox = draw.textbbox((0, 0), display_text, font=font_bold)
        text_width = bbox[2] - bbox[0]
        draw.text((text_anchor_x - text_width, y), display_text,
                  font=font_bold, fill=color_rgb)

    return y + font_bold.size + 12


# ═══════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════

def generate_infographic(analysis: Dict[str, Any], output_path: str = None) -> Optional[str]:
    """
    Generate a beautiful PNG infographic from NotebookLM analysis.

    Args:
        analysis: The structured analysis dict from NotebookLMService
        output_path: Optional output path. If None, uses a temp file.

    Returns:
        Path to the generated PNG file, or None on failure
    """
    if not _ensure_imports():
        return None

    if not analysis:
        return None

    try:
        # ── Fonts ──
        font_title = _find_font(28, bold=True)
        font_section = _find_font(20, bold=True)
        font_body = _find_font(16, bold=False)
        font_body_bold = _find_font(16, bold=True)
        font_small = _find_font(13, bold=False)
        font_quote = _find_font(15, bold=False)

        # ── Layout constants ──
        W = 800
        PADDING = 35
        CARD_PADDING = 20
        CONTENT_RIGHT = W - PADDING  # right edge for RTL text
        CONTENT_WIDTH = W - 2 * PADDING - 2 * CARD_PADDING  # text width inside cards
        SECTION_GAP = 16
        CARD_RADIUS = 12

        # ── Pre-calculate height ──
        # We'll draw on a tall canvas first, then crop
        MAX_H = 4000
        img = Image.new("RGB", (W, MAX_H), _hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)
        y = 0

        # ═══════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════
        header_h = 90
        draw.rectangle((0, 0, W, header_h), fill=_hex_to_rgb(COLORS["header_bg"]))
        # Accent line
        draw.rectangle((0, header_h - 4, W, header_h), fill=_hex_to_rgb(COLORS["header_accent"]))

        # Title
        title = "ניתוח מעמיק — Second Brain"
        if _HAS_RAQM:
            draw.text((W - PADDING, 20), title, font=font_title,
                      fill=_hex_to_rgb(COLORS["header_text"]),
                      direction="rtl", anchor="ra")
        else:
            title_display = _bidi(title)
            bbox = draw.textbbox((0, 0), title_display, font=font_title)
            tx = W - PADDING - (bbox[2] - bbox[0])
            draw.text((tx, 20), title_display, font=font_title, fill=_hex_to_rgb(COLORS["header_text"]))

        # Subtitle (date + speakers)
        meta = analysis.get("_metadata", {})
        date_str = meta.get("generated_at", "")[:10] if meta.get("generated_at") else ""
        speakers_list = meta.get("speakers", [])
        speakers_str = ", ".join(speakers_list[:4]) if speakers_list else ""
        subtitle_parts = [s for s in [date_str, speakers_str] if s]
        subtitle = " | ".join(subtitle_parts) if subtitle_parts else ""
        if subtitle:
            if _HAS_RAQM:
                draw.text((W - PADDING, 55), subtitle, font=font_small,
                          fill=(200, 200, 210), direction="rtl", anchor="ra")
            else:
                sub_display = _bidi(subtitle)
                bbox_s = draw.textbbox((0, 0), sub_display, font=font_small)
                sx = W - PADDING - (bbox_s[2] - bbox_s[0])
                draw.text((sx, 55), sub_display, font=font_small, fill=(200, 200, 210))

        y = header_h + SECTION_GAP

        # ═══════════════════════════════════════
        # HELPER: Draw a card section
        # ═══════════════════════════════════════
        def draw_card(y_start, section_color, section_title, icon, content_fn):
            """
            Draw a white card with section header and content.
            content_fn(draw, y, content_right, content_width) -> y_end
            Returns y after the card + gap.
            """
            nonlocal draw, img

            # Pre-calculate content height on a temp canvas
            temp_img = Image.new("RGB", (W, 2000), (255, 255, 255))
            temp_draw = ImageDraw.Draw(temp_img)
            cr = CONTENT_RIGHT - CARD_PADDING
            cw = CONTENT_WIDTH

            # Section header
            ty = CARD_PADDING
            ty = _draw_section_header(temp_draw, ty, cr, section_title, section_color, font_section, icon)
            ty += 4
            # Content
            ty = content_fn(temp_draw, ty, cr, cw)
            ty += CARD_PADDING

            card_height = ty
            card_y0 = y_start
            card_y1 = y_start + card_height

            # Draw card background with shadow
            shadow_offset = 2
            _draw_rounded_rect(
                draw,
                (PADDING + shadow_offset, card_y0 + shadow_offset,
                 W - PADDING + shadow_offset, card_y1 + shadow_offset),
                CARD_RADIUS,
                fill=_hex_to_rgb(COLORS["card_shadow"])
            )
            _draw_rounded_rect(
                draw,
                (PADDING, card_y0, W - PADDING, card_y1),
                CARD_RADIUS,
                fill=_hex_to_rgb(COLORS["card_bg"])
            )

            # Draw colored left accent bar
            bar_width = 5
            draw.rectangle(
                (W - PADDING - bar_width, card_y0 + CARD_RADIUS,
                 W - PADDING, card_y1 - CARD_RADIUS),
                fill=_hex_to_rgb(section_color)
            )

            # Now draw the actual content on the main canvas
            cr = CONTENT_RIGHT - CARD_PADDING
            cw = CONTENT_WIDTH
            content_y = card_y0 + CARD_PADDING
            content_y = _draw_section_header(draw, content_y, cr, section_title, section_color, font_section, icon)
            content_y += 4
            content_fn(draw, content_y, cr, cw)

            return card_y1 + SECTION_GAP

        # ═══════════════════════════════════════
        # SECTION 1: Executive Summary
        # ═══════════════════════════════════════
        summary = analysis.get("executive_summary", "")
        if summary and not summary.strip().startswith("{"):
            def draw_summary(d, cy, cr, cw):
                return _draw_text_rtl(d, cr, cy, summary, font_body, _hex_to_rgb(COLORS["body"]), cw)
            y = draw_card(y, COLORS["section_summary"], "תמצית מנהלים", "", draw_summary)

        # ═══════════════════════════════════════
        # SECTION 2: Key Topics
        # ═══════════════════════════════════════
        topics = analysis.get("key_topics", [])
        if topics:
            def draw_topics(d, cy, cr, cw):
                for i, topic in enumerate(topics[:6], 1):
                    name = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
                    details = topic.get("details", "") if isinstance(topic, dict) else ""
                    if not name:
                        continue

                    # Topic title with number
                    num_text = f".{i}"
                    cy = _draw_text_rtl(d, cr, cy, f"{name} {num_text}", font_body_bold,
                                        _hex_to_rgb(COLORS["section_topics"]), cw)
                    # Details
                    if details:
                        cy = _draw_text_rtl(d, cr - 15, cy, details[:200], font_small,
                                            _hex_to_rgb(COLORS["muted"]), cw - 15)
                    cy += 6
                return cy
            y = draw_card(y, COLORS["section_topics"], "נושאים מרכזיים", "", draw_topics)

        # ═══════════════════════════════════════
        # SECTION 3: Action Items
        # ═══════════════════════════════════════
        actions = analysis.get("action_items", [])
        if actions:
            def draw_actions(d, cy, cr, cw):
                for action in actions[:5]:
                    task = action.get("task", "") if isinstance(action, dict) else str(action)
                    owner = action.get("owner", "") if isinstance(action, dict) else ""
                    priority = action.get("priority", "") if isinstance(action, dict) else ""

                    if not task:
                        continue

                    # Priority indicator
                    p_color = COLORS["priority_high"] if priority == "high" \
                        else COLORS["priority_medium"] if priority == "medium" \
                        else COLORS["priority_low"]
                    circle_x = cr - 5
                    d.ellipse((circle_x - 5, cy + 4, circle_x + 5, cy + 14),
                              fill=_hex_to_rgb(p_color))

                    # Task text
                    task_text = task
                    if owner:
                        task_text += f" ({owner})"
                    cy = _draw_text_rtl(d, cr - 18, cy, task_text, font_body,
                                        _hex_to_rgb(COLORS["body"]), cw - 18)
                    cy += 4
                return cy
            y = draw_card(y, COLORS["section_actions"], "פריטי פעולה", "", draw_actions)

        # ═══════════════════════════════════════
        # SECTION 4: Decisions
        # ═══════════════════════════════════════
        decisions = analysis.get("decisions_made", [])
        if decisions:
            def draw_decisions(d, cy, cr, cw):
                for dec in decisions[:5]:
                    decision_text = dec.get("decision", "") if isinstance(dec, dict) else str(dec)
                    if not decision_text:
                        continue
                    bullet = _bidi("•")
                    d.text((cr - 8, cy), bullet, font=font_body, fill=_hex_to_rgb(COLORS["section_decisions"]))
                    cy = _draw_text_rtl(d, cr - 18, cy, decision_text, font_body,
                                        _hex_to_rgb(COLORS["body"]), cw - 18)
                    cy += 4
                return cy
            y = draw_card(y, COLORS["section_decisions"], "החלטות", "", draw_decisions)

        # ═══════════════════════════════════════
        # SECTION 5: Notable Quotes
        # ═══════════════════════════════════════
        quotes = analysis.get("notable_quotes", [])
        if quotes:
            def draw_quotes(d, cy, cr, cw):
                for q in quotes[:3]:
                    quote_text = q.get("quote", "") if isinstance(q, dict) else str(q)
                    speaker = q.get("speaker", "") if isinstance(q, dict) else ""
                    if not quote_text:
                        continue

                    # Quote with quotation marks
                    full_quote = f'"{quote_text}"'
                    cy = _draw_text_rtl(d, cr, cy, full_quote, font_quote,
                                        _hex_to_rgb(COLORS["section_quotes"]), cw)
                    if speaker:
                        cy = _draw_text_rtl(d, cr - 20, cy, f"— {speaker}", font_small,
                                            _hex_to_rgb(COLORS["muted"]), cw - 20)
                    cy += 8
                return cy
            y = draw_card(y, COLORS["section_quotes"], "ציטוטים בולטים", "", draw_quotes)

        # ═══════════════════════════════════════
        # SECTION 6: Speaker Profiles
        # ═══════════════════════════════════════
        profiles = analysis.get("speaker_profiles", [])
        if profiles:
            def draw_profiles(d, cy, cr, cw):
                for p in profiles[:5]:
                    name = p.get("name", "") if isinstance(p, dict) else str(p)
                    role = p.get("role_in_conversation", "") if isinstance(p, dict) else ""
                    contributions = p.get("key_contributions", "") if isinstance(p, dict) else ""
                    if not name:
                        continue

                    name_with_role = name
                    if role:
                        name_with_role += f" — {role}"
                    cy = _draw_text_rtl(d, cr, cy, name_with_role, font_body_bold,
                                        _hex_to_rgb(COLORS["section_speakers"]), cw)
                    if contributions:
                        cy = _draw_text_rtl(d, cr - 10, cy, contributions[:150], font_small,
                                            _hex_to_rgb(COLORS["muted"]), cw - 10)
                    cy += 6
                return cy
            y = draw_card(y, COLORS["section_speakers"], "פרופיל דוברים", "", draw_profiles)

        # ═══════════════════════════════════════
        # SECTION 7: Mood & Tone
        # ═══════════════════════════════════════
        mood = analysis.get("mood_and_tone", "")
        if mood:
            def draw_mood(d, cy, cr, cw):
                return _draw_text_rtl(d, cr, cy, mood, font_body, _hex_to_rgb(COLORS["body"]), cw)
            y = draw_card(y, COLORS["section_mood"], "אווירה כללית", "", draw_mood)

        # ═══════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════
        y += 5
        footer_text = "Second Brain — Powered by Gemini AI"
        ft_display = footer_text  # English, no bidi needed
        bbox_f = draw.textbbox((0, 0), ft_display, font=font_small)
        fx = (W - (bbox_f[2] - bbox_f[0])) // 2
        draw.text((fx, y), ft_display, font=font_small, fill=_hex_to_rgb(COLORS["muted"]))
        y += 30

        # ═══════════════════════════════════════
        # CROP TO CONTENT HEIGHT
        # ═══════════════════════════════════════
        final_height = min(y, MAX_H)
        img = img.crop((0, 0, W, final_height))

        # ═══════════════════════════════════════
        # SAVE
        # ═══════════════════════════════════════
        if not output_path:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="infographic_")
            output_path = tmp.name
            tmp.close()

        img.save(output_path, "PNG", optimize=True)
        file_size = os.path.getsize(output_path)
        print(f"🖼️ [Infographic] Generated: {output_path} ({file_size:,} bytes, {W}x{final_height})")
        return output_path

    except Exception as e:
        logger.error(f"[Infographic] Generation error: {e}")
        import traceback
        traceback.print_exc()
        return None
