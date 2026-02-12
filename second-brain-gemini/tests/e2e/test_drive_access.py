"""
E2E tests for Google Drive folder access.

Verifies that the system can access all required Drive folders:
- Memory folder (root)
- Audio archive
- Transcripts
- Voice signatures
- Cursor inbox
- Context folder (KB)

These tests can run in two modes:
1. Mocked (default) — uses MockDriveMemoryService
2. Live (manual) — hits real Drive API (mark with @pytest.mark.live)
"""
import pytest
from tests.mocks.mock_drive import MockDriveMemoryService


class TestDriveFolderAccess:
    """Test Drive folder structure is properly configured."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.drive = MockDriveMemoryService()

    def test_audio_archive_folder_exists(self):
        """Audio archive folder should be accessible."""
        folder_id = self.drive._ensure_audio_archive_folder()
        assert folder_id is not None

    def test_transcripts_folder_exists(self):
        """Transcripts folder should be accessible."""
        folder_id = self.drive._ensure_transcripts_folder()
        assert folder_id is not None

    def test_voice_signatures_folder_exists(self):
        """Voice signatures folder should be accessible."""
        folder_id = self.drive._ensure_voice_signatures_folder()
        assert folder_id is not None

    def test_cursor_inbox_folder_exists(self):
        """Cursor inbox folder should be accessible."""
        folder_id = self.drive._ensure_cursor_inbox_folder()
        assert folder_id is not None

    def test_upload_audio_returns_metadata(self):
        """Audio upload should return file_id and links."""
        result = self.drive.upload_audio_to_archive(
            audio_bytes=b"fake audio content",
            filename="test_audio.ogg"
        )
        assert result is not None
        assert "file_id" in result
        assert result["file_id"]

    def test_save_transcript_returns_file_id(self):
        """Transcript save should return a file ID."""
        file_id = self.drive.save_transcript(
            transcript_data={"text": "שלום, זו שיחת בדיקה"},
            speakers=["Speaker 1"]
        )
        assert file_id is not None

    def test_upload_voice_signature(self):
        """Voice signature upload should succeed."""
        file_id = self.drive.upload_voice_signature(
            file_path="/tmp/test_voice.ogg",
            person_name="יובל"
        )
        assert file_id is not None
        self.drive.assert_voice_signature_saved("יובל")

    def test_transcript_search(self):
        """Should find transcripts by search terms."""
        self.drive.save_transcript({"text": "שיחה עם יובל על הפרויקט"})
        self.drive.save_transcript({"text": "פגישה עם חן על התקציב"})

        results = self.drive.search_transcripts(["יובל"])
        assert len(results) == 1

    def test_speaker_retroactive_update(self):
        """Should update speaker names in saved transcripts."""
        self.drive.save_transcript({"text": "Unknown Speaker 1 אמר שלום"})

        updated = self.drive.update_transcript_speaker(
            speaker_id="Unknown Speaker 1",
            real_name="יובל לייקין"
        )
        assert updated == 1

        # Verify the transcript was updated
        transcripts = self.drive.get_recent_transcripts(limit=1)
        text = str(transcripts[0]["data"])
        assert "יובל לייקין" in text
        assert "Unknown Speaker 1" not in text


@pytest.mark.live
class TestDriveLiveAccess:
    """
    Live tests against real Google Drive.
    Run manually: pytest tests/e2e/test_drive_access.py -m live -v
    Requires real credentials in environment.
    """

    def test_live_memory_load(self):
        """Load memory from real Drive."""
        from app.services.drive_memory_service import DriveMemoryService
        import os

        if not os.environ.get("GOOGLE_CLIENT_ID"):
            pytest.skip("No real Drive credentials available")

        service = DriveMemoryService()
        if not service.is_configured:
            pytest.skip("Drive service not configured")

        memory = service.get_memory()
        assert isinstance(memory, dict)
        assert "chat_history" in memory
