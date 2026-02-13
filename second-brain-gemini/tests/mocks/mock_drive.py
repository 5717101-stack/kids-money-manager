"""
Mock Drive Memory Service — in-memory storage for test assertions.
"""
from typing import Dict, Any, Optional, List
from io import BytesIO
import json
import copy


class MockDriveMemoryService:
    """In-memory substitute for DriveMemoryService."""

    def __init__(self):
        self.is_configured = True
        self.service = True  # Truthy to pass configuration checks

        # In-memory storage
        self._files: Dict[str, Dict[str, Any]] = {}  # file_id -> {name, content, folder}
        self._memory: Dict[str, Any] = {"chat_history": [], "user_profile": {}}
        self._transcripts: List[Dict[str, Any]] = []
        self._voice_signatures: Dict[str, str] = {}  # person_name -> file_id
        self._audio_archive: List[Dict[str, Any]] = []
        self._folder_ids = {
            "audio_archive": "MOCK_AUDIO_ARCHIVE",
            "transcripts": "MOCK_TRANSCRIPTS",
            "voice_signatures": "MOCK_VOICE_SIGS",
            "cursor_inbox": "MOCK_CURSOR_INBOX",
        }
        self.folder_id = "MOCK_ROOT_FOLDER"
        self._file_counter = 0

    def _next_file_id(self) -> str:
        self._file_counter += 1
        return f"MOCK_FILE_{self._file_counter:04d}"

    # ── Folder methods ───────────────────────────────────────────
    def _ensure_audio_archive_folder(self) -> Optional[str]:
        return self._folder_ids["audio_archive"]

    def _ensure_transcripts_folder(self) -> Optional[str]:
        return self._folder_ids["transcripts"]

    def _ensure_voice_signatures_folder(self) -> Optional[str]:
        return self._folder_ids["voice_signatures"]

    def _ensure_cursor_inbox_folder(self) -> Optional[str]:
        return self._folder_ids["cursor_inbox"]

    def _refresh_credentials_if_needed(self):
        pass  # No-op in tests

    # ── Upload methods ───────────────────────────────────────────
    def upload_audio_to_archive(self, audio_path=None, audio_bytes=None,
                                 audio_file_obj=None, filename=None,
                                 mime_type=None) -> Optional[Dict[str, str]]:
        file_id = self._next_file_id()
        entry = {
            "file_id": file_id,
            "web_content_link": f"https://drive.mock/{file_id}",
            "web_view_link": f"https://drive.mock/{file_id}/view",
            "filename": filename or "audio.ogg",
        }
        self._audio_archive.append(entry)
        return entry

    def upload_voice_signature(self, file_path: str, person_name: str) -> Optional[str]:
        file_id = self._next_file_id()
        self._voice_signatures[person_name] = file_id
        return file_id

    def upload_to_context_folder(self, **kwargs) -> Optional[Dict[str, str]]:
        file_id = self._next_file_id()
        return {"file_id": file_id, "filename": kwargs.get("filename", "context_file")}

    # ── Transcript methods ───────────────────────────────────────
    def save_transcript(self, transcript_data: dict, speakers: list = None) -> Optional[str]:
        file_id = self._next_file_id()
        self._transcripts.append({
            "file_id": file_id,
            "data": copy.deepcopy(transcript_data),
            "speakers": speakers or [],
        })
        return file_id

    def get_recent_transcripts(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._transcripts[-limit:]

    def search_transcripts(self, search_terms: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        results = []
        for t in self._transcripts:
            text = json.dumps(t["data"], ensure_ascii=False)
            if any(term.lower() in text.lower() for term in search_terms):
                results.append(t)
        return results[:limit]

    def update_transcript_speaker(self, speaker_id: str, real_name: str,
                                   limit: int = 5) -> int:
        updated = 0
        for t in self._transcripts[-limit:]:
            text = json.dumps(t["data"], ensure_ascii=False)
            if speaker_id in text:
                t["data"] = json.loads(text.replace(speaker_id, real_name))
                updated += 1
        return updated

    def update_summary_speaker(self, speaker_id: str, real_name: str,
                                limit: int = 5) -> int:
        return 0  # Simplified

    # ── Memory methods ───────────────────────────────────────────
    def get_memory(self) -> Dict[str, Any]:
        return copy.deepcopy(self._memory)

    def update_memory(self, new_interaction: Dict[str, Any], background_tasks=None) -> bool:
        self._memory["chat_history"].append(new_interaction)
        return True

    def preload_memory(self) -> bool:
        return True

    # ── Speaker methods ──────────────────────────────────────────
    def get_known_speaker_names(self) -> List[str]:
        return list(self._voice_signatures.keys())

    def count_voice_signature_files(self) -> int:
        return len(self._voice_signatures)

    def count_transcript_files(self) -> int:
        return len(self._transcripts)

    def get_voice_signatures(self, max_signatures: int = 2) -> List[Dict[str, str]]:
        sigs = []
        for name, fid in list(self._voice_signatures.items())[:max_signatures]:
            sigs.append({"name": name, "file_path": f"/tmp/mock_{fid}.mp3"})
        return sigs

    def refresh_credentials(self):
        pass  # No-op in tests

    # ── Cursor inbox ─────────────────────────────────────────────
    def save_cursor_command(self, command: str) -> Optional[str]:
        return self._next_file_id()

    # ── Assertion helpers ────────────────────────────────────────
    def assert_audio_uploaded(self, count: int = 1):
        assert len(self._audio_archive) >= count, (
            f"Expected at least {count} audio uploads, got {len(self._audio_archive)}"
        )

    def assert_transcript_saved(self, count: int = 1):
        assert len(self._transcripts) >= count, (
            f"Expected at least {count} transcripts, got {len(self._transcripts)}"
        )

    def assert_voice_signature_saved(self, person_name: str):
        assert person_name in self._voice_signatures, (
            f"Expected voice signature for '{person_name}', "
            f"saved: {list(self._voice_signatures.keys())}"
        )

    def reset(self):
        self._files.clear()
        self._memory = {"chat_history": [], "user_profile": {}}
        self._transcripts.clear()
        self._voice_signatures.clear()
        self._audio_archive.clear()
        self._file_counter = 0
