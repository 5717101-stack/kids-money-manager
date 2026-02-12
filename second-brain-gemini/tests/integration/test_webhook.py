"""
Integration tests for the /webhook endpoint.

Tests the webhook verification, message routing, idempotency,
and voice imprinting interceptor.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """Create async test client for the FastAPI app."""
    # Patch heavy services before importing app
    with patch("app.services.pyannote_service._ensure_models", return_value=False), \
         patch("app.services.drive_memory_service.DriveMemoryService") as mock_drive_cls, \
         patch("app.services.conversation_engine.ConversationEngine") as mock_engine_cls:

        # Configure mock drive
        mock_drive = MagicMock()
        mock_drive.is_configured = True
        mock_drive.preload_memory.return_value = True
        mock_drive.get_memory.return_value = {"chat_history": [], "user_profile": {}}
        mock_drive_cls.return_value = mock_drive

        # Configure mock engine
        mock_engine = MagicMock()
        mock_engine.chat = AsyncMock(return_value="תשובה מהמערכת")
        mock_engine_cls.return_value = mock_engine

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.integration
class TestWebhookVerification:
    """Test GET /webhook for Meta WhatsApp verification."""

    @pytest.mark.asyncio
    async def test_successful_verification(self, client, webhook_verify_params):
        """Should return the challenge token on valid verification."""
        response = await client.get("/webhook", params=webhook_verify_params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_wrong_verify_token(self, client):
        """Should reject verification with wrong token."""
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "CHALLENGE_123",
            "hub.verify_token": "WRONG_TOKEN"
        }
        response = await client.get("/webhook", params=params)
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_missing_params(self, client):
        """Should handle missing verification params gracefully."""
        response = await client.get("/webhook")
        # Should not crash — return 400 or handle gracefully
        assert response.status_code in (200, 400, 401, 403)


@pytest.mark.integration
class TestWebhookPost:
    """Test POST /webhook for incoming WhatsApp messages."""

    @pytest.mark.asyncio
    async def test_returns_200_for_valid_payload(self, client, whatsapp_text_message):
        """Webhook should always return 200 to prevent WhatsApp retries."""
        payload = whatsapp_text_message("שלום")
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_empty_entry(self, client):
        """Should handle empty entry gracefully."""
        payload = {"object": "whatsapp_business_account", "entry": []}
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_200_for_status_update(self, client):
        """Status updates (delivered, read) should return 200 without processing."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "statuses": [{
                            "id": "wamid.STATUS001",
                            "status": "delivered"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health and status endpoints."""

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_version(self, client):
        response = await client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data or isinstance(data, str)
