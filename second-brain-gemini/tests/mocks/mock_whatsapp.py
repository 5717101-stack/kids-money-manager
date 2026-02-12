"""
Mock WhatsApp provider — captures sent messages for assertion.
"""
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock
import uuid


class MockWhatsAppProvider:
    """Captures all WhatsApp messages for test assertions."""

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.sent_audio: List[Dict[str, Any]] = []
        self.is_configured_flag = True
        self._msg_counter = 0

    def _next_wamid(self) -> str:
        self._msg_counter += 1
        return f"wamid.MOCK{self._msg_counter:04d}"

    def send_whatsapp(self, message: str, to: str = "", **kwargs) -> Dict[str, Any]:
        wamid = self._next_wamid()
        entry = {"message": message, "to": to, "wamid": wamid, **kwargs}
        self.sent_messages.append(entry)
        return {"success": True, "message_id": wamid}

    def send_audio(self, audio_path: str, caption: str = "", to: str = "",
                   **kwargs) -> Dict[str, Any]:
        audio_wamid = self._next_wamid()
        caption_wamid = self._next_wamid() if caption else None
        entry = {
            "audio_path": audio_path,
            "caption": caption,
            "to": to,
            "audio_wamid": audio_wamid,
            "caption_wamid": caption_wamid,
        }
        self.sent_audio.append(entry)
        return {
            "success": True,
            "message_id": audio_wamid,
            "wam_id": audio_wamid,
            "caption_message_id": caption_wamid,
            "media_id": f"MEDIA_{self._msg_counter}",
        }

    def is_configured(self) -> bool:
        return self.is_configured_flag

    # ── Assertion helpers ────────────────────────────────────────
    def get_last_message(self) -> Optional[str]:
        return self.sent_messages[-1]["message"] if self.sent_messages else None

    def get_all_message_texts(self) -> List[str]:
        return [m["message"] for m in self.sent_messages]

    def find_message_containing(self, substring: str) -> Optional[Dict[str, Any]]:
        for m in self.sent_messages:
            if substring in m.get("message", ""):
                return m
        return None

    def assert_message_sent_containing(self, substring: str):
        match = self.find_message_containing(substring)
        assert match is not None, (
            f"Expected a WhatsApp message containing '{substring}', "
            f"but none found. Sent messages: {self.get_all_message_texts()}"
        )

    def assert_no_messages_sent(self):
        assert len(self.sent_messages) == 0, (
            f"Expected no messages, but {len(self.sent_messages)} were sent: "
            f"{self.get_all_message_texts()}"
        )

    def reset(self):
        self.sent_messages.clear()
        self.sent_audio.clear()
        self._msg_counter = 0
