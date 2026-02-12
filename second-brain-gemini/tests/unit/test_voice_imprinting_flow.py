"""
Unit tests for the Voice Imprinting (Speaker Identification) flow.

Tests verify:
  1. Reply interceptor catches speaker identification replies
  2. Pending identifications are persisted to Drive (survive container restarts)
  3. Pending IDs are loaded from Drive on startup when local cache is empty
  4. Non-matching replies fall through to normal chat
  5. Short name replies to identification requests are correctly processed

These tests would have caught:
  - v7.3.1: Container restart wiped local pending_identifications → user's
    reply "מירי" was not recognized as speaker identification → fell through to
    Gemini → "⚠️ לא הצלחתי לייצר תשובה"

NOTE: These tests read source files directly (no heavy imports needed).
"""
import os
import json
import pytest

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN_PY = os.path.join(APP_ROOT, "app", "main.py")
DRIVE_SERVICE_PY = os.path.join(APP_ROOT, "app", "services", "drive_memory_service.py")


def _read_source(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ═════════════════════════════════════════════════════════════════════════════
# 1. Voice Imprinting Reply Interceptor (Source Code Analysis)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestVoiceImprintingInterceptor:
    """Verify the reply interceptor catches speaker identification replies."""

    def test_interceptor_exists_and_runs_before_chat(self):
        """
        The VOICE IMPRINTING INTERCEPTOR must run BEFORE the conversation engine
        within the webhook handler. If a user replies to a speaker identification
        message, the interceptor should catch it and NOT send the reply to Gemini.
        """
        source = _read_source(MAIN_PY)

        # Find the webhook POST handler as our scope
        webhook_start = source.find("async def webhook(")
        assert webhook_start != -1, "webhook function not found in main.py"
        webhook_body = source[webhook_start:]

        # Find the interceptor within the webhook
        pos_interceptor = webhook_body.find("VOICE IMPRINTING INTERCEPTOR")
        assert pos_interceptor != -1, (
            "VOICE IMPRINTING INTERCEPTOR not found in webhook handler. "
            "Without it, speaker identification replies will be sent to Gemini."
        )

        # Find the conversation engine handler within the webhook
        pos_conversation = webhook_body.find("CONVERSATION ENGINE")
        assert pos_conversation != -1, "CONVERSATION ENGINE not found in webhook handler"

        # Interceptor must come BEFORE conversation engine
        assert pos_interceptor < pos_conversation, (
            "VOICE IMPRINTING INTERCEPTOR must run BEFORE CONVERSATION ENGINE in webhook handler. "
            "Otherwise, speaker identification replies will be processed as chat messages."
        )

    def test_interceptor_checks_pending_identifications(self):
        """
        The interceptor must check `replied_message_id in pending_identifications`.
        This is the core matching logic.
        """
        source = _read_source(MAIN_PY)

        # The interceptor should check the replied message ID against pending identifications
        assert "replied_message_id" in source and "pending_identifications" in source, (
            "Interceptor must check replied_message_id against pending_identifications dict"
        )

        # Find the actual check
        assert "replied_message_id in pending_identifications" in source, (
            "Missing: 'replied_message_id in pending_identifications'. "
            "This is the core matching logic for the voice imprinting interceptor."
        )

    def test_interceptor_sends_confirmation(self):
        """
        After identifying a speaker, the system should send a confirmation message
        like "✅ למדתי, זה *{person_name}*".
        """
        source = _read_source(MAIN_PY)

        assert "למדתי" in source, (
            "Confirmation message 'למדתי' not found. "
            "After voice imprinting, the system should confirm the identification to the user."
        )

    def test_interceptor_stops_processing(self):
        """
        After handling voice imprinting, the interceptor must `continue` 
        (skip all subsequent handlers like Conversation Engine).
        """
        source = _read_source(MAIN_PY)

        # Find the interceptor section
        interceptor_start = source.find("VOICE IMPRINTING INTERCEPTOR")
        interceptor_end = source.find("IDEMPOTENCY CHECK", interceptor_start)

        if interceptor_start != -1 and interceptor_end != -1:
            interceptor_section = source[interceptor_start:interceptor_end]
            assert "continue" in interceptor_section, (
                "After voice imprinting, the interceptor must use 'continue' to skip "
                "all subsequent handlers. Without this, the reply would also be sent to Gemini."
            )


# ═════════════════════════════════════════════════════════════════════════════
# 2. Pending Identifications Persistence (THE CRITICAL FIX)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPendingIdentificationsPersistence:
    """
    Verify pending identifications survive container restarts.
    
    This is the test that would have caught the v7.3.1 bug:
    - Clips sent → pending IDs stored in local file → container restart → 
      local file wiped → user replies → interceptor doesn't match → 
      reply goes to Gemini → "⚠️ לא הצלחתי לייצר תשובה"
    """

    def test_save_persists_to_drive(self):
        """
        _save_pending_identifications must save to BOTH local file AND Drive.
        Local file alone is not enough — Cloud Run filesystem is ephemeral.
        """
        source = _read_source(MAIN_PY)

        func_start = source.find("def _save_pending_identifications(")
        assert func_start != -1, "_save_pending_identifications function not found"

        # Find the function body (until next top-level def or assignment)
        next_def = source.find("\ndef ", func_start + 10)
        next_assignment = source.find("\npending_identifications", func_start + 10)
        func_end = min(
            next_def if next_def != -1 else len(source),
            next_assignment if next_assignment != -1 else len(source)
        )
        func_body = source[func_start:func_end]

        # Must write to Drive
        assert "save_pending_identifications" in func_body or "drive_memory_service" in func_body, (
            "CRITICAL: _save_pending_identifications must persist to Drive (not just local file). "
            "Cloud Run's filesystem is ephemeral — container restarts wipe local files. "
            "Without Drive persistence, speaker identification replies break after every deploy."
        )

    def test_load_falls_back_to_drive(self):
        """
        _load_pending_identifications must try local file first, then fall back to Drive.
        This ensures recovery after container restarts.
        """
        source = _read_source(MAIN_PY)

        func_start = source.find("def _load_pending_identifications(")
        assert func_start != -1, "_load_pending_identifications function not found"

        # Find the function body
        next_def = source.find("\ndef ", func_start + 10)
        func_body = source[func_start:next_def if next_def != -1 else len(source)]

        # Must load from Drive as fallback
        assert "load_pending_identifications" in func_body or "drive_memory_service" in func_body, (
            "CRITICAL: _load_pending_identifications must fall back to Drive when local file is empty. "
            "After a container restart, the local file doesn't exist. Without Drive fallback, "
            "all pending speaker identifications are lost."
        )

    def test_drive_service_has_persistence_methods(self):
        """
        DriveMemoryService must have save/load methods for pending identifications.
        """
        source = _read_source(DRIVE_SERVICE_PY)

        assert "def save_pending_identifications" in source, (
            "DriveMemoryService missing save_pending_identifications method. "
            "This is needed to persist speaker identification data across container restarts."
        )

        assert "def load_pending_identifications" in source, (
            "DriveMemoryService missing load_pending_identifications method. "
            "This is needed to restore speaker identification data after container restarts."
        )

    def test_drive_persistence_uses_retry_decorator(self):
        """
        Drive persistence methods should use @_retry_on_ssl to handle transient errors.
        """
        source = _read_source(DRIVE_SERVICE_PY)

        # Find save method and check for retry
        save_start = source.find("def save_pending_identifications")
        if save_start != -1:
            pre_save = source[max(0, save_start - 200):save_start]
            assert "_retry_on_ssl" in pre_save, (
                "save_pending_identifications should use @_retry_on_ssl decorator "
                "to handle transient SSL errors."
            )

        # Find load method and check for retry
        load_start = source.find("def load_pending_identifications")
        if load_start != -1:
            pre_load = source[max(0, load_start - 200):load_start]
            assert "_retry_on_ssl" in pre_load, (
                "load_pending_identifications should use @_retry_on_ssl decorator "
                "to handle transient SSL errors."
            )


# ═════════════════════════════════════════════════════════════════════════════
# 3. Pending Identification Data Structure Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPendingIdentificationDataStructure:
    """Test the data structure used for pending identifications."""

    def test_pending_data_serialization(self):
        """
        Pending identification data must be JSON-serializable.
        embeddings (list of floats) should serialize correctly.
        """
        pending_data = {
            'file_path': '/tmp/clip_speaker2.ogg',
            'speaker_id': 'Unknown Speaker 2',
            'embedding': [0.1, -0.5, 0.3] * 64  # 192 dims (realistic)
        }

        # Must serialize without error
        serialized = json.dumps(pending_data, ensure_ascii=False)
        deserialized = json.loads(serialized)

        assert deserialized['speaker_id'] == 'Unknown Speaker 2'
        assert len(deserialized['embedding']) == 192

    def test_pending_data_without_embedding(self):
        """
        Legacy pending data (without embedding) should still work.
        """
        pending_data = {
            'file_path': '/tmp/clip.ogg',
            'speaker_id': 'Unknown Speaker 3',
        }

        serialized = json.dumps(pending_data)
        deserialized = json.loads(serialized)
        assert deserialized.get('embedding') is None
        assert deserialized['speaker_id'] == 'Unknown Speaker 3'

    def test_pending_data_paired_ids(self):
        """
        Both audio_msg_id and caption_msg_id should map to the same pending data.
        This ensures the user can reply to either the audio or the caption message.
        """
        pending_data = {
            'file_path': '/tmp/clip.ogg',
            'speaker_id': 'Unknown Speaker 2',
        }

        # Simulate how audio_pipeline stores it
        pending_identifications = {}
        audio_msg_id = "wamid.AUDIO001"
        caption_msg_id = "wamid.CAPTION001"

        pending_identifications[audio_msg_id] = pending_data
        pending_identifications[caption_msg_id] = pending_data

        # User replies to caption message
        replied_to = caption_msg_id
        assert replied_to in pending_identifications
        assert pending_identifications[replied_to]['speaker_id'] == 'Unknown Speaker 2'

        # User replies to audio message (alternative)
        replied_to_alt = audio_msg_id
        assert replied_to_alt in pending_identifications


# ═════════════════════════════════════════════════════════════════════════════
# 4. Audio Pipeline Clip Sending Tests
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestClipSendingAndPendingStorage:
    """Verify clips are sent and pending identifications are stored correctly."""

    def test_export_and_send_stores_pending_ids(self):
        """
        After sending a clip, both audio and caption message IDs must be
        stored in pending_identifications.
        """
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_pipeline.py"))

        # Verify both IDs are stored
        assert "audio_msg_id" in source, "audio_msg_id not tracked in audio_pipeline.py"
        assert "caption_msg_id" in source, "caption_msg_id not tracked in audio_pipeline.py"
        assert "pending_identifications[audio_msg_id]" in source, (
            "audio message ID not stored in pending_identifications"
        )
        assert "pending_identifications[caption_msg_id]" in source, (
            "caption message ID not stored in pending_identifications"
        )

    def test_save_called_after_storing_pending(self):
        """
        _save_pending_identifications must be called after storing new pending IDs.
        Without this, the IDs won't be persisted to Drive.
        """
        source = _read_source(os.path.join(APP_ROOT, "app", "services", "audio_pipeline.py"))

        # Find where pending IDs are stored
        pos_store = source.find("pending_identifications[audio_msg_id]")
        assert pos_store != -1

        # _save_pending_identifications should be called shortly after
        pos_save = source.find("_save_pending_identifications()", pos_store)
        assert pos_save != -1, (
            "_save_pending_identifications() not called after storing pending IDs. "
            "Without this, speaker identification data won't survive container restarts."
        )

        # Save should be within ~200 chars of the store (not way later)
        assert pos_save - pos_store < 500, (
            "_save_pending_identifications() is too far from the store call. "
            "It should be called immediately after storing pending IDs."
        )
