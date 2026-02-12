"""
Root conftest — shared fixtures for all test levels.

Environment is configured BEFORE any app imports to prevent
real API calls during tests.
"""
import os
import sys
import json
import pytest

# ── Set test environment BEFORE any app imports ──────────────────────────────
os.environ.setdefault("GOOGLE_API_KEY", "test-fake-key")
os.environ.setdefault("WHATSAPP_CLOUD_API_TOKEN", "test-fake-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "000000000")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("DRIVE_MEMORY_FOLDER_ID", "test-folder-id")
os.environ.setdefault("CONTEXT_FOLDER_ID", "test-context-folder-id")
os.environ.setdefault("HUGGINGFACE_TOKEN", "hf-test-token")
os.environ.setdefault("MY_PHONE_NUMBER", "972501234567")
os.environ.setdefault("SERPAPI_KEY", "test-serpapi-key")

# Ensure app directory is on sys.path
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


# ── Fixtures: WhatsApp webhook payloads ──────────────────────────────────────

@pytest.fixture
def whatsapp_text_message():
    """Standard text message webhook payload."""
    def _make(body: str, from_number: str = "972501234567", message_id: str = "wamid.TEST001"):
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BIZ_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "972509999999",
                            "phone_number_id": "000000000"
                        },
                        "messages": [{
                            "from": from_number,
                            "id": message_id,
                            "timestamp": "1707700000",
                            "type": "text",
                            "text": {"body": body}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
    return _make


@pytest.fixture
def whatsapp_reply_message():
    """Reply to a specific message (used for voice imprinting)."""
    def _make(body: str, reply_to_id: str, from_number: str = "972501234567",
              message_id: str = "wamid.REPLY001"):
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BIZ_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "972509999999",
                            "phone_number_id": "000000000"
                        },
                        "messages": [{
                            "from": from_number,
                            "id": message_id,
                            "timestamp": "1707700100",
                            "type": "text",
                            "text": {"body": body},
                            "context": {"id": reply_to_id}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
    return _make


@pytest.fixture
def whatsapp_audio_message():
    """Audio message webhook payload."""
    def _make(media_id: str = "MEDIA_123", from_number: str = "972501234567",
              message_id: str = "wamid.AUDIO001"):
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "BIZ_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "972509999999",
                            "phone_number_id": "000000000"
                        },
                        "messages": [{
                            "from": from_number,
                            "id": message_id,
                            "timestamp": "1707700000",
                            "type": "audio",
                            "audio": {"id": media_id, "mime_type": "audio/ogg"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
    return _make


@pytest.fixture
def webhook_verify_params():
    """Query parameters for webhook verification (GET /webhook)."""
    return {
        "hub.mode": "subscribe",
        "hub.challenge": "CHALLENGE_TOKEN_12345",
        "hub.verify_token": "test-verify-token"
    }


# ── Fixtures: Knowledge Base data ────────────────────────────────────────────

@pytest.fixture
def sample_kb_identity_graph():
    """A minimal identity graph for testing search_people and name resolution."""
    return {
        "Yuval Laikin": {
            "canonical_name": "Yuval Laikin",
            "hebrew_name": "יובל לייקין",
            "role": "VP R&D",
            "department": "Engineering",
            "reports_to": "CEO",
            "direct_reports": ["Chen Katz", "Noam Cohen"],
        },
        "Chen Katz": {
            "canonical_name": "Chen Katz",
            "hebrew_name": "חן כץ",
            "role": "Team Lead",
            "department": "Engineering",
            "reports_to": "Yuval Laikin",
        },
        "Noam Cohen": {
            "canonical_name": "Noam Cohen",
            "hebrew_name": "נועם כהן",
            "role": "Market Success Lead",
            "department": "Marketing",
            "reports_to": "Yuval Laikin",
            "direct_reports": ["Bar Rimon", "Moti Michael"],
        },
    }


@pytest.fixture
def sample_name_map():
    """Name map for testing Hebrew → English name resolution."""
    return {
        "yuval": "Yuval Laikin",
        "yuval laikin": "Yuval Laikin",
        "יובל": "Yuval Laikin",
        "יובל לייקין": "Yuval Laikin",
        "chen": "Chen Katz",
        "chen katz": "Chen Katz",
        "חן": "Chen Katz",
        "חן כץ": "Chen Katz",
        "noam": "Noam Cohen",
        "noam cohen": "Noam Cohen",
        "נועם": "Noam Cohen",
        "נועם כהן": "Noam Cohen",
    }


# ── Fixtures: Drive API responses ────────────────────────────────────────────

@pytest.fixture
def drive_upload_response():
    """Successful Drive file upload response."""
    return {
        "id": "FILE_ID_123",
        "webContentLink": "https://drive.google.com/uc?id=FILE_ID_123",
        "webViewLink": "https://drive.google.com/file/d/FILE_ID_123/view",
    }


@pytest.fixture
def drive_list_files_response():
    """Drive list files response."""
    return {
        "files": [
            {"id": "FILE_1", "name": "transcript_2026-02-12.json", "modifiedTime": "2026-02-12T10:00:00Z"},
            {"id": "FILE_2", "name": "transcript_2026-02-11.json", "modifiedTime": "2026-02-11T10:00:00Z"},
        ]
    }
