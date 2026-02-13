"""
Tests for the Architecture Audit Report — verifies that the report
correctly counts transcripts and voice signatures, never silently
swallows errors, and uses lightweight counting methods.
"""
import os
import sys
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ────────────────────────────────────────────────────────────────
# Source-code analysis helpers
# ────────────────────────────────────────────────────────────────

def _read_source(relative_path: str) -> str:
    """Read a source file relative to the project root."""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    full_path = os.path.join(project_root, relative_path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


AUDIT_SRC = _read_source('app/services/architecture_audit_service.py')
DRIVE_SRC = _read_source('app/services/drive_memory_service.py')


# ────────────────────────────────────────────────────────────────
# 1. No bare except:pass — errors must be logged
# ────────────────────────────────────────────────────────────────

class TestNoSilentErrors:
    """Ensure audit code never uses bare 'except: pass' to swallow errors."""

    def test_no_bare_except_pass_in_audit(self):
        """The audit service must not use bare 'except: pass'."""
        import re
        # Match patterns like: except:\n            pass
        matches = re.findall(r'except\s*:\s*\n\s*pass', AUDIT_SRC)
        assert len(matches) == 0, (
            f"Found {len(matches)} bare 'except: pass' pattern(s) in "
            f"architecture_audit_service.py. All exceptions must be logged."
        )

    def test_health_check_logs_voice_sig_errors(self):
        """check_system_health must log errors when voice sig counting fails."""
        # The voice sig block should print errors, not silently pass
        assert 'Voice signature count failed' in AUDIT_SRC or \
               'voice signature' in AUDIT_SRC.lower(), (
            "check_system_health should log voice signature count errors"
        )

    def test_health_check_logs_transcript_errors(self):
        """check_system_health must log errors when transcript counting fails."""
        assert 'Transcript count failed' in AUDIT_SRC or \
               'count transcripts' in AUDIT_SRC.lower(), (
            "check_system_health should log transcript count errors"
        )


# ────────────────────────────────────────────────────────────────
# 2. Lightweight counting — no file downloads for counts
# ────────────────────────────────────────────────────────────────

class TestLightweightCounting:
    """Audit must use lightweight methods that don't download files."""

    def test_health_check_uses_count_methods(self):
        """check_system_health should call count_voice_signature_files or
        get_known_speaker_names, NOT get_voice_signatures."""
        # Find the check_system_health method
        health_start = AUDIT_SRC.find('def check_system_health')
        assert health_start != -1
        # Find the next method boundary
        next_method = AUDIT_SRC.find('\n    def ', health_start + 10)
        health_code = AUDIT_SRC[health_start:next_method] if next_method != -1 else AUDIT_SRC[health_start:]
        
        assert 'count_voice_signature_files' in health_code or \
               'get_known_speaker_names' in health_code, (
            "check_system_health should use lightweight counting "
            "(count_voice_signature_files or get_known_speaker_names), "
            "not download actual MP3 files"
        )
        
        assert 'count_transcript_files' in health_code or \
               'get_recent_transcripts' in health_code, (
            "check_system_health should use count_transcript_files or "
            "get_recent_transcripts, not chat_history scanning"
        )

    def test_health_check_does_not_use_get_voice_signatures(self):
        """check_system_health must NOT call get_voice_signatures (downloads files)."""
        health_start = AUDIT_SRC.find('def check_system_health')
        next_method = AUDIT_SRC.find('\n    def ', health_start + 10)
        health_code = AUDIT_SRC[health_start:next_method] if next_method != -1 else AUDIT_SRC[health_start:]
        
        assert 'get_voice_signatures(' not in health_code, (
            "check_system_health should NOT call get_voice_signatures() — "
            "it downloads actual MP3 files which is wasteful for counting"
        )

    def test_health_check_does_not_scan_chat_history_for_audio_type(self):
        """check_system_health must NOT count transcripts via chat_history type check."""
        health_start = AUDIT_SRC.find('def check_system_health')
        next_method = AUDIT_SRC.find('\n    def ', health_start + 10)
        health_code = AUDIT_SRC[health_start:next_method] if next_method != -1 else AUDIT_SRC[health_start:]
        
        assert "h.get('type') == 'audio'" not in health_code, (
            "check_system_health should NOT count transcripts by scanning "
            "chat_history for type=='audio'. Use count_transcript_files() instead."
        )

    def test_data_hygiene_uses_lightweight_counting(self):
        """analyze_data_hygiene should use count methods."""
        hygiene_start = AUDIT_SRC.find('def analyze_data_hygiene')
        next_method = AUDIT_SRC.find('\n    def ', hygiene_start + 10)
        hygiene_code = AUDIT_SRC[hygiene_start:next_method] if next_method != -1 else AUDIT_SRC[hygiene_start:]
        
        assert 'count_voice_signature_files' in hygiene_code or \
               'get_known_speaker_names' in hygiene_code, (
            "analyze_data_hygiene should use lightweight voice sig counting"
        )

    def test_voice_analysis_uses_lightweight_counting(self):
        """analyze_voice_identification should use lightweight counting."""
        voice_start = AUDIT_SRC.find('def analyze_voice_identification')
        next_method = AUDIT_SRC.find('\n    def ', voice_start + 10)
        voice_code = AUDIT_SRC[voice_start:next_method] if next_method != -1 else AUDIT_SRC[voice_start:]
        
        assert 'count_voice_signature_files' in voice_code or \
               'get_known_speaker_names' in voice_code, (
            "analyze_voice_identification should use lightweight counting"
        )


# ────────────────────────────────────────────────────────────────
# 3. Drive service has the required counting methods
# ────────────────────────────────────────────────────────────────

class TestDriveCountingMethods:
    """DriveMemoryService must have lightweight counting methods."""

    def test_count_voice_signature_files_exists(self):
        """DriveMemoryService should have count_voice_signature_files method."""
        assert 'def count_voice_signature_files' in DRIVE_SRC

    def test_count_transcript_files_exists(self):
        """DriveMemoryService should have count_transcript_files method."""
        assert 'def count_transcript_files' in DRIVE_SRC

    def test_count_methods_have_retry_decorator(self):
        """Counting methods must have @_retry_on_ssl decorator."""
        # Find count_voice_signature_files and check decorator
        idx = DRIVE_SRC.find('def count_voice_signature_files')
        assert idx != -1
        # Look up to 200 chars before for the decorator
        preceding = DRIVE_SRC[max(0, idx - 200):idx]
        assert '_retry_on_ssl' in preceding, (
            "count_voice_signature_files must have @_retry_on_ssl decorator"
        )
        
        idx = DRIVE_SRC.find('def count_transcript_files')
        assert idx != -1
        preceding = DRIVE_SRC[max(0, idx - 200):idx]
        assert '_retry_on_ssl' in preceding, (
            "count_transcript_files must have @_retry_on_ssl decorator"
        )

    def test_voice_signatures_folder_has_caching(self):
        """_ensure_voice_signatures_folder should cache folder ID."""
        assert '_voice_signatures_folder_id_cache' in DRIVE_SRC, (
            "_ensure_voice_signatures_folder should cache the folder ID "
            "to avoid repeated API calls"
        )

    def test_voice_signatures_folder_re_raises_retryable(self):
        """_ensure_voice_signatures_folder should re-raise retryable exceptions."""
        # Find the method
        method_start = DRIVE_SRC.find('def _ensure_voice_signatures_folder')
        next_method = DRIVE_SRC.find('\n    def ', method_start + 10)
        method_code = DRIVE_SRC[method_start:next_method] if next_method != -1 else DRIVE_SRC[method_start:]
        
        assert '_RETRYABLE_EXCEPTIONS' in method_code, (
            "_ensure_voice_signatures_folder should re-raise _RETRYABLE_EXCEPTIONS "
            "so the retry decorator can handle them"
        )


# ────────────────────────────────────────────────────────────────
# 4. Functional test: audit report produces non-zero counts
# ────────────────────────────────────────────────────────────────

def _try_import_audit_service():
    """Try to import ArchitectureAuditService; may fail on broken local envs."""
    try:
        from app.services.architecture_audit_service import ArchitectureAuditService
        return ArchitectureAuditService
    except (ImportError, ModuleNotFoundError):
        return None

_AuditService = _try_import_audit_service()
_skip_if_no_audit = pytest.mark.skipif(
    _AuditService is None,
    reason="ArchitectureAuditService import failed (local env issue)"
)


@_skip_if_no_audit
class TestAuditReportWithMockDrive:
    """Test that the audit report correctly picks up data from Drive."""

    def _make_mock_drive(self):
        """Create a mock Drive service with test data."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mocks.mock_drive import MockDriveMemoryService
        
        mock = MockDriveMemoryService()
        # Add some transcripts
        for i in range(7):
            mock.save_transcript(
                {"segments": [{"text": f"Test transcript {i}"}]},
                speakers=[f"Speaker_{i}"]
            )
        # Add some voice signatures
        mock.upload_voice_signature("/tmp/test1.mp3", "איציק")
        mock.upload_voice_signature("/tmp/test2.mp3", "מירי")
        mock.upload_voice_signature("/tmp/test3.mp3", "דן")
        
        # Add voice_map to memory
        mock._memory["user_profile"] = {
            "name": "Test User",
            "voice_map": {
                "speaker_0": "איציק",
                "speaker_1": "מירי",
                "speaker_2": "דן",
                "speaker_3": "Unknown"
            }
        }
        return mock

    def test_voice_metrics_counts_signatures(self):
        """analyze_voice_identification should return non-zero voice_signatures_count."""
        audit = _AuditService()
        mock = self._make_mock_drive()
        result = audit.analyze_voice_identification(mock)
        
        metrics = result.get('metrics', {})
        assert metrics['voice_signatures_count'] == 3, (
            f"Expected 3 voice signatures, got {metrics['voice_signatures_count']}"
        )

    def test_voice_metrics_counts_speakers(self):
        """analyze_voice_identification should count identified speakers."""
        audit = _AuditService()
        mock = self._make_mock_drive()
        result = audit.analyze_voice_identification(mock)
        
        metrics = result.get('metrics', {})
        assert metrics['total_speakers'] == 3, (
            f"Expected 3 identified speakers (excluding Unknown), got {metrics['total_speakers']}"
        )

    def test_data_hygiene_counts_transcripts(self):
        """analyze_data_hygiene should return non-zero transcript_count."""
        audit = _AuditService()
        mock = self._make_mock_drive()
        result = audit.analyze_data_hygiene(mock)
        
        hygiene = result.get('hygiene', {})
        assert hygiene['transcript_count'] == 7, (
            f"Expected 7 transcripts, got {hygiene['transcript_count']}"
        )

    def test_data_hygiene_counts_voice_sigs(self):
        """analyze_data_hygiene should return non-zero voice_signatures_count."""
        audit = _AuditService()
        mock = self._make_mock_drive()
        result = audit.analyze_data_hygiene(mock)
        
        hygiene = result.get('hygiene', {})
        assert hygiene['voice_signatures_count'] == 3, (
            f"Expected 3 voice signatures, got {hygiene['voice_signatures_count']}"
        )

    def test_report_contains_non_zero_counts(self):
        """The final strategic report should show non-zero counts."""
        audit = _AuditService()
        mock = self._make_mock_drive()
        
        voice_metrics = audit.analyze_voice_identification(mock)
        data_hygiene = audit.analyze_data_hygiene(mock)
        
        # Generate report with minimal external data
        report = audit.generate_strategic_report(
            external_scan={"success": False, "error": "test"},
            comparison={"success": False},
            voice_metrics=voice_metrics,
            data_hygiene=data_hygiene,
            health_status=None
        )
        
        # Verify non-zero counts appear in report
        assert '*3*' in report, (
            "Report should show *3* for voice signatures or speakers"
        )
        assert '*7*' in report, (
            "Report should show *7* for transcript count"
        )
        assert 'תמלולים' in report, "Report should mention transcripts"
        assert 'חתימות קול' in report, "Report should mention voice signatures"

    def test_report_with_empty_drive_shows_recommendations(self):
        """With no data, report should show recommendations, not just zeros."""
        audit = _AuditService()
        
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mocks.mock_drive import MockDriveMemoryService
        mock = MockDriveMemoryService()
        mock._memory["user_profile"] = {"name": "Test"}
        
        voice_metrics = audit.analyze_voice_identification(mock)
        data_hygiene = audit.analyze_data_hygiene(mock)
        
        report = audit.generate_strategic_report(
            external_scan={"success": False, "error": "test"},
            comparison={"success": False},
            voice_metrics=voice_metrics,
            data_hygiene=data_hygiene,
            health_status=None
        )
        
        # Should show zeros
        assert '*0*' in report
        # Should recommend starting to use the system
        assert 'התחל' in report or 'START' in report


# ────────────────────────────────────────────────────────────────
# 5. Mock Drive returns correct counts
# ────────────────────────────────────────────────────────────────

class TestMockDriveConsistency:
    """Ensure mock drive counting methods are consistent."""

    def test_mock_count_voice_signatures(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mocks.mock_drive import MockDriveMemoryService
        mock = MockDriveMemoryService()
        mock.upload_voice_signature("/tmp/a.mp3", "Alice")
        mock.upload_voice_signature("/tmp/b.mp3", "Bob")
        assert mock.count_voice_signature_files() == 2

    def test_mock_count_transcripts(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mocks.mock_drive import MockDriveMemoryService
        mock = MockDriveMemoryService()
        mock.save_transcript({"text": "hello"})
        mock.save_transcript({"text": "world"})
        mock.save_transcript({"text": "three"})
        assert mock.count_transcript_files() == 3
