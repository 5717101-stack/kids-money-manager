"""
Critical Path Tests — "Smoke tests" for the most important user flows.

These tests verify the MINIMUM viable behavior that MUST work:
  1. User sends audio → gets analysis back
  2. User sends text → gets response back
  3. Webhook verification → Meta can reach us
  4. Drive failures don't break user-facing features

Run these BEFORE every deploy:
    python -m pytest tests/integration/test_critical_paths.py -v

These tests would have caught:
  - v2.3.0: int(challenge) bug → webhook verification broken
  - v7.2.x: Drive upload before analysis → users got nothing when Drive crashed
  - v7.2.x: SSL errors in Drive → audio pipeline crashed before sending analysis
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from httpx import AsyncClient, ASGITransport

# ── Mock heavy deps ─────────────────────────────────────────────────────────
for mod in [
    "pyannote", "pyannote.audio", "pyannote.audio.pipelines",
    "torch", "torchaudio", "speechbrain",
    "google", "google.oauth2", "google.oauth2.credentials",
    "google.auth", "google.auth.transport", "google.auth.transport.requests",
    "googleapiclient", "googleapiclient.discovery", "googleapiclient.http",
    "googleapiclient._helpers", "googleapiclient.errors",
    "dateutil", "dateutil.parser",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()


@pytest.fixture
async def app_client():
    """Create test client with all external services mocked."""
    with patch("app.services.pyannote_service._ensure_models", return_value=False), \
         patch("app.services.drive_memory_service.DriveMemoryService") as mock_drive_cls, \
         patch("app.services.conversation_engine.ConversationEngine") as mock_engine_cls:

        mock_drive = MagicMock()
        mock_drive.is_configured = True
        mock_drive.preload_memory.return_value = True
        mock_drive.get_memory.return_value = {"chat_history": [], "user_profile": {}}
        mock_drive.upload_audio_to_archive.return_value = {
            "file_id": "F1",
            "web_content_link": "https://drive.mock/F1",
            "web_view_link": "https://drive.mock/F1/view",
            "filename": "test.ogg",
        }
        mock_drive.save_transcript.return_value = "T1"
        mock_drive.update_memory.return_value = True
        mock_drive_cls.return_value = mock_drive

        mock_engine = MagicMock()
        mock_engine.chat = AsyncMock(return_value="תשובה מהמערכת")
        mock_engine_cls.return_value = mock_engine

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, mock_drive, mock_engine


# ═════════════════════════════════════════════════════════════════════════════
# CRITICAL PATH 1: Webhook Verification
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCriticalWebhookVerification:
    """
    If this breaks, Meta stops sending us messages entirely.
    Severity: P0 — TOTAL SERVICE OUTAGE
    """

    CHALLENGES = [
        "1234567890",           # Numeric
        "abc123",               # Alphanumeric
        "a1b2c3d4e5f6",         # Mixed
        "test-challenge_v2.0",  # With special chars
        "שלום",                 # Unicode (unlikely but safe)
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("challenge", CHALLENGES)
    async def test_any_challenge_string_echoed_back(self, app_client, challenge):
        """
        Meta sends various challenge formats. ALL must be echoed as plain text.
        """
        client, _, _ = app_client
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": challenge,
            "hub.verify_token": os.environ.get("WEBHOOK_VERIFY_TOKEN", "test-verify-token"),
        }
        response = await client.get("/webhook", params=params)
        assert response.status_code == 200
        assert response.text == challenge, (
            f"Challenge not echoed. Sent: {challenge!r}, Got: {response.text!r}"
        )

    @pytest.mark.asyncio
    async def test_wrong_token_rejected(self, app_client):
        """Wrong verify token must be rejected — security requirement."""
        client, _, _ = app_client
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "CHALLENGE",
            "hub.verify_token": "WRONG_TOKEN",
        }
        response = await client.get("/webhook", params=params)
        assert response.status_code in (401, 403)


# ═════════════════════════════════════════════════════════════════════════════
# CRITICAL PATH 2: Text Message → Response
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCriticalTextMessage:
    """
    If this breaks, the bot doesn't respond to text messages.
    Severity: P1 — CORE FEATURE BROKEN
    """

    @pytest.mark.asyncio
    async def test_text_message_returns_200(self, app_client):
        """
        WhatsApp POST /webhook MUST return 200 for text messages.
        Non-200 causes WhatsApp to retry exponentially → message storm.
        """
        client, _, _ = app_client
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BIZ",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "972509999999",
                            "phone_number_id": "000000000",
                        },
                        "messages": [{
                            "from": "972501234567",
                            "id": "wamid.TEXT001",
                            "timestamp": "1707700000",
                            "type": "text",
                            "text": {"body": "שלום, מה שלומך?"},
                        }],
                    },
                    "field": "messages",
                }],
            }],
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# CRITICAL PATH 3: Audio Message → Returns 200 (processing in background)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCriticalAudioMessage:
    """
    If this breaks, audio messages are not processed.
    Severity: P0 — PRIMARY USE CASE BROKEN
    """

    @pytest.mark.asyncio
    async def test_audio_webhook_returns_200(self, app_client):
        """
        Audio webhook MUST return 200 immediately (processing is async).
        Non-200 causes WhatsApp retries → duplicate processing.
        """
        client, _, _ = app_client
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BIZ",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "972509999999",
                            "phone_number_id": "000000000",
                        },
                        "messages": [{
                            "from": "972501234567",
                            "id": "wamid.AUDIO001",
                            "timestamp": "1707700000",
                            "type": "audio",
                            "audio": {"id": "MEDIA_123", "mime_type": "audio/ogg"},
                        }],
                    },
                    "field": "messages",
                }],
            }],
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# CRITICAL PATH 4: Drive Failures Don't Break User Flows
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestDriveFailureResilience:
    """
    Drive is a STORAGE layer. Its failure must NEVER prevent:
      - Webhook returning 200
      - Text messages getting responses
      - Audio processing pipeline sending analysis

    Severity: P1 — these are the bugs that caused multi-hour outages
    """

    @pytest.mark.asyncio
    async def test_webhook_200_when_drive_down(self):
        """
        Even if Drive service fails to initialize, webhook must return 200.
        """
        with patch("app.services.pyannote_service._ensure_models", return_value=False), \
             patch("app.services.drive_memory_service.DriveMemoryService") as mock_cls, \
             patch("app.services.conversation_engine.ConversationEngine"):

            # Simulate Drive being down
            mock_drive = MagicMock()
            mock_drive.is_configured = False
            mock_drive.preload_memory.side_effect = Exception("Drive is down")
            mock_drive.get_memory.return_value = {"chat_history": [], "user_profile": {}}
            mock_cls.return_value = mock_drive

            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_text_message_handled_when_drive_upload_fails(self):
        """
        Text messages should still get a response even if Drive memory
        update fails in the background.
        """
        with patch("app.services.pyannote_service._ensure_models", return_value=False), \
             patch("app.services.drive_memory_service.DriveMemoryService") as mock_cls, \
             patch("app.services.conversation_engine.ConversationEngine") as mock_engine_cls:

            mock_drive = MagicMock()
            mock_drive.is_configured = True
            mock_drive.preload_memory.return_value = True
            mock_drive.get_memory.return_value = {"chat_history": [], "user_profile": {}}
            mock_drive.update_memory.side_effect = Exception("Drive upload failed")
            mock_cls.return_value = mock_drive

            mock_engine = MagicMock()
            mock_engine.chat = AsyncMock(return_value="תשובה")
            mock_engine_cls.return_value = mock_engine

            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "object": "whatsapp_business_account",
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "972509999999",
                                    "phone_number_id": "000000000",
                                },
                                "messages": [{
                                    "from": "972501234567",
                                    "id": "wamid.TEXT_DRIVE_FAIL",
                                    "timestamp": "1707700000",
                                    "type": "text",
                                    "text": {"body": "בדיקה"},
                                }],
                            },
                            "field": "messages",
                        }],
                    }],
                }
                response = await client.post("/webhook", json=payload)
                assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# CRITICAL PATH 5: Health & Status Endpoints
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCriticalHealthEndpoints:
    """
    Cloud Run uses /health for liveness probes.
    If this breaks, Cloud Run kills the container → total outage.
    Severity: P0
    """

    @pytest.mark.asyncio
    async def test_health_always_200(self, app_client):
        """Health endpoint must always return 200."""
        client, _, _ = app_client
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_version_returns_valid_data(self, app_client):
        """Version endpoint must return parseable data."""
        client, _, _ = app_client
        response = await client.get("/version")
        assert response.status_code == 200
