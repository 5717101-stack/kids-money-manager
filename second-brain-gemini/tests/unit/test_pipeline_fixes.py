"""
Unit tests for the 4 pipeline fixes (v7.3.4):

1. Infographic/PDF is always sent (image → text → expert fallback)
2. No SMS-era character limit truncation on WhatsApp messages
3. ALL unknown speakers get identification clips (even short-segment ones)
4. Inbox files ALWAYS move to archive after processing

These tests use source code analysis and isolated unit testing — no heavy
imports, no GPU, no network. They run in < 5 seconds in CI/CD.
"""
import os
import re
import pytest

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _read_source(path: str) -> str:
    with open(os.path.join(APP_ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


# ═════════════════════════════════════════════════════════════════════════════
# Issue 1: Infographic must ALWAYS be sent (with guaranteed fallback chain)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestInfographicAlwaysSent:
    """Verify infographic has a guaranteed 3-tier fallback in the pipeline."""

    def test_infographic_has_image_attempt(self):
        """Pipeline must attempt PNG infographic generation."""
        source = _read_source("app/services/audio_pipeline.py")
        assert "generate_infographic" in source, (
            "audio_pipeline.py must import/call generate_infographic"
        )
        assert "send_image" in source, (
            "audio_pipeline.py must call send_image for PNG infographic"
        )

    def test_infographic_has_text_fallback(self):
        """If image fails, pipeline must send text infographic."""
        source = _read_source("app/services/audio_pipeline.py")
        assert "format_infographic" in source, (
            "audio_pipeline.py must call format_infographic as text fallback"
        )

    def test_infographic_has_guaranteed_final_fallback(self):
        """If both image and text infographic fail, send a basic summary."""
        source = _read_source("app/services/audio_pipeline.py")
        assert "Infographic Fallback" in source, (
            "audio_pipeline.py must have a guaranteed final fallback "
            "that sends a basic summary even if NotebookLM fails entirely"
        )

    def test_infographic_fallback_uses_available_data(self):
        """The final fallback must use the data already available (summary, speakers, topics)."""
        source = _read_source("app/services/audio_pipeline.py")
        # The guaranteed fallback should use the already-available data
        fallback_start = source.find("Infographic Fallback")
        assert fallback_start > 0
        # Check the CONDITION that triggers the fallback (outer check uses expert_summary)
        # and the body that builds the message (uses summary_text, speaker_names, topics)
        pre_fallback = source[fallback_start - 200:fallback_start]
        fallback_section = source[fallback_start:fallback_start + 800]
        assert "expert_summary" in pre_fallback, (
            "Guaranteed fallback condition must check expert_summary is available"
        )
        assert "summary_text" in fallback_section, (
            "Guaranteed fallback must use summary_text"
        )
        assert "speaker_names" in fallback_section, (
            "Guaranteed fallback must include speaker names"
        )

    def test_infographic_sent_flag_tracked(self):
        """Pipeline must track whether ANY infographic was sent."""
        source = _read_source("app/services/audio_pipeline.py")
        assert "infographic_sent" in source, (
            "Pipeline must track infographic_sent flag to trigger fallbacks"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Issue 2: No SMS-era character limit on WhatsApp messages
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestNoCharacterLimit:
    """Verify the SMS-era 1200 char limit has been removed."""

    def test_no_max_length_enforcement_in_format_for_whatsapp(self):
        """format_for_whatsapp must NOT enforce a character limit."""
        source = _read_source("app/services/expert_analysis_service.py")
        # Find the format_for_whatsapp method
        func_start = source.find("def format_for_whatsapp(")
        assert func_start > 0
        # Get the method body (up to the next def at same indent level)
        next_def = source.find("\n    def ", func_start + 1)
        if next_def == -1:
            next_def = len(source)
        func_body = source[func_start:next_def]

        # Must NOT contain truncation logic
        assert "MAX_LENGTH = 1200" not in func_body, (
            "format_for_whatsapp still enforces MAX_LENGTH = 1200 — "
            "this SMS-era limit must be removed"
        )
        assert "_(קוצר)_" not in func_body, (
            "format_for_whatsapp still has truncation marker '_(קוצר)_'"
        )

    def test_no_1200_char_instruction_in_prompts(self):
        """Gemini prompts must NOT instruct to keep under 1200 chars."""
        source = _read_source("app/prompts.py")
        assert "under 1200 characters" not in source, (
            "prompts.py still tells Gemini to keep under 1200 characters"
        )

    def test_no_1500_char_instruction_in_expert_service(self):
        """Expert analysis service prompt must NOT limit to 1500 chars."""
        source = _read_source("app/services/expert_analysis_service.py")
        assert "under 1500 characters" not in source, (
            "DIRECT_AUDIO_SYSTEM_INSTRUCTION still limits to 1500 characters"
        )

    def test_no_summary_truncation_in_pipeline(self):
        """audio_pipeline.py must not truncate summary_text when sending."""
        source = _read_source("app/services/audio_pipeline.py")
        # The old truncation pattern: summary_text[:1000] + "..."
        # Should no longer exist in the WhatsApp sending section
        assert 'summary_text[:1000]' not in source, (
            "audio_pipeline.py still truncates summary_text at 1000 chars"
        )

    def test_format_for_whatsapp_has_no_truncation_code(self):
        """format_for_whatsapp must not contain any message truncation logic."""
        source = _read_source("app/services/expert_analysis_service.py")
        func_start = source.find("def format_for_whatsapp(")
        assert func_start > 0
        next_def = source.find("\n    def ", func_start + 1)
        if next_def == -1:
            next_def = len(source)
        func_body = source[func_start:next_def]

        # Must NOT contain slicing patterns that truncate text
        assert "message[:MAX_LENGTH" not in func_body, (
            "format_for_whatsapp still truncates message with message[:MAX_LENGTH...]"
        )
        assert "message[:1200" not in func_body, (
            "format_for_whatsapp still truncates message at 1200 chars"
        )
        assert "trimming to" not in func_body, (
            "format_for_whatsapp still has trimming logic"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Issue 3: ALL unknown speakers must get identification clips
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAllUnknownSpeakersGetClips:
    """Verify that speakers with short segments still get clips."""

    def test_identify_speakers_includes_short_segment_speakers(self):
        """identify_speakers must return ALL speakers, even those with
        segments too short for embedding extraction (< 2.0s)."""
        source = _read_source("app/services/pyannote_service.py")
        func_start = source.find("def identify_speakers(")
        assert func_start > 0
        func_body = source[func_start:]

        # Must include logic to handle speakers without embeddings
        assert "speakers_without_embeddings" in func_body, (
            "identify_speakers must handle speakers whose segments are "
            "too short for embedding extraction"
        )

    def test_short_segment_speakers_added_as_unknown(self):
        """Speakers without embeddings must be added with status='unknown'."""
        source = _read_source("app/services/pyannote_service.py")
        # Must add short-segment speakers with best_segment from diarization
        assert "no embedding" in source.lower() or "No embedding" in source, (
            "identify_speakers must document that some speakers have no embedding"
        )

    def test_clip_minimum_duration_lowered(self):
        """Clip extraction must accept segments as short as 0.5s (not 1.0s)."""
        source = _read_source("app/services/audio_pipeline.py")
        # Find the clip extraction section
        clip_section = source[source.find("DIRECT CLIP EXTRACTION"):]
        assert "< 0.5" in clip_section or "0.5s" in clip_section, (
            "Minimum clip duration should be 0.5s (was 1.0s)"
        )

    def test_pipeline_handles_none_embedding_in_clip(self):
        """Clip extraction must work even when embedding is None."""
        source = _read_source("app/services/audio_pipeline.py")
        # The _export_and_send_clip function must check for None embedding
        assert "embedding is not None" in source, (
            "Clip sending must handle embedding=None gracefully"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Issue 4: Inbox file must ALWAYS move to archive after processing
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestInboxFileAlwaysArchived:
    """Verify that Drive inbox files are moved to archive even if processing fails."""

    def test_archive_move_in_finally_block(self):
        """The archive move must happen in a finally block, not inside the try."""
        source = _read_source("process_meetings.py")
        func_start = source.find("def _process_inbox_file(")
        assert func_start > 0
        func_body = source[func_start:]

        # The archive move must be in the finally block
        finally_start = func_body.find("finally:")
        assert finally_start > 0, "No finally block in _process_inbox_file"

        finally_body = func_body[finally_start:]
        assert "archive_folder_id" in finally_body, (
            "Archive move must be in the finally block to ensure it ALWAYS runs"
        )

    def test_credentials_refreshed_before_archive_move(self):
        """Credentials must be refreshed before the archive move (processing may take 5+ min)."""
        source = _read_source("process_meetings.py")
        func_start = source.find("def _process_inbox_file(")
        func_body = source[func_start:]
        finally_body = func_body[func_body.find("finally:"):]

        assert "_refresh_credentials_if_needed" in finally_body, (
            "Must refresh Drive credentials before archive move — "
            "audio processing takes 5+ minutes, token may expire"
        )

    def test_rename_fallback_if_move_fails(self):
        """If the archive move fails, the file must be renamed to prevent re-processing."""
        source = _read_source("process_meetings.py")
        assert "[PROCESSED]" in source, (
            "Must rename file with [PROCESSED] prefix if archive move fails "
            "to prevent the inbox poller from re-processing it"
        )

    def test_processing_error_does_not_block_archive(self):
        """Even if process_audio_core throws an exception, the file must still be archived."""
        source = _read_source("process_meetings.py")
        func_start = source.find("def _process_inbox_file(")
        func_body = source[func_start:]

        # process_audio_core must be in a try block that doesn't re-raise
        # (so the finally block can execute the archive move)
        try_block_start = func_body.find("process_audio_core(")
        assert try_block_start > 0

        # There must be an except clause between process_audio_core and finally
        except_start = func_body.find("except", try_block_start)
        finally_start = func_body.find("finally:")
        assert except_start > 0 and except_start < finally_start, (
            "process_audio_core must be wrapped in try/except so errors "
            "don't prevent the archive move in the finally block"
        )
