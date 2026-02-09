"""
NotebookLM-Style Deep Analysis Service
========================================
Generates rich, structured summaries of audio recordings — similar to
Google NotebookLM's analysis capabilities.

Architecture:
  - Feature flag: NOTEBOOKLM_ENABLED (default: "true")
  - Provider:     NOTEBOOKLM_PROVIDER (default: "gemini")
  - When Google releases a dedicated NotebookLM API, swap provider to
    "notebooklm_api" — zero code changes needed in callers.

The service is called AFTER the standard audio pipeline completes.
It takes the transcript + expert analysis and generates:
  1. Executive Summary (תמצית מנהלים)
  2. Key Topics with details (נושאים מרכזיים)
  3. Action Items (פריטי פעולה)
  4. Decisions Made (החלטות שהתקבלו)
  5. Notable Quotes (ציטוטים בולטים)
  6. Speaker Profiles (פרופיל דוברים)
  7. Follow-up Questions (שאלות המשך)
  8. Text Infographic (אינפוגרפיקה טקסטואלית)

Storage:
  - Saved as JSON to Google Drive → NotebookLM_Summaries/ folder
  - Queryable via `search_notebook` tool in Conversation Engine

Kill switch:
  - Set NOTEBOOKLM_ENABLED=false to disable entirely
  - No code changes, no redeployment needed (just env var)
"""

import os
import io
import json
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

NOTEBOOKLM_ENABLED = os.environ.get("NOTEBOOKLM_ENABLED", "true").lower() == "true"
NOTEBOOKLM_PROVIDER = os.environ.get("NOTEBOOKLM_PROVIDER", "gemini")
NOTEBOOKLM_FOLDER_NAME = "NotebookLM_Summaries"


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER INTERFACE (Abstract)
# ═══════════════════════════════════════════════════════════════════════

class NotebookLMProvider:
    """Base class for NotebookLM-style analysis providers."""

    def analyze(self, transcript_text: str, expert_summary: str,
                speakers: list, metadata: dict) -> Optional[Dict[str, Any]]:
        """
        Generate a deep structured analysis of a conversation.

        Args:
            transcript_text: Full transcript text (all segments joined)
            expert_summary: The expert analysis text from the audio pipeline
            speakers: List of speaker names
            metadata: Dict with filename, timestamp, source, etc.

        Returns:
            Structured analysis dict, or None on failure
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════
# GEMINI PROVIDER — Uses Gemini API to mimic NotebookLM analysis
# ═══════════════════════════════════════════════════════════════════════

class GeminiNotebookProvider(NotebookLMProvider):
    """
    Uses Gemini 2.5 Pro to generate NotebookLM-style deep analysis.
    This is the default provider until Google releases a dedicated API.
    """

    def analyze(self, transcript_text: str, expert_summary: str,
                speakers: list, metadata: dict) -> Optional[Dict[str, Any]]:
        try:
            from app.services.model_discovery import MODEL_MAPPING, configure_genai
            import google.generativeai as genai

            api_key = os.environ.get("GOOGLE_API_KEY", "")
            if not api_key:
                logger.error("[NotebookLM] No GOOGLE_API_KEY — cannot analyze")
                return None

            configure_genai(api_key)

            model_name = MODEL_MAPPING.get("pro", "gemini-2.5-pro")
            model = genai.GenerativeModel(model_name)

            # Build the analysis prompt
            speakers_str = ", ".join(speakers) if speakers else "לא זוהו"
            filename = metadata.get("filename", "unknown")
            timestamp = metadata.get("timestamp", "")

            prompt = f"""אתה מנתח שיחות מקצועי ברמה של NotebookLM של גוגל.
קיבלת תמלול של שיחה/פגישה. הפק ניתוח מעמיק ומובנה.

═══ פרטי ההקלטה ═══
קובץ: {filename}
תאריך: {timestamp}
דוברים: {speakers_str}

═══ תמלול השיחה ═══
{transcript_text[:15000]}

