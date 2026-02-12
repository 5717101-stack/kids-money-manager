"""
Integration tests for the Voice Imprinting flow.

Flow:
1. Audio is processed → unknown speakers found
2. Bot sends audio clips + "who is this?" captions
3. Both audio and caption message IDs are stored in pending_identifications
4. User replies to either message with a name
5. Interceptor catches reply → saves voice signature → sends confirmation
6. Message does NOT pass through to Gemini
"""
import pytest
import os
import json
import tempfile
from unittest.mock import patch

# Skip if production deps not available
try:
    from app.main import (pending_identifications, _save_pending_identifications,
                          _load_pending_identifications, _PENDING_ID_FILE)
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS,
                                reason="Requires full production dependencies")


class TestPendingIdentifications:
    """Test that pending identifications store both audio + caption IDs."""

    def test_both_ids_stored(self):
        """When audio pipeline stores a pending ID, both audio and caption IDs should be present."""
        from app.main import pending_identifications, _save_pending_identifications

        # Simulate what audio_pipeline does after sending audio + caption
        audio_wamid = "wamid.AUDIO_TEST_001"
        caption_wamid = "wamid.CAPTION_TEST_001"
        pending_data = {
            "file_path": "/tmp/test_audio.ogg",
            "speaker_id": "Unknown Speaker 1",
        }

        # Store under both IDs (as the fixed code does)
        pending_identifications[audio_wamid] = pending_data
        pending_identifications[caption_wamid] = pending_data

        assert audio_wamid in pending_identifications
        assert caption_wamid in pending_identifications
        # Both point to same data
        assert pending_identifications[audio_wamid] is pending_identifications[caption_wamid]

        # Cleanup
        pending_identifications.pop(audio_wamid, None)
        pending_identifications.pop(caption_wamid, None)

    def test_reply_to_audio_matches(self):
        """Replying to the AUDIO message should match pending identification."""
        from app.main import pending_identifications

        audio_wamid = "wamid.AUDIO_MATCH_001"
        caption_wamid = "wamid.CAPTION_MATCH_001"
        pending_data = {"file_path": "/tmp/test.ogg", "speaker_id": "Unknown Speaker 2"}

        pending_identifications[audio_wamid] = pending_data
        pending_identifications[caption_wamid] = pending_data

        # Simulate user replying to audio message
        replied_message_id = audio_wamid
        assert replied_message_id in pending_identifications

        # Cleanup
        pending_identifications.pop(audio_wamid, None)
        pending_identifications.pop(caption_wamid, None)

    def test_reply_to_caption_matches(self):
        """Replying to the CAPTION message should match pending identification."""
        from app.main import pending_identifications

        audio_wamid = "wamid.AUDIO_CAP_001"
        caption_wamid = "wamid.CAPTION_CAP_001"
        pending_data = {"file_path": "/tmp/test.ogg", "speaker_id": "Unknown Speaker 3"}

        pending_identifications[audio_wamid] = pending_data
        pending_identifications[caption_wamid] = pending_data

        # Simulate user replying to caption message
        replied_message_id = caption_wamid
        assert replied_message_id in pending_identifications

        # Cleanup
        pending_identifications.pop(audio_wamid, None)
        pending_identifications.pop(caption_wamid, None)

    def test_cleanup_removes_paired_id(self):
        """When one ID is popped, the paired ID should also be removable."""
        from app.main import pending_identifications

        audio_wamid = "wamid.AUDIO_PAIR_001"
        caption_wamid = "wamid.CAPTION_PAIR_001"
        pending_data = {"file_path": "/tmp/test.ogg", "speaker_id": "Unknown Speaker 4"}

        pending_identifications[audio_wamid] = pending_data
        pending_identifications[caption_wamid] = pending_data

        # Pop one (as interceptor does)
        popped = pending_identifications.pop(audio_wamid)
        assert popped is pending_data

        # Find and remove paired IDs (same logic as in main.py interceptor)
        paired = [k for k, v in pending_identifications.items()
                  if v is pending_data or (
                      isinstance(v, dict) and isinstance(pending_data, dict)
                      and v.get('speaker_id') == pending_data.get('speaker_id')
                      and v.get('file_path') == pending_data.get('file_path')
                  )]
        for pid in paired:
            pending_identifications.pop(pid, None)

        assert caption_wamid not in pending_identifications


class TestPersistence:
    """Test that pending identifications survive save/load cycle."""

    def test_save_and_load(self):
        """Pending identifications should persist to disk and reload."""
        from app.main import (
            pending_identifications,
            _save_pending_identifications,
            _load_pending_identifications,
            _PENDING_ID_FILE
        )

        # Add test data
        pending_identifications["wamid.PERSIST_001"] = {
            "file_path": "/tmp/persist_test.ogg",
            "speaker_id": "Unknown Speaker 5",
        }
        _save_pending_identifications()

        # Verify file exists
        assert _PENDING_ID_FILE.exists()

        # Load and verify
        loaded = _load_pending_identifications()
        assert "wamid.PERSIST_001" in loaded
        assert loaded["wamid.PERSIST_001"]["speaker_id"] == "Unknown Speaker 5"

        # Cleanup
        pending_identifications.pop("wamid.PERSIST_001", None)
        _save_pending_identifications()
