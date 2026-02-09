"""
Speaker Identity Service — Unified Person Identity Graph
=========================================================
Manages the Speaker Identity Graph that links:
  - Voice profiles (embeddings + source metadata)
  - Org chart references (person from org_structure.json)
  - Conversation history per person
  - Sentiment tracking over time

Storage: speaker_identity.json on Google Drive (same folder as second_brain_memory.json)
person_id format: "yuval_laikin" (lowercase, underscores)
"""

import json
import io
import logging
import re
import numpy as np
from typing import Optional, Dict, Any, List
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)

SPEAKER_IDENTITY_FILE = "speaker_identity.json"

DEFAULT_STRUCTURE = {
    "version": 1,
    "people": {},
    "name_map": {},        # "יובל" → "yuval_laikin", "yuval" → "yuval_laikin"
    "voice_map_history": []  # Per-session speaker mapping log
}


def generate_person_id(canonical_name: str) -> str:
    """Generate a person_id from a canonical name.

    "Yuval Laikin" → "yuval_laikin"
    "איציק" → "___" (Hebrew chars stripped — callers should provide English canonical name)
    """
    clean = canonical_name.strip().lower()
    # Keep only ASCII alphanumeric and spaces
    clean = re.sub(r'[^a-z0-9\s]', '', clean)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    return clean or f"person_{abs(hash(canonical_name)) % 100000}"