═══ ניתוח מומחה (אם קיים) ═══
{expert_summary[:5000] if expert_summary else "לא זמין"}

═══════════════════════════════════════════════
הפק את הניתוח הבא בפורמט JSON מדויק (בעברית):
═══════════════════════════════════════════════

החזר JSON בלבד, בלי markdown, בלי backticks, בפורמט הבא:
{{
  "executive_summary": "תמצית מנהלים של 2-3 משפטים — מה הנקודה המרכזית של השיחה",
  "key_topics": [
    {{
      "topic": "שם הנושא",
      "details": "פירוט קצר על מה דובר",
      "speakers_involved": ["שם דובר 1", "שם דובר 2"]
    }}
  ],
  "action_items": [
    {{
      "task": "תיאור המשימה",
      "owner": "מי אחראי (אם ידוע)",
      "deadline": "מועד (אם הוזכר)",
      "priority": "high/medium/low"
    }}
  ],
  "decisions_made": [
    {{
      "decision": "מה הוחלט",
      "context": "רקע קצר"
    }}
  ],
  "notable_quotes": [
    {{
      "speaker": "שם הדובר",
      "quote": "הציטוט המדויק",
      "significance": "למה זה חשוב"
    }}
  ],
  "speaker_profiles": [
    {{
      "name": "שם הדובר",
      "role_in_conversation": "תפקיד בשיחה (יוזם, מגיב, מקשה...)",
      "key_contributions": "תרומות עיקריות",
      "speaking_time_estimate": "הרבה/בינוני/מעט"
    }}
  ],
  "follow_up_questions": [
    "שאלה שכדאי לשאול בפגישה הבאה"
  ],
  "mood_and_tone": "תיאור קצר של האווירה הכללית (רשמי, ידידותי, מתוח...)",
  "infographic_text": "סיכום ויזואלי-טקסטואלי קצר עם אמוג'ים ומבנה ברור — מתאים לשליחה בוואטסאפ"
}}

