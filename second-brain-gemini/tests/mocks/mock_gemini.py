"""
Mock Gemini Service — deterministic responses for testing.
"""
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock
import json


class MockGeminiResponse:
    """Mimics the Gemini API response object."""
    def __init__(self, text: str, tool_calls: list = None):
        self._text = text
        self.tool_calls = tool_calls or []

    @property
    def text(self):
        return self._text


class MockGeminiService:
    """Deterministic Gemini service for tests."""

    def __init__(self):
        self._responses: Dict[str, str] = {}
        self._call_log: List[Dict[str, Any]] = []
        self._default_response = "תשובה מהמערכת"

    def set_response(self, trigger: str, response: str):
        """Set a canned response for messages containing `trigger`."""
        self._responses[trigger.lower()] = response

    def set_default_response(self, response: str):
        self._default_response = response

    def analyze_day(self, **kwargs) -> dict:
        """Mock audio analysis."""
        self._call_log.append({"method": "analyze_day", "kwargs": kwargs})
        return {
            "transcript": "דובר 1: שלום, אני יובל.\nדובר 2: היי, אני חן.",
            "summary": "שיחה בין יובל וחן על פרויקט חדש.",
            "speakers": [
                {"id": "Speaker 1", "name": "Unknown Speaker 1"},
                {"id": "Speaker 2", "name": "Unknown Speaker 2"},
            ],
            "action_items": ["לסיים את הפרויקט עד סוף החודש"],
            "key_decisions": ["להתחיל עם MVP"],
        }

    def answer_history_query(self, **kwargs) -> str:
        self._call_log.append({"method": "answer_history_query", "kwargs": kwargs})
        return "מצאתי 3 שיחות שבהן הוזכר הנושא הזה."

    def generate_response(self, message: str, **kwargs) -> str:
        """Generic Gemini response — matches canned responses by trigger."""
        self._call_log.append({"method": "generate_response", "message": message})
        msg_lower = message.lower()
        for trigger, response in self._responses.items():
            if trigger in msg_lower:
                return response
        return self._default_response

    # ── Assertion helpers ────────────────────────────────────────
    def assert_called(self, method: str, times: int = None):
        calls = [c for c in self._call_log if c["method"] == method]
        if times is not None:
            assert len(calls) == times, (
                f"Expected {method} to be called {times} times, "
                f"but was called {len(calls)} times"
            )
        else:
            assert len(calls) > 0, f"Expected {method} to be called at least once"

    def get_calls(self, method: str) -> List[Dict[str, Any]]:
        return [c for c in self._call_log if c["method"] == method]

    def reset(self):
        self._call_log.clear()
        self._responses.clear()
