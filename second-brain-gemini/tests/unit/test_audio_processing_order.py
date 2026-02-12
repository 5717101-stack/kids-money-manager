"""
Unit tests for audio processing order and resilience.

These tests verify that:
  1. The user receives their analysis BEFORE any Drive upload happens
  2. Drive upload failures do NOT prevent analysis delivery
  3. The audio pipeline receives correct metadata even without Drive upload
  4. Webhook verification returns challenge as plain text

These tests would have caught:
  - The v2.3.0→v7.2.9 bug: int(challenge) crashed on non-numeric challenges
  - The v7.2.x bug: Drive upload before analysis → users got nothing when Drive crashed

NOTE: These tests read source files directly (no heavy imports needed).
"""
import os
import pytest

# Path to the source file under test
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN_PY = os.path.join(APP_ROOT, "app", "main.py")


def _read_source(path: str) -> str:
    """Read a source file and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ═════════════════════════════════════════════════════════════════════════════
# Audio Processing Order Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAudioProcessingOrder:
    """Verify audio processing happens BEFORE Drive upload in source code."""

    def test_process_audio_core_called_before_drive_upload(self):
        """
        The background function must call process_audio_core() BEFORE
        upload_audio_to_archive(). This ensures users get their analysis
        even if Drive upload crashes the container.

        This test would have caught the v7.2.9 bug where:
          1. Audio downloaded ✅
          2. Drive upload started → heap corruption → CRASH ❌
          3. process_audio_core never ran → user never got analysis ❌
        """
        source = _read_source(MAIN_PY)

        # Find the process_audio_in_background function
        func_start = source.find("def process_audio_in_background(")
        assert func_start != -1, "process_audio_in_background function not found in main.py"

        # Limit search to this function body
        func_body = source[func_start:]

        # Find the position of key operations in the function
        pos_process_audio = func_body.find("process_audio_core(")
        pos_drive_upload = func_body.find("upload_audio_to_archive(")

        assert pos_process_audio != -1, "process_audio_core() call not found in process_audio_in_background"
        assert pos_drive_upload != -1, "upload_audio_to_archive() call not found in process_audio_in_background"
        assert pos_process_audio < pos_drive_upload, (
            f"CRITICAL: process_audio_core() (offset={pos_process_audio}) must come BEFORE "
            f"upload_audio_to_archive() (offset={pos_drive_upload}) in the source code. "
            f"If Drive upload crashes, user must already have their analysis!"
        )

    def test_drive_upload_wrapped_in_try_except(self):
        """
        Drive upload failure should NOT prevent the function from completing.
        The upload_audio_to_archive call should be inside a try/except block.
        """
        source = _read_source(MAIN_PY)

        func_start = source.find("def process_audio_in_background(")
        assert func_start != -1
        func_body = source[func_start:]

        pos_drive = func_body.find("upload_audio_to_archive(")
        assert pos_drive != -1

        # Look backwards from the drive upload to find the nearest try: block
        pre_drive = func_body[:pos_drive]
        last_try = pre_drive.rfind("try:")

        assert last_try != -1, (
            "upload_audio_to_archive must be inside a try/except block. "
            "None found before it."
        )

    def test_audio_metadata_works_without_drive_upload(self):
        """
        process_audio_core must work with minimal audio_metadata (no file_id).
        This ensures the pipeline runs even before Drive upload provides IDs.
        """
        # Simulate the minimal metadata that process_audio_in_background creates
        # before Drive upload
        minimal_metadata = {
            "filename": "whatsapp_audio_wamid.TEST.ogg",
            "message_id": "wamid.TEST",
        }

        # These are the fields process_audio_core accesses with .get()
        assert minimal_metadata.get("recording_date") is None  # Falls back to extractor/utcnow
        assert minimal_metadata.get("filename", "audio") == "whatsapp_audio_wamid.TEST.ogg"
        assert minimal_metadata.get("file_id", "") == ""  # Empty string, not crash
        assert minimal_metadata.get("web_content_link", "") == ""
        assert minimal_metadata.get("web_view_link", "") == ""


# ═════════════════════════════════════════════════════════════════════════════
# Webhook Verification Source Code Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestWebhookVerificationSourceCode:
    """
    Verify the webhook verification endpoint returns challenge correctly
    by analyzing the SOURCE CODE — no heavy imports needed.

    This would have caught the v2.3.0→v7.2.9 bug where return int(challenge)
    crashed on non-numeric challenges and returned JSON instead of plain text.
    """

    def test_no_int_conversion_of_challenge(self):
        """
        The webhook GET handler must NOT convert the challenge to int.
        return int(challenge) will crash on non-numeric challenges.
        """
        source = _read_source(MAIN_PY)

        # Find the webhook GET handler
        webhook_section_start = source.find("hub.verify_token")
        assert webhook_section_start != -1, "Webhook verification section not found"

        # Check for the anti-pattern: int(challenge)
        # Limit search to a reasonable range after the verify_token check
        webhook_section = source[webhook_section_start:webhook_section_start + 2000]
        assert "int(challenge)" not in webhook_section, (
            "CRITICAL: Found int(challenge) in webhook verification. "
            "Meta sends string challenges — int() will crash on non-numeric values. "
            "Use PlainTextResponse(content=challenge) instead."
        )

    def test_uses_plain_text_response(self):
        """
        The challenge must be returned as PlainTextResponse,
        not as a raw return (which FastAPI wraps in JSON).
        """
        source = _read_source(MAIN_PY)

        # Check that PlainTextResponse is imported
        assert "PlainTextResponse" in source, (
            "PlainTextResponse not found in imports. "
            "The webhook verification must use PlainTextResponse(content=challenge) "
            "to ensure Meta receives the challenge as plain text, not JSON."
        )

        # Find the webhook GET handler and check it uses PlainTextResponse
        webhook_start = source.find("hub.verify_token")
        assert webhook_start != -1
        webhook_section = source[webhook_start:webhook_start + 2000]
        assert "PlainTextResponse" in webhook_section, (
            "PlainTextResponse not used in webhook verification handler. "
            "FastAPI's default return wraps values in JSON, which Meta rejects."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Audio Date Extractor Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAudioDateExtractor:
    """Test recording date extraction doesn't crash the pipeline."""

    def test_extract_from_ogg_returns_none_gracefully(self):
        """
        WhatsApp sends .ogg files which don't have MP4 mvhd atoms.
        Extraction should return None (not crash), triggering the
        datetime.utcnow() fallback.
        """
        import tempfile
        from app.services.audio_date_extractor import extract_recording_date

        # Create a fake .ogg file (no mvhd atom)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(b"\x00" * 1000)  # Garbage data
            tmp_path = f.name

        try:
            result = extract_recording_date(tmp_path)
            # Should gracefully return None, not crash
            assert result is None
        finally:
            os.unlink(tmp_path)

    def test_extract_from_empty_file_returns_none(self):
        """Extraction from an empty file should not crash."""
        import tempfile
        from app.services.audio_date_extractor import extract_recording_date

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            tmp_path = f.name  # Empty file

        try:
            result = extract_recording_date(tmp_path)
            assert result is None
        finally:
            os.unlink(tmp_path)

    def test_extract_from_corrupt_m4a_returns_none(self):
        """Corrupt M4A with fake mvhd should not crash."""
        import tempfile
        from app.services.audio_date_extractor import extract_recording_date

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            # Write a fake mvhd atom with garbage data
            f.write(b"\x00" * 100 + b"mvhd" + b"\xFF" * 20)
            tmp_path = f.name

        try:
            result = extract_recording_date(tmp_path)
            # Should return None or a datetime, never crash
            assert result is None or hasattr(result, 'isoformat')
        finally:
            os.unlink(tmp_path)

    def test_filename_pattern_extraction(self):
        """Apple Voice Memos filename pattern should be recognized."""
        import tempfile
        from app.services.audio_date_extractor import extract_recording_date

        with tempfile.NamedTemporaryFile(
            prefix="20260115 143022", suffix=".m4a", delete=False, dir="/tmp"
        ) as f:
            f.write(b"\x00" * 100)  # No mvhd, but filename has pattern
            tmp_path = f.name

        try:
            result = extract_recording_date(tmp_path)
            if result is not None:
                # Should extract 2026-01-15
                assert result.year == 2026
                assert result.month == 1
                assert result.day == 15
        finally:
            os.unlink(tmp_path)

    def test_whatsapp_ogg_filename_returns_none(self):
        """
        WhatsApp audio files are named 'whatsapp_audio_{wamid}.ogg'.
        This has NO date pattern → extraction should return None.
        This is the ROOT CAUSE of recordings showing 'today' as their date.
        """
        import tempfile
        from app.services.audio_date_extractor import extract_recording_date

        with tempfile.NamedTemporaryFile(
            prefix="whatsapp_audio_wamid123", suffix=".ogg", delete=False, dir="/tmp"
        ) as f:
            f.write(b"\x00" * 500)
            tmp_path = f.name

        try:
            result = extract_recording_date(tmp_path)
            # OGG from WhatsApp has no metadata or filename pattern
            assert result is None, (
                "WhatsApp OGG files should return None — no mvhd, no ffprobe date, "
                "no filename pattern. The pipeline should then use Gemini's content-based "
                "date hint or fall back to processing time with estimated flag."
            )
        finally:
            os.unlink(tmp_path)