🔴 חשוב: החזר JSON חוקי בלבד. בלי טקסט לפני או אחרי. בלי ```json.
אם אין מספיק מידע לסעיף מסוים — החזר רשימה ריקה [] או מחרוזת ריקה "".
"""

            print(f"📓 [NotebookLM] Generating deep analysis with {model_name}...")
            start_time = time.time()

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 4096,
                }
            )

            elapsed = time.time() - start_time
            print(f"📓 [NotebookLM] Analysis generated in {elapsed:.1f}s")

            if not response or not response.text:
                logger.error("[NotebookLM] Empty response from Gemini")
                return None

            # Parse the JSON response
            raw_text = response.text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                # Remove opening fence (```json or ```)
                first_newline = raw_text.index("\n")
                raw_text = raw_text[first_newline + 1:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

            try:
                analysis = json.loads(raw_text)
            except json.JSONDecodeError as e:
                logger.error(f"[NotebookLM] JSON parse error: {e}")
                logger.error(f"[NotebookLM] Raw response: {raw_text[:500]}")
                # Try to salvage — wrap in a basic structure
                analysis = {
                    "executive_summary": raw_text[:500],
                    "key_topics": [],
                    "action_items": [],
                    "decisions_made": [],
                    "notable_quotes": [],
                    "speaker_profiles": [],
                    "follow_up_questions": [],
                    "mood_and_tone": "",
                    "infographic_text": raw_text[:1000],
                    "_parse_error": True,
                }

            # Add metadata
            israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
            analysis["_metadata"] = {
                "provider": "gemini",
                "model": model_name,
                "generated_at": israel_time.isoformat(),
                "generation_time_seconds": round(elapsed, 1),
                "source_filename": filename,
                "speakers": speakers,
                "transcript_length": len(transcript_text),
            }

            print(f"📓 [NotebookLM] Analysis complete:")
            print(f"   Executive summary: {analysis.get('executive_summary', '')[:100]}...")
            print(f"   Topics: {len(analysis.get('key_topics', []))}")
            print(f"   Action items: {len(analysis.get('action_items', []))}")
            print(f"   Decisions: {len(analysis.get('decisions_made', []))}")
            print(f"   Quotes: {len(analysis.get('notable_quotes', []))}")
            print(f"   Speaker profiles: {len(analysis.get('speaker_profiles', []))}")

            return analysis

        except Exception as e:
            logger.error(f"[NotebookLM] Gemini analysis error: {e}")
            import traceback
            traceback.print_exc()
            return None


# ═══════════════════════════════════════════════════════════════════════
# NOTEBOOKLM API PROVIDER — Placeholder for future Google API
# ═══════════════════════════════════════════════════════════════════════

class NotebookLMApiProvider(NotebookLMProvider):
    """
    Placeholder for a future dedicated NotebookLM API from Google.
    When Google releases one, implement the API calls here.
    Switch via: NOTEBOOKLM_PROVIDER=notebooklm_api
    """

    def analyze(self, transcript_text: str, expert_summary: str,
                speakers: list, metadata: dict) -> Optional[Dict[str, Any]]:
        logger.warning("[NotebookLM] notebooklm_api provider not yet implemented. "
                       "Waiting for Google to release a public API.")
        print("⚠️ [NotebookLM] notebooklm_api provider is a placeholder. "
              "Set NOTEBOOKLM_PROVIDER=gemini to use the Gemini-based provider.")
        return None


# ═══════════════════════════════════════════════════════════════════════
# MAIN SERVICE CLASS
# ═══════════════════════════════════════════════════════════════════════

class NotebookLMService:
    """
    NotebookLM-style deep analysis service.

    Feature flags:
      - NOTEBOOKLM_ENABLED=true/false → enable/disable entirely
      - NOTEBOOKLM_PROVIDER=gemini|notebooklm_api → swap provider

    Usage:
        from app.services.notebooklm_service import notebooklm_service

        if notebooklm_service.is_enabled:
            result = notebooklm_service.analyze_recording(...)
    """

    def __init__(self):
        self._provider: Optional[NotebookLMProvider] = None
        self._folder_id: Optional[str] = None  # Drive folder for summaries
        self._configured = False

    @property
    def is_enabled(self) -> bool:
        """Check if the service is enabled via environment variable."""
        return os.environ.get("NOTEBOOKLM_ENABLED", "true").lower() == "true"

    @property
    def provider_name(self) -> str:
        """Current provider name."""
        return os.environ.get("NOTEBOOKLM_PROVIDER", "gemini")

    def _ensure_provider(self):
        """Lazy-initialize the provider based on config."""
        if self._provider is not None:
            return

        provider_name = self.provider_name
        if provider_name == "gemini":
            self._provider = GeminiNotebookProvider()
        elif provider_name == "notebooklm_api":
            self._provider = NotebookLMApiProvider()
        else:
            logger.warning(f"[NotebookLM] Unknown provider '{provider_name}', falling back to gemini")
            self._provider = GeminiNotebookProvider()

        print(f"📓 [NotebookLM] Provider: {provider_name} | Enabled: {self.is_enabled}")

    def analyze_recording(
        self,
        transcript_text: str,
        expert_summary: str,
        speakers: list,
        segments: list,
        metadata: dict,
        drive_memory_service=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a deep NotebookLM-style analysis of a recording.

        Args:
            transcript_text: Full transcript (all segments joined)
            expert_summary: Expert analysis text from audio pipeline
            speakers: List of identified speaker names
            segments: Raw transcript segments
            metadata: Dict with filename, timestamp, source, etc.
            drive_memory_service: DriveMemoryService for saving to Drive

        Returns:
            The analysis dict, or None if disabled/failed
        """
        if not self.is_enabled:
            print("ℹ️ [NotebookLM] Disabled (NOTEBOOKLM_ENABLED=false)")
            return None

        self._ensure_provider()

        # Build transcript text from segments if not provided
        if not transcript_text and segments:
            transcript_text = "\n".join(
                f"{seg.get('speaker', '?')}: {seg.get('text', '')}"
                for seg in segments
                if seg.get('text')
            )

        if not transcript_text or len(transcript_text.strip()) < 50:
            print("ℹ️ [NotebookLM] Transcript too short — skipping analysis")
            return None

        # Generate analysis
        analysis = self._provider.analyze(
            transcript_text=transcript_text,
            expert_summary=expert_summary,
            speakers=speakers,
            metadata=metadata,
        )

        if not analysis:
            return None

        # Save to Drive if service available
        if drive_memory_service:
            self._save_to_drive(analysis, metadata, drive_memory_service)

        return analysis

    def _save_to_drive(self, analysis: Dict[str, Any], metadata: dict,
                       drive_memory_service) -> Optional[str]:
        """Save the analysis as a JSON file to NotebookLM_Summaries/ on Drive."""
        try:
            # Ensure the NotebookLM_Summaries folder exists
            folder_id = self._ensure_folder(drive_memory_service)
            if not folder_id:
                logger.error("[NotebookLM] Could not create/find summaries folder")
                return None

            # Build filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            speakers_str = "_".join(
                (analysis.get("_metadata", {}).get("speakers", []) or ["unknown"])[:3]
            )
            # Sanitize
            speakers_str = "".join(
                c if c.isalnum() or c in ['_', '-'] else '_'
                for c in speakers_str
            )
            filename = f"notebooklm_{timestamp}_{speakers_str}.json"

            # Upload
            content = json.dumps(analysis, ensure_ascii=False, indent=2)
            file_stream = io.BytesIO(content.encode('utf-8'))

            from googleapiclient.http import MediaIoBaseUpload
            media = MediaIoBaseUpload(file_stream, mimetype='application/json')

            drive_memory_service._refresh_credentials_if_needed()
            file = drive_memory_service.service.files().create(
                body={
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': 'application/json',
                },
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')
            print(f"📓 [NotebookLM] Saved to Drive: {filename} (ID: {file_id})")
            return file_id

        except Exception as e:
            logger.error(f"[NotebookLM] Error saving to Drive: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _ensure_folder(self, drive_memory_service) -> Optional[str]:
        """Ensure the NotebookLM_Summaries folder exists in Drive."""
        if self._folder_id:
            return self._folder_id

        try:
            service = drive_memory_service.service
            parent_id = drive_memory_service.folder_id

            drive_memory_service._refresh_credentials_if_needed()

            # Check if folder exists
            query = (
                f"name = '{NOTEBOOKLM_FOLDER_NAME}' and "
                f"'{parent_id}' in parents and "
                f"mimeType = 'application/vnd.google-apps.folder' and "
                f"trashed = false"
            )
            results = service.files().list(
                q=query, fields="files(id, name)"
            ).execute()

            files = results.get('files', [])
            if files:
                self._folder_id = files[0]['id']
                print(f"📓 [NotebookLM] Summaries folder exists (ID: {self._folder_id})")
                return self._folder_id

            # Create folder
            folder_metadata = {
                'name': NOTEBOOKLM_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id],
            }
            folder = service.files().create(
                body=folder_metadata, fields='id'
            ).execute()

            self._folder_id = folder.get('id')
            print(f"📓 [NotebookLM] Created summaries folder (ID: {self._folder_id})")
            return self._folder_id

        except Exception as e:
            logger.error(f"[NotebookLM] Error ensuring folder: {e}")
            return None

    def search_summaries(
        self, query: str, drive_memory_service=None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search through saved NotebookLM summaries.

        Args:
            query: Search terms (keywords, speaker names, topics)
            drive_memory_service: DriveMemoryService instance
            limit: Max results to return

        Returns:
            List of matching analysis summaries
        """
        if not self.is_enabled:
            return []
        if not drive_memory_service or not drive_memory_service.is_configured:
            return []

        try:
            folder_id = self._ensure_folder(drive_memory_service)
            if not folder_id:
                return []

            drive_memory_service._refresh_credentials_if_needed()
            service = drive_memory_service.service

            # List recent analysis files
            file_query = (
                f"'{folder_id}' in parents and "
                f"mimeType = 'application/json' and "
                f"trashed = false"
            )
            results = service.files().list(
                q=file_query,
                orderBy='createdTime desc',
                pageSize=20,  # Fetch more than limit so we can filter
                fields="files(id, name, createdTime)"
            ).execute()

            files = results.get('files', [])
            if not files:
                return []

            # Download and search through files
            matching = []
            search_terms = [t.lower().strip() for t in query.split() if t.strip()]

            from googleapiclient.http import MediaIoBaseDownload

            for file_info in files:
                if len(matching) >= limit:
                    break

                try:
                    request = service.files().get_media(fileId=file_info['id'])
                    content_io = io.BytesIO()
                    downloader = MediaIoBaseDownload(content_io, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                    content_io.seek(0)
                    content = content_io.read().decode('utf-8')
                    analysis = json.loads(content)

                    # Search across all text fields
                    searchable = json.dumps(analysis, ensure_ascii=False).lower()
                    if any(term in searchable for term in search_terms):
                        matching.append({
                            "file_id": file_info['id'],
                            "filename": file_info['name'],
                            "created_time": file_info.get('createdTime', ''),
                            "executive_summary": analysis.get("executive_summary", ""),
                            "key_topics": analysis.get("key_topics", []),
                            "action_items": analysis.get("action_items", []),
                            "speakers": analysis.get("_metadata", {}).get("speakers", []),
                            "mood_and_tone": analysis.get("mood_and_tone", ""),
                        })

                except Exception as file_err:
                    logger.error(f"[NotebookLM] Error reading {file_info.get('name')}: {file_err}")
                    continue

            print(f"📓 [NotebookLM] Search '{query}': found {len(matching)} match(es)")
            return matching

        except Exception as e:
            logger.error(f"[NotebookLM] Search error: {e}")
            return []

    def format_infographic(self, analysis: Dict[str, Any]) -> str:
        """
        Format the analysis as a WhatsApp-friendly infographic message.

        Args:
            analysis: The structured analysis dict

        Returns:
            Formatted string for WhatsApp
        """
        if not analysis:
            return ""

        # Use the AI-generated infographic if available
        infographic = analysis.get("infographic_text", "")
        if infographic:
            return f"📓 *ניתוח NotebookLM:*\n\n{infographic}"

        # Fallback: build our own
        parts = []
        parts.append("📓 *ניתוח NotebookLM:*\n")

        # Executive summary
        summary = analysis.get("executive_summary", "")
        if summary:
            parts.append(f"📌 *תמצית:* {summary}\n")

        # Key topics
        topics = analysis.get("key_topics", [])
        if topics:
            parts.append("📋 *נושאים מרכזיים:*")
            for i, topic in enumerate(topics[:5], 1):
                name = topic.get("topic", "")
                if name:
                    parts.append(f"  {i}. {name}")
            parts.append("")

        # Action items
        actions = analysis.get("action_items", [])
        if actions:
            parts.append("✅ *פריטי פעולה:*")
            for action in actions[:5]:
                task = action.get("task", "")
                owner = action.get("owner", "")
                priority = action.get("priority", "")
                icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                line = f"  {icon} {task}"
                if owner:
                    line += f" ({owner})"
                parts.append(line)
            parts.append("")

        # Decisions
        decisions = analysis.get("decisions_made", [])
        if decisions:
            parts.append("🎯 *החלטות:*")
            for d in decisions[:3]:
                parts.append(f"  • {d.get('decision', '')}")
            parts.append("")

        # Mood
        mood = analysis.get("mood_and_tone", "")
        if mood:
            parts.append(f"🎭 *אווירה:* {mood}")

        return "\n".join(parts)

    def get_status(self) -> Dict[str, Any]:
        """Get service status for debugging."""
        return {
            "enabled": self.is_enabled,
            "provider": self.provider_name,
            "folder_id": self._folder_id,
            "configured": self._configured,
        }


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
notebooklm_service = NotebookLMService()