class SpeakerIdentityService:
    """Manages the Speaker Identity Graph on Google Drive."""

    def __init__(self):
        self._data: Dict[str, Any] = {k: (v.copy() if isinstance(v, (dict, list)) else v)
                                       for k, v in DEFAULT_STRUCTURE.items()}
        self._lock = Lock()
        self._drive_service = None
        self._folder_id: Optional[str] = None
        self._file_id: Optional[str] = None
        self._loaded = False
        self._dirty = False

    # ─── Initialization ───────────────────────────────────────

    def initialize(self, drive_memory_service) -> bool:
        """Initialize with DriveMemoryService for Drive access.

        Returns True if loaded successfully.
        """
        if drive_memory_service and drive_memory_service.is_configured:
            self._drive_service = drive_memory_service.service
            self._folder_id = drive_memory_service.folder_id
            return self._load_from_drive()
        else:
            logger.warning("⚠️ SpeakerIdentityService: Drive not configured, using in-memory only")
            return False

    def _load_from_drive(self) -> bool:
        """Load speaker_identity.json from Drive."""
        if not self._drive_service or not self._folder_id:
            return False

        try:
            from googleapiclient.http import MediaIoBaseDownload

            query = (f"'{self._folder_id}' in parents and "
                     f"name = '{SPEAKER_IDENTITY_FILE}' and trashed = false")
            results = self._drive_service.files().list(
                q=query, fields="files(id)"
            ).execute()
            files = results.get('files', [])

            if files:
                self._file_id = files[0]['id']
                request = self._drive_service.files().get_media(fileId=self._file_id)
                buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(buffer, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                buffer.seek(0)
                content = buffer.read().decode('utf-8')
                self._data = json.loads(content)
                # Ensure structure
                for key, default in DEFAULT_STRUCTURE.items():
                    if key not in self._data:
                        self._data[key] = default.copy() if isinstance(default, (dict, list)) else default
                self._loaded = True
                logger.info(f"✅ Loaded speaker_identity.json ({len(self._data.get('people', {}))} people)")
                return True
            else:
                logger.info("ℹ️ speaker_identity.json not found — creating new")
                self._save_to_drive()
                self._loaded = True
                return True
        except Exception as e:
            logger.error(f"❌ Error loading speaker_identity.json: {e}")
            return False

    def _save_to_drive(self):
        """Save speaker_identity.json to Drive."""
        if not self._drive_service or not self._folder_id:
            return

        try:
            from googleapiclient.http import MediaIoBaseUpload

            content = json.dumps(self._data, ensure_ascii=False, indent=2)
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode('utf-8')),
                mimetype='application/json'
            )

            if self._file_id:
                self._drive_service.files().update(
                    fileId=self._file_id,
                    media_body=media
                ).execute()
            else:
                file_metadata = {
                    'name': SPEAKER_IDENTITY_FILE,
                    'parents': [self._folder_id],
                    'mimeType': 'application/json'
                }
                file = self._drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self._file_id = file.get('id')

            self._dirty = False
            logger.info(f"💾 Saved speaker_identity.json ({len(self._data.get('people', {}))} people)")
        except Exception as e:
            logger.error(f"❌ Error saving speaker_identity.json: {e}")

    def save_if_dirty(self):
        """Save to Drive if there are unsaved changes."""
        if self._dirty:
            self._save_to_drive()

    # ─── Person CRUD ──────────────────────────────────────────

    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Get a person by person_id."""
        with self._lock:
            return self._data.get("people", {}).get(person_id)

    def get_all_people(self) -> Dict[str, Any]:
        """Get all people."""
        with self._lock:
            return dict(self._data.get("people", {}))

    def add_person(self, canonical_name: str, aliases: List[str] = None,
                   org_ref: str = None, person_id: str = None) -> str:
        """Add or update a person in the identity graph.

        Returns the person_id.
        """
        if not person_id:
            person_id = generate_person_id(canonical_name)

        with self._lock:
            if person_id in self._data["people"]:
                person = self._data["people"][person_id]
                if aliases:
                    existing = set(person.get("aliases", []))
                    existing.update(aliases)
                    person["aliases"] = list(existing)
                if org_ref:
                    person["org_ref"] = org_ref
            else:
                self._data["people"][person_id] = {
                    "person_id": person_id,
                    "canonical_name": canonical_name,
                    "aliases": aliases or [],
                    "voice_profiles": [],
                    "org_ref": org_ref,
                    "conversations": [],
                    "sentiment_timeline": [],
                    "last_interaction": None,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }

            # Update name_map
            name_map = self._data.setdefault("name_map", {})
            name_map[canonical_name.lower()] = person_id
            if aliases:
                for alias in aliases:
                    name_map[alias.lower()] = person_id

            self._dirty = True
        return person_id

    def resolve_name(self, name: str) -> Optional[str]:
        """Resolve a name (Hebrew/English/nickname) to person_id.

        Returns person_id or None.
        """
        with self._lock:
            name_lower = name.strip().lower()
            name_map = self._data.get("name_map", {})

            # Exact match
            if name_lower in name_map:
                return name_map[name_lower]

            # Substring match
            for variant, pid in name_map.items():
                if name_lower in variant or variant in name_lower:
                    return pid

            return None

    # ─── Voice Profiles ───────────────────────────────────────

    def add_voice_profile(self, person_id: str, embedding: List[float],
                          source: str = "enrollment",
                          audio_file_id: str = None,
                          start_sec: float = None, end_sec: float = None,
                          quality: float = 1.0):
        """Add a voice embedding to a person's profile."""
        with self._lock:
            person = self._data.get("people", {}).get(person_id)
            if not person:
                logger.error(f"❌ Person {person_id} not found — cannot add voice profile")
                return

            profile = {
                "source": source,
                "embedding": embedding,
                "audio_file_id": audio_file_id,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "quality": quality,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            person.setdefault("voice_profiles", []).append(profile)
            self._dirty = True

    def get_all_embeddings(self) -> Dict[str, List[List[float]]]:
        """Get all voice embeddings indexed by person_id.

        Returns: {"yuval_laikin": [[0.23, -0.45, ...], [...]], ...}
        """
        with self._lock:
            result = {}
            for pid, person in self._data.get("people", {}).items():
                profiles = person.get("voice_profiles", [])
                embeddings = [p["embedding"] for p in profiles if p.get("embedding")]
                if embeddings:
                    result[pid] = embeddings
            return result

    def get_centroid_embeddings(self) -> Dict[str, List[float]]:
        """Get the centroid (average) embedding per person.

        More robust than any single embedding.
        Returns: {"yuval_laikin": [0.23, -0.45, ...], ...}
        """
        all_emb = self.get_all_embeddings()
        centroids = {}
        for pid, embeddings in all_emb.items():
            if embeddings:
                arr = np.array(embeddings)
                centroid = arr.mean(axis=0)
                norm = np.linalg.norm(centroid)
                if norm > 0:
                    centroid = centroid / norm
                centroids[pid] = centroid.tolist()
        return centroids

    # ─── Conversation Index ───────────────────────────────────

    def add_conversation(self, person_id: str, date: str,
                         transcript_id: str = None,
                         audio_file_id: str = None,
                         topics: List[str] = None,
                         sentiment: float = None,
                         key_segments: List[Dict] = None,
                         summary: str = None):
        """Add a conversation entry to a person's history."""
        with self._lock:
            person = self._data.get("people", {}).get(person_id)
            if not person:
                return

            conv = {
                "date": date,
                "transcript_id": transcript_id,
                "audio_file_id": audio_file_id,
                "topics": topics or [],
                "sentiment": sentiment,
                "key_segments": key_segments or [],
                "summary": summary
            }
            person.setdefault("conversations", []).append(conv)
            person["last_interaction"] = date

            if sentiment is not None:
                person.setdefault("sentiment_timeline", []).append({
                    "date": date,
                    "score": sentiment
                })

            self._dirty = True

    def get_person_history(self, person_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for a person."""
        with self._lock:
            person = self._data.get("people", {}).get(person_id)
            if not person:
                return []
            return person.get("conversations", [])[-limit:]

    def get_sentiment_timeline(self, person_id: str) -> List[Dict]:
        """Get sentiment timeline for a person."""
        with self._lock:
            person = self._data.get("people", {}).get(person_id)
            if not person:
                return []
            return person.get("sentiment_timeline", [])

    # ─── Voice Map History ────────────────────────────────────

    def record_voice_mapping(self, date: str, audio_file_id: str,
                             mappings: Dict[str, Dict]):
        """Record a voice mapping from a session.

        mappings: {"SPEAKER_00": {"person_id": "itzik_bachar", "confidence": 0.95}, ...}
        """
        with self._lock:
            self._data.setdefault("voice_map_history", []).append({
                "date": date,
                "audio_file_id": audio_file_id,
                "mappings": mappings
            })
            # Keep last 100
            if len(self._data["voice_map_history"]) > 100:
                self._data["voice_map_history"] = self._data["voice_map_history"][-100:]
            self._dirty = True

    # ─── Utility ──────────────────────────────────────────────

    def get_person_canonical_name(self, person_id: str) -> Optional[str]:
        """Get the canonical name for a person_id."""
        person = self.get_person(person_id)
        return person.get("canonical_name") if person else None

    def get_stats(self) -> Dict[str, Any]:
        """Get stats about the identity graph."""
        with self._lock:
            people = self._data.get("people", {})
            total_profiles = sum(
                len(p.get("voice_profiles", []))
                for p in people.values()
            )
            total_conversations = sum(
                len(p.get("conversations", []))
                for p in people.values()
            )
            return {
                "total_people": len(people),
                "total_voice_profiles": total_profiles,
                "total_conversations": total_conversations,
                "loaded": self._loaded,
                "dirty": self._dirty
            }


# Singleton
speaker_identity_service = SpeakerIdentityService()