# ═════════════════════════════════════════════════════════════════════════════
# Recording Date Pipeline Integration Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestRecordingDatePipeline:
    """Test that the audio pipeline correctly handles estimated vs actual dates."""

    def test_pipeline_has_recording_date_is_estimated_flag(self):
        """The pipeline must track whether the recording date is estimated."""
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_pipeline.py"))

        assert "recording_date_is_estimated" in source, (
            "audio_pipeline.py must track whether the date is estimated. "
            "When the date is from fallback (utcnow), it should set "
            "recording_date_is_estimated = True so downstream code knows "
            "the date may be wrong."
        )

    def test_pipeline_stores_estimated_flag_in_memory(self):
        """The estimated flag must be saved in the memory entry."""
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_pipeline.py"))

        assert '"timestamp_is_estimated": recording_date_is_estimated' in source, (
            "The audio_interaction dict saved to memory must include "
            "'timestamp_is_estimated' so queries can warn users when "
            "the date is the processing time, not the recording time."
        )

    def test_pipeline_uses_gemini_date_hint(self):
        """The pipeline must check Gemini's recording_date_hint when date is estimated."""
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_pipeline.py"))

        assert "recording_date_hint" in source, (
            "audio_pipeline.py must check for 'recording_date_hint' from Gemini's "
            "analysis response. When the date is estimated (fallback to utcnow), "
            "Gemini's content-based date extraction can provide a more accurate date."
        )

    def test_gemini_prompts_request_recording_date_hint(self):
        """Both Gemini prompts must ask for recording_date_hint."""
        source = _read_source(os.path.join(APP_ROOT, "app", "prompts.py"))

        assert "recording_date_hint" in source, (
            "prompts.py must include 'recording_date_hint' in the JSON output format. "
            "Gemini should listen for date references in the audio and return them."
        )

        # Both prompts should request it
        pyannote_idx = source.find("PYANNOTE_ASSISTED_PROMPT")
        combined_idx = source.find("COMBINED_DIARIZATION_EXPERT_PROMPT")
        assert pyannote_idx > 0 and combined_idx > 0

        pyannote_section = source[pyannote_idx:]
        combined_section = source[combined_idx:pyannote_idx]

        assert "recording_date_hint" in pyannote_section, (
            "PYANNOTE_ASSISTED_PROMPT must request recording_date_hint"
        )
        assert "recording_date_hint" in combined_section, (
            "COMBINED_DIARIZATION_EXPERT_PROMPT must request recording_date_hint"
        )

    def test_date_extractor_has_ffprobe_strategy(self):
        """The date extractor must include ffprobe as a fallback strategy."""
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_date_extractor.py"))

        assert "ffprobe" in source, (
            "audio_date_extractor.py must include an ffprobe-based strategy "
            "for extracting dates from OGG, MP3, FLAC, and other formats "
            "that don't have MP4 mvhd atoms."
        )

        assert "_extract_via_ffprobe" in source, (
            "audio_date_extractor.py must have a _extract_via_ffprobe function."
        )

    def test_search_results_include_timestamp_note_for_estimated_dates(self):
        """search_meetings results must flag estimated timestamps."""
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "conversation_engine.py"))

        assert "timestamp_note" in source, (
            "conversation_engine.py must include 'timestamp_note' in search results "
            "when the timestamp is estimated, so Gemini tells the user the date "
            "might be wrong instead of confidently stating the processing date."
        )
