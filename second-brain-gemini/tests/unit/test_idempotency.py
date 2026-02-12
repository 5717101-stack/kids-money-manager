"""
Unit tests for message idempotency / deduplication.

The system must process each WhatsApp message exactly once,
even when webhooks are retried or sent to multiple instances.

NOTE: Requires full production dependencies (google-generativeai, etc.)
      because app.main imports everything at module level.
      Run in Docker/CI or with full venv installed.
"""
import pytest
from unittest.mock import patch

# Skip entire module if production deps not available
try:
    from app.main import (processed_message_ids, _processed_ids_lock,
                          _try_acquire_message_lock, mark_message_processed)
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS,
                                reason="Requires full production dependencies")


class TestMessageDedup:
    """Test the message deduplication mechanism."""

    @pytest.fixture(autouse=True)
    def setup(self):
        with _processed_ids_lock:
            processed_message_ids.clear()

    def test_first_message_accepted(self):
        """First occurrence of a message ID should be accepted."""
        assert _try_acquire_message_lock("wamid.DEDUP_001")

    def test_duplicate_message_rejected(self):
        """Second occurrence of the same message ID should be rejected."""
        assert _try_acquire_message_lock("wamid.DEDUP_002")
        assert not _try_acquire_message_lock("wamid.DEDUP_002")

    def test_different_messages_both_accepted(self):
        """Different message IDs should both be accepted."""
        assert _try_acquire_message_lock("wamid.DEDUP_A")
        assert _try_acquire_message_lock("wamid.DEDUP_B")

    def test_mark_message_processed(self):
        """mark_message_processed should prevent future processing."""
        mark_message_processed("wamid.DEDUP_MARK")
        assert not _try_acquire_message_lock("wamid.DEDUP_MARK")
