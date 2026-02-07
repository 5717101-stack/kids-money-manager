"""
Context Writer Service — Smart Write-back to Knowledge Base JSONs

Provides:
1. update_context(file_name, updates) — Smart merge into org_structure.json / family_tree.json on Drive
2. identify_facts(transcript_text, segments) — Gemini-based new-fact extraction from transcripts
3. Pending-confirmation tracking per phone number (one-shot, TTL 10 min)

Usage (from main.py):
    from app.services.context_writer_service import context_writer

    # After transcript is ready:
    facts = context_writer.identify_facts(summary_text, segments)
    if facts:
        msg_id = context_writer.send_fact_confirmation(phone, facts, whatsapp_provider)

    # When user replies "כן" or a digit:
    result = context_writer.try_confirm_facts(phone, message_text)
    if result:
        for fact in result.confirmed_facts:
            context_writer.apply_fact(fact)
"""

import json
import io
import logging
import os
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
CONFIRMATION_TTL_SECONDS = 600  # 10 minutes
MAX_PENDING = 100


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ExtractedFact:
    """A single new fact detected from a transcript."""
    person_name: str        # Canonical English name
    field: str              # e.g. "title", "salary", "children", "reports_to"
    old_value: Any          # Current value (or None if new)
    new_value: Any          # Value detected from transcript
    source_quote: str       # The sentence from the transcript supporting this
    confidence: str         # "high" | "medium"

    def to_dict(self) -> dict:
        return {
            "person_name": self.person_name,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source_quote": self.source_quote,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(d: dict) -> "ExtractedFact":
        return ExtractedFact(
            person_name=d.get("person_name", ""),
            field=d.get("field", ""),
            old_value=d.get("old_value"),
            new_value=d.get("new_value"),
            source_quote=d.get("source_quote", ""),
            confidence=d.get("confidence", "medium"),
        )


@dataclass
class PendingConfirmation:
    """Tracks facts awaiting user approval."""
    facts: List[ExtractedFact] = field(default_factory=list)
    created_at: float = 0.0
    whatsapp_msg_id: str = ""  # The message ID we sent to track replies

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > CONFIRMATION_TTL_SECONDS


@dataclass
class ConfirmationResult:
    """Returned when user confirms/rejects facts."""
    confirmed_facts: List[ExtractedFact]
    rejected_facts: List[ExtractedFact]


# ═══════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════

class ContextWriterService:
    """Manages fact extraction, confirmation, and write-back to Drive JSONs."""

    def __init__(self):
        self._pending: Dict[str, PendingConfirmation] = {}
        self._lock = Lock()

    # ──────────────────────────────────────────────────────────────────
    # 1. FACT IDENTIFICATION (Gemini-powered)
    # ──────────────────────────────────────────────────────────────────

    def identify_facts(
        self,
        summary_text: str,
        segments: List[Dict[str, Any]],
    ) -> List[ExtractedFact]:
        """
        Use Gemini (Flash for speed/cost) to scan a transcript for new facts
        about people in the Knowledge Base.

        Returns a list of ExtractedFact objects. Returns [] if nothing new found.
        """
        if not summary_text and not segments:
            return []

        # Build a short transcript snippet (limit tokens)
        transcript_lines = []
        for seg in (segments or [])[:80]:
            speaker = seg.get("speaker", "?")
            text = seg.get("text", "")
            if text.strip():
                transcript_lines.append(f"{speaker}: {text.strip()}")
        transcript_block = "\n".join(transcript_lines)
        if not transcript_block:
            transcript_block = summary_text or ""
        if len(transcript_block) > 6000:
            transcript_block = transcript_block[:6000] + "\n[...truncated]"

        # Load current KB people for comparison
        known_people_summary = self._get_known_people_summary()

        prompt = f"""You are a fact-extraction assistant for a Knowledge Base system.

KNOWN PEOPLE IN THE DATABASE:
{known_people_summary}

TRANSCRIPT:
{transcript_block}

TASK:
Scan the transcript for NEW FACTS about any of the known people above.
A "new fact" is information that UPDATES or ADDS to their existing record — for example:
- A role change ("David is now VP of Engineering")
- A salary mention ("Her salary is $180K")
- A family update ("Yuval's daughter started school")
- A reporting change ("Shey now reports to Amit")
- A new team member ("We hired Noa for the Product team under Asaf")

RULES:
1. ONLY flag facts about people who EXIST in the database (or are clearly joining/being added).
2. Do NOT flag opinions, small talk, or speculative statements.
3. Each fact must have a direct quote from the transcript.
4. Confidence = "high" if the speaker states it as fact. "medium" if inferred.
5. If NO new facts are found, return an EMPTY array.

OUTPUT FORMAT (strict JSON array):
```json
[
  {{
    "person_name": "Full English Name",
    "field": "title|salary|reports_to|department|children|rating|individual_factor|new_hire|other",
    "old_value": null,
    "new_value": "the new value",
    "source_quote": "exact quote from transcript",
    "confidence": "high|medium"
  }}
]
```

Return ONLY the JSON array. No explanations."""

        try:
            from app.services.model_discovery import MODEL_MAPPING, gemini_v1_generate

            response_text, error = gemini_v1_generate(
                model_name=MODEL_MAPPING["flash"],
                prompt_parts=[prompt],
                generation_config={"temperature": 0.1, "max_output_tokens": 2048},
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
                timeout=30,
            )

            if error or not response_text:
                print(f"   ⚠️ [FactID] Gemini error: {error}")
                return []

            # Parse JSON from response
            cleaned = response_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1]
                if "```" in cleaned:
                    cleaned = cleaned.split("```", 1)[0]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
                if "```" in cleaned:
                    cleaned = cleaned.split("```", 1)[0]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                return []

            facts = []
            for item in parsed:
                if item.get("person_name") and item.get("field") and item.get("new_value"):
                    facts.append(ExtractedFact.from_dict(item))

            print(f"   🔍 [FactID] Found {len(facts)} new fact(s)")
            for f in facts:
                print(f"      • {f.person_name}.{f.field} = {f.new_value} [{f.confidence}]")
            return facts

        except json.JSONDecodeError as je:
            print(f"   ⚠️ [FactID] JSON parse error: {je}")
            return []
        except Exception as e:
            print(f"   ⚠️ [FactID] Error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────
    # 2. CONFIRMATION FLOW (WhatsApp)
    # ──────────────────────────────────────────────────────────────────

    def format_fact_confirmation(self, facts: List[ExtractedFact]) -> str:
        """Format facts as a Hebrew WhatsApp confirmation message."""
        if not facts:
            return ""

        lines = ["🧠 *זיהיתי עובדות חדשות מהשיחה:*", ""]
        for i, fact in enumerate(facts, 1):
            name = fact.person_name
            field_he = self._field_to_hebrew(fact.field)
            if fact.old_value:
                lines.append(f"{i}. *{name}* — {field_he}: {fact.old_value} → *{fact.new_value}*")
            else:
                lines.append(f"{i}. *{name}* — {field_he}: *{fact.new_value}*")
            if fact.source_quote:
                quote = fact.source_quote[:80]
                lines.append(f"   _{quote}_")

        lines.append("")
        lines.append("השב *כן* לעדכן הכל, *לא* לבטל, או מספר ספציפי לאשר חלקית.")
        return "\n".join(lines)

    def store_pending(self, phone: str, facts: List[ExtractedFact], msg_id: str = ""):
        """Save facts as pending confirmation for this phone number."""
        with self._lock:
            # Evict expired
            expired = [k for k, v in self._pending.items() if v.is_expired()]
            for k in expired:
                del self._pending[k]
            if len(self._pending) > MAX_PENDING:
                oldest = min(self._pending, key=lambda k: self._pending[k].created_at)
                del self._pending[oldest]

            self._pending[phone] = PendingConfirmation(
                facts=facts,
                created_at=time.time(),
                whatsapp_msg_id=msg_id,
            )
        print(f"📝 [Writer] Stored {len(facts)} pending fact(s) for {phone}")

    def has_pending(self, phone: str) -> bool:
        """Check if this phone has pending fact confirmations."""
        with self._lock:
            p = self._pending.get(phone)
            return p is not None and not p.is_expired() and len(p.facts) > 0

    def try_confirm_facts(
        self, phone: str, message: str
    ) -> Optional[ConfirmationResult]:
        """
        Check if the user's message is a confirmation/rejection of pending facts.

        Accepts:
        - "כן" / "yes" → confirm ALL
        - "לא" / "no"  → reject ALL
        - Single digit (e.g. "1") → confirm only that fact
        - Comma-separated digits (e.g. "1,3") → confirm those facts
        """
        with self._lock:
            pending = self._pending.get(phone)
            if not pending or pending.is_expired() or not pending.facts:
                return None

        msg = message.strip().lower()

        # ── Confirm all ──
        if msg in ("כן", "yes", "כ", "y"):
            facts = pending.facts
            with self._lock:
                del self._pending[phone]
            print(f"✅ [Writer] User confirmed ALL {len(facts)} fact(s)")
            return ConfirmationResult(confirmed_facts=facts, rejected_facts=[])

        # ── Reject all ──
        if msg in ("לא", "no", "ל", "n"):
            facts = pending.facts
            with self._lock:
                del self._pending[phone]
            print(f"❌ [Writer] User rejected ALL {len(facts)} fact(s)")
            return ConfirmationResult(confirmed_facts=[], rejected_facts=facts)

        # ── Selective confirm (digits) ──
        digit_match = re.match(r'^[\d,\s]+$', msg)
        if digit_match:
            selected = set()
            for part in msg.replace(" ", "").split(","):
                if part.isdigit():
                    selected.add(int(part))

            confirmed = []
            rejected = []
            for i, fact in enumerate(pending.facts, 1):
                if i in selected:
                    confirmed.append(fact)
                else:
                    rejected.append(fact)

            with self._lock:
                del self._pending[phone]

            print(f"✅ [Writer] User confirmed {len(confirmed)}/{len(pending.facts)} fact(s)")
            return ConfirmationResult(confirmed_facts=confirmed, rejected_facts=rejected)

        return None  # Not a confirmation message

    # ──────────────────────────────────────────────────────────────────
    # 3. SMART MERGE — Write facts back to Drive JSONs
    # ──────────────────────────────────────────────────────────────────

    def apply_facts(self, facts: List[ExtractedFact]) -> Tuple[int, List[str]]:
        """
        Apply confirmed facts to the appropriate JSON files on Google Drive.
        Uses smart merge: only updates specific fields, never overwrites the full object.

        Returns (success_count, error_messages).
        """
        if not facts:
            return 0, []

        # Group facts by target file
        org_facts = []
        family_facts = []
        for fact in facts:
            if fact.field in ("children", "spouse", "parent", "sibling", "family_role"):
                family_facts.append(fact)
            else:
                org_facts.append(fact)

        success = 0
        errors = []

        if org_facts:
            ok, err = self._merge_into_json("org_structure.json", org_facts)
            success += ok
            errors.extend(err)

        if family_facts:
            ok, err = self._merge_into_json("family_tree.json", family_facts)
            success += ok
            errors.extend(err)

        # Invalidate KB cache so next query picks up changes
        if success > 0:
            self._invalidate_kb_cache()

        return success, errors

    def _merge_into_json(
        self, file_name: str, facts: List[ExtractedFact]
    ) -> Tuple[int, List[str]]:
        """
        Download a JSON from Drive, smart-merge facts, re-upload.
        """
        errors = []
        try:
            service = self._get_drive_service()
            folder_id = os.environ.get("CONTEXT_FOLDER_ID")
            if not service or not folder_id:
                return 0, [f"Drive not configured for {file_name}"]

            # Find the file in Drive
            file_id, current_data = self._download_json_from_drive(service, folder_id, file_name)
            if current_data is None:
                current_data = {}

            success_count = 0
            # Smart merge each fact
            for fact in facts:
                try:
                    self._smart_merge_fact(current_data, fact, file_name)
                    success_count += 1
                    print(f"   ✅ [Writer] Merged: {fact.person_name}.{fact.field} = {fact.new_value}")
                except Exception as merge_err:
                    msg = f"Failed to merge {fact.person_name}.{fact.field}: {merge_err}"
                    errors.append(msg)
                    print(f"   ❌ [Writer] {msg}")

            # Upload back to Drive
            if success_count > 0:
                if file_id:
                    self._upload_json_to_drive(service, file_id, current_data)
                else:
                    self._create_json_in_drive(service, folder_id, file_name, current_data)
                print(f"   ✅ [Writer] Uploaded {file_name} with {success_count} update(s)")

            return success_count, errors

        except Exception as e:
            msg = f"Error updating {file_name}: {e}"
            print(f"   ❌ [Writer] {msg}")
            return 0, [msg]

    def _smart_merge_fact(
        self, data: Dict[str, Any], fact: ExtractedFact, file_name: str
    ):
        """
        Smart merge: find the person in the JSON and update only the specific field.
        If the person doesn't exist, add a new entry.
        """
        person_name = fact.person_name
        field = fact.field
        new_value = fact.new_value

        # ── org_structure.json: structured with 'employees' or 'people' array ──
        if "org_structure" in file_name:
            people = data.get("employees") or data.get("people") or data.get("nodes") or []
            found = False
            for person in people:
                name = person.get("name") or person.get("full_name") or person.get("full_name_english") or ""
                if name.lower() == person_name.lower():
                    person[field] = new_value
                    found = True
                    break

            if not found:
                # Add new person entry
                new_entry = {"name": person_name, field: new_value}
                # Add to the first available array key
                for key in ("employees", "people", "nodes"):
                    if key in data:
                        data[key].append(new_entry)
                        found = True
                        break
                if not found:
                    data.setdefault("employees", []).append(new_entry)

        # ── family_tree.json: similar structure ──
        elif "family_tree" in file_name:
            members = data.get("members") or data.get("people") or data.get("family") or []
            found = False
            for person in members:
                name = person.get("name") or person.get("full_name") or ""
                if name.lower() == person_name.lower():
                    # Smart merge: for list fields, append instead of overwrite
                    if field in ("children", "siblings") and isinstance(person.get(field), list):
                        if new_value not in person[field]:
                            person[field].append(new_value)
                    else:
                        person[field] = new_value
                    found = True
                    break

            if not found:
                new_entry = {"name": person_name, field: new_value}
                for key in ("members", "people", "family"):
                    if key in data:
                        data[key].append(new_entry)
                        found = True
                        break
                if not found:
                    data.setdefault("members", []).append(new_entry)

    # ──────────────────────────────────────────────────────────────────
    # DRIVE HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_drive_service():
        """Build Google Drive API service (reuses KB pattern)."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            client_id = os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
            refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

            if not all([client_id, client_secret, refresh_token]):
                return None

            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            return build("drive", "v3", credentials=creds, cache_discovery=False)
        except Exception as e:
            logger.warning(f"[Writer] Drive service error: {e}")
            return None

    @staticmethod
    def _download_json_from_drive(
        service, folder_id: str, file_name: str
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """Download and parse a JSON file from Drive. Returns (file_id, parsed_data)."""
        try:
            query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])

            if not files:
                print(f"   ⚠️ [Writer] {file_name} not found in Drive — will create new")
                return None, None

            file_id = files[0]["id"]
            from googleapiclient.http import MediaIoBaseDownload

            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            raw = buffer.getvalue().decode("utf-8")
            data = json.loads(raw)
            print(f"   📥 [Writer] Downloaded {file_name} ({len(raw)} bytes)")
            return file_id, data

        except Exception as e:
            print(f"   ❌ [Writer] Error downloading {file_name}: {e}")
            return None, None

    @staticmethod
    def _upload_json_to_drive(service, file_id: str, data: Dict[str, Any]):
        """Update an existing JSON file on Drive."""
        from googleapiclient.http import MediaIoBaseUpload

        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(
            io.BytesIO(json_bytes), mimetype="application/json", resumable=False
        )
        service.files().update(fileId=file_id, media_body=media).execute()

    @staticmethod
    def _create_json_in_drive(
        service, folder_id: str, file_name: str, data: Dict[str, Any]
    ):
        """Create a new JSON file in the Drive folder."""
        from googleapiclient.http import MediaIoBaseUpload

        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(
            io.BytesIO(json_bytes), mimetype="application/json", resumable=False
        )
        metadata = {"name": file_name, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media).execute()
        print(f"   📤 [Writer] Created new file: {file_name}")

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _invalidate_kb_cache():
        """Force KB service to reload on next query."""
        try:
            from app.services import knowledge_base_service as kb
            kb._cache_timestamp = 0
            kb._cached_context = None
            print("   🔄 [Writer] KB cache invalidated — will reload on next query")
        except Exception:
            pass

    @staticmethod
    def _get_known_people_summary() -> str:
        """Get a compact summary of people in the KB for the fact-extraction prompt."""
        try:
            from app.services.knowledge_base_service import _identity_graph
            if not _identity_graph:
                return "(No people loaded yet)"

            people = _identity_graph.get("people", {})
            if not people:
                return "(No people loaded yet)"

            lines = []
            for name, info in list(people.items())[:100]:
                title = info.get("title", "")
                dept = info.get("department", "")
                mgr = info.get("reports_to", "")
                salary = info.get("salary", "")
                parts = [name]
                if title:
                    parts.append(f"title={title}")
                if dept:
                    parts.append(f"dept={dept}")
                if mgr:
                    parts.append(f"reports_to={mgr}")
                if salary:
                    parts.append(f"salary={salary}")
                lines.append(" | ".join(parts))

            return "\n".join(lines) if lines else "(No people loaded yet)"
        except Exception:
            return "(Could not load people)"

    @staticmethod
    def _field_to_hebrew(field: str) -> str:
        """Translate field names to Hebrew for the WhatsApp menu."""
        mapping = {
            "title": "תפקיד",
            "salary": "שכר",
            "reports_to": "מנהל",
            "department": "מחלקה",
            "children": "ילדים",
            "spouse": "בן/בת זוג",
            "rating": "דירוג",
            "individual_factor": "פקטור אישי",
            "new_hire": "עובד חדש",
            "parent": "הורה",
            "sibling": "אח/אחות",
            "family_role": "תפקיד משפחתי",
        }
        return mapping.get(field, field)


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
context_writer = ContextWriterService()
