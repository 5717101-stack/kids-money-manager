"""
Unit tests for the SSL retry decorator on Drive service.

Verifies that transient SSL errors are retried and eventually succeed.
"""
import ssl
import sys
import pytest
from unittest.mock import MagicMock, patch, call

# Create a real HttpError stand-in that inherits from Exception
class _FakeHttpError(Exception):
    def __init__(self, resp=None, content=b""):
        self.resp = resp or MagicMock(status=500)
        self.content = content
        super().__init__(str(resp))

# Build mock modules for heavy Google dependencies
_mock_errors = MagicMock()
_mock_errors.HttpError = _FakeHttpError

for mod in ["google", "google.oauth2", "google.oauth2.credentials",
            "google.auth", "google.auth.transport", "google.auth.transport.requests",
            "googleapiclient", "googleapiclient.discovery", "googleapiclient.http",
            "googleapiclient._helpers",
            "dateutil", "dateutil.parser"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Set HttpError to our real exception subclass
sys.modules["googleapiclient.errors"] = _mock_errors

from app.services.drive_memory_service import _retry_on_ssl


class TestRetryDecorator:
    """Test the _retry_on_ssl decorator."""

    def test_succeeds_first_try(self):
        """Should return immediately on success."""
        @_retry_on_ssl(max_retries=3, base_delay=0.01)
        def always_works():
            return "ok"

        assert always_works() == "ok"

    def test_retries_on_ssl_error(self):
        """Should retry on SSLError and eventually succeed."""
        call_count = 0

        @_retry_on_ssl(max_retries=3, base_delay=0.01)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number")
            return "ok"

        result = fails_twice()
        assert result == "ok"
        assert call_count == 3  # 2 failures + 1 success

    def test_raises_after_max_retries(self):
        """Should raise the last exception after exhausting retries."""
        @_retry_on_ssl(max_retries=2, base_delay=0.01)
        def always_fails():
            raise ssl.SSLError("persistent error")

        with pytest.raises(ssl.SSLError):
            always_fails()

    def test_retries_on_connection_error(self):
        """Should retry on ConnectionError."""
        call_count = 0

        @_retry_on_ssl(max_retries=3, base_delay=0.01)
        def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionResetError("reset")
            return "ok"

        assert fails_once() == "ok"
        assert call_count == 2

    def test_does_not_retry_value_error(self):
        """Should NOT retry on non-network errors like ValueError."""
        @_retry_on_ssl(max_retries=3, base_delay=0.01)
        def bad_value():
            raise ValueError("not a network error")

        with pytest.raises(ValueError):
            bad_value()

    def test_preserves_function_name(self):
        """Decorator should preserve the wrapped function's name."""
        @_retry_on_ssl(max_retries=3, base_delay=0.01)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
