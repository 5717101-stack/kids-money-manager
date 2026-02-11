"""
Google Drive Memory Service
Manages persistent conversation memory stored in Google Drive.
Uses in-memory caching with robust timestamp-based stale-while-revalidate logic.
"""

import os
import json
import copy
import tempfile
import io
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from io import BytesIO
import logging
from threading import Lock
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

MEMORY_FILE_NAME = "second_brain_memory.json"
DEFAULT_MEMORY_STRUCTURE = {
    "chat_history": [],
    "user_profile": {}
}


class DriveMemoryService:
    """Service for managing persistent memory in Google Drive with robust caching."""
    
    # Class-level in-memory cache
    # Structure: (memory_data: Dict, modified_time: datetime, file_id: str)
    _memory_cache: Optional[tuple] = None
    _cache_lock = Lock()  # Thread-safe cache access
    
    def __init__(self, folder_id: Optional[str] = None):
        """
        Initialize Drive Memory Service using OAuth 2.0 User Credentials.
        
        Args:
            folder_id: Google Drive folder ID where memory file is stored.
                      If None, uses DRIVE_MEMORY_FOLDER_ID from environment.
        
        Raises:
            ValueError: If required environment variables are missing
        """
        print("\n" + "=" * 60)
        print("--- DRIVE SERVICE INIT DEBUG ---")
        print("=" * 60)
        
        # Check folder ID
        self.folder_id = folder_id or os.environ.get("DRIVE_MEMORY_FOLDER_ID")
        print(f"DRIVE_MEMORY_FOLDER_ID: {'FOUND' if self.folder_id else 'MISSING'}")
        if self.folder_id:
            print(f"  Value: {self.folder_id[:20]}..." if len(self.folder_id) > 20 else f"  Value: {self.folder_id}")
        
        if not self.folder_id:
            error_msg = "DRIVE_MEMORY_FOLDER_ID not set. Memory service cannot work."
            logger.error(f"❌ {error_msg}")
            print(f"❌ {error_msg}")
            print("=" * 60 + "\n")
            raise ValueError(error_msg)
        
        # Check OAuth 2.0 credentials
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
        
        print(f"GOOGLE_CLIENT_ID: {'FOUND' if client_id else 'MISSING'}")
        print(f"GOOGLE_CLIENT_SECRET: {'FOUND' if client_secret else 'MISSING'}")
        print(f"GOOGLE_REFRESH_TOKEN: {'FOUND' if refresh_token else 'MISSING'}")
        
        # FAIL FAST: Raise ValueError immediately if any credential is missing
        missing_vars = []
        if not client_id:
            missing_vars.append("GOOGLE_CLIENT_ID")
        if not client_secret:
            missing_vars.append("GOOGLE_CLIENT_SECRET")
        if not refresh_token:
            missing_vars.append("GOOGLE_REFRESH_TOKEN")
        
        if missing_vars:
            error_msg = (
                f"Missing required Google Drive OAuth credentials: {', '.join(missing_vars)}. "
                f"Please set these environment variables."
            )
            logger.error(f"❌ {error_msg}")
            print(f"❌ {error_msg}")
            print("=" * 60 + "\n")
            raise ValueError(error_msg)
        
        print("=" * 60)
        print("✅ All required environment variables found")
        print("=" * 60 + "\n")
        
        try:
            # Initialize OAuth 2.0 credentials using os.environ values
            print("🔐 Initializing OAuth 2.0 credentials...")
            self.creds = Credentials(
                None,  # No access token initially
                refresh_token=refresh_token,  # From os.environ
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,  # From os.environ
                client_secret=client_secret  # From os.environ
            )
            print("✅ Credentials object created")
            
            # Refresh token to get initial access token
            if self.creds.expired and self.creds.refresh_token:
                logger.info("🔄 Refreshing OAuth token on initialization...")
                print("🔄 Refreshing OAuth token on initialization...")
                self.creds.refresh(Request())
                logger.info("✅ OAuth token refreshed successfully")
                print("✅ OAuth token refreshed successfully")
            
            # Build Drive service with OAuth credentials
            print("🔨 Building Drive API service...")
            self.service = build('drive', 'v3', credentials=self.creds)
            self.is_configured = True
            logger.info("✅ Drive Memory Service initialized successfully (OAuth 2.0)")
            print("✅ Drive Memory Service initialized successfully (OAuth 2.0)")
            
            # Ensure audio_archive folder exists
            print("📁 Ensuring audio_archive folder exists...")
            self._ensure_audio_archive_folder()
            print("✅ Drive Memory Service fully initialized\n")
        except Exception as e:
            error_msg = f"Failed to initialize Drive Memory Service: {e}"
            logger.error(f"❌ {error_msg}")
            print(f"❌ {error_msg}")
            import traceback
            print("=" * 60)
            print("FULL TRACEBACK:")
            print("=" * 60)
            traceback.print_exc()
            print("=" * 60 + "\n")
            # Re-raise to fail fast
            raise ValueError(error_msg) from e
    
    def _refresh_credentials_if_needed(self):
        """
        Refresh OAuth credentials if they are expired.
        This should be called before any API operation.
        """
        if not self.creds:
            return
        
        try:
            if self.creds.expired and self.creds.refresh_token:
                logger.debug("🔄 OAuth token expired, refreshing...")
                self.creds.refresh(Request())
                logger.debug("✅ OAuth token refreshed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to refresh OAuth token: {e}")
            raise
    
    def _ensure_audio_archive_folder(self) -> Optional[str]:
        """
        Ensure the audio_archive subfolder exists in the main memory folder.
        Creates it if it doesn't exist.
        
        Returns:
            Folder ID of audio_archive, or None if creation failed
        """
        if not self.is_configured or not self.service:
            return None
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        try:
            # Check if audio_archive folder already exists
            query = f"name = 'audio_archive' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Audio archive folder already exists (ID: {folder_id})")
                return folder_id
            
            # Create audio_archive folder
            folder_metadata = {
                'name': 'audio_archive',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created audio_archive folder (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring audio_archive folder: {e}")
            return None
    
    def _ensure_transcripts_folder(self) -> Optional[str]:
        """
        Ensure the Transcripts subfolder exists in the main memory folder.
        Creates it if it doesn't exist.
        
        Returns:
            Folder ID of Transcripts folder, or None if creation failed
        """
        if not self.is_configured or not self.service:
            return None
        
        self._refresh_credentials_if_needed()
        
        try:
            # Check if Transcripts folder already exists
            query = f"name = 'Transcripts' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Transcripts folder already exists (ID: {folder_id})")
                return folder_id

            # Create Transcripts folder
            folder_metadata = {
                'name': 'Transcripts',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created Transcripts folder (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring Transcripts folder: {e}")
            return None
    
    def save_transcript(self, transcript_data: dict, speakers: list = None) -> Optional[str]:
        """
        Save a transcript as a separate JSON file in the Transcripts folder.
        
        Args:
            transcript_data: The transcript JSON (with segments)
            speakers: List of speaker names for the filename
            
        Returns:
            File ID of saved transcript, or None if failed
        """
        if not self.is_configured or not self.service:
            return None
        
        self._refresh_credentials_if_needed()
        
        transcripts_folder_id = self._ensure_transcripts_folder()
        if not transcripts_folder_id:
            logger.error("❌ Cannot save transcript: Transcripts folder not available")
            return None
        
        try:
            # Create filename with timestamp and speakers
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            speakers_str = "_".join(speakers[:3]) if speakers else "unknown"
            # Sanitize filename
            speakers_str = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in speakers_str)
            filename = f"transcript_{timestamp}_{speakers_str}.json"
            
            # Prepare content
            content = json.dumps(transcript_data, ensure_ascii=False, indent=2)
            file_stream = io.BytesIO(content.encode('utf-8'))
            
            # Upload to Drive
            file_metadata = {
                'name': filename,
                'parents': [transcripts_folder_id],
                'mimeType': 'application/json'
            }
            
            media = MediaIoBaseUpload(file_stream, mimetype='application/json')
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"✅ Saved transcript to Drive: {filename} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            return None
    
    def get_recent_transcripts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent transcripts from the Transcripts folder.
        
        Args:
            limit: Maximum number of transcripts to retrieve
            
        Returns:
            List of transcript dictionaries with metadata and content
        """
        if not self.is_configured or not self.service:
            return []
        
        self._refresh_credentials_if_needed()
        
        transcripts_folder_id = self._ensure_transcripts_folder()
        if not transcripts_folder_id:
            return []
        
        try:
            # List transcript files, ordered by creation time (newest first)
            query = f"'{transcripts_folder_id}' in parents and mimeType = 'application/json' and trashed = false"
            results = self.service.files().list(
                q=query,
                orderBy='createdTime desc',
                pageSize=limit,
                fields="files(id, name, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                logger.info("ℹ️  No transcripts found in Transcripts folder")
                return []
            
            logger.info(f"📥 Found {len(files)} transcript(s)")
            
            # Download and parse each transcript
            transcripts = []
            for file_info in files:
                file_id = file_info.get('id')
                filename = file_info.get('name', '')
                created_time = file_info.get('createdTime', '')
                
                try:
                    # Download file content
                    request = self.service.files().get_media(fileId=file_id)
                    file_content = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_content, request)
                    
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    
                    file_content.seek(0)
                    content = file_content.read().decode('utf-8')
                    transcript_data = json.loads(content)
                    
                    transcripts.append({
                        'file_id': file_id,
                        'filename': filename,
                        'created_time': created_time,
                        'content': transcript_data
                    })
                    logger.info(f"✅ Loaded transcript: {filename}")
                    
                except Exception as e:
                    logger.error(f"❌ Error loading transcript {filename}: {e}")
                    continue
            
            return transcripts
            
        except Exception as e:
            logger.error(f"❌ Error getting recent transcripts: {e}")
            return []
    
    def search_transcripts(self, search_terms: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search through transcripts for specific terms (names, topics).
        
        Args:
            search_terms: List of terms to search for (names, keywords)
            limit: Maximum number of matching transcripts to return
            
        Returns:
            List of matching transcript segments with context
        """
        # Get recent transcripts
        transcripts = self.get_recent_transcripts(limit=20)  # Get more to search through
        
        if not transcripts:
            return []
        
        matching_results = []
        search_terms_lower = [term.lower() for term in search_terms]
        
        for transcript in transcripts:
            content = transcript.get('content', {})
            segments = content.get('segments', [])
            filename = transcript.get('filename', '')
            created_time = transcript.get('created_time', '')
            
            matching_segments = []
            all_speakers = set()
            
            for segment in segments:
                speaker = segment.get('speaker', '')
                text = segment.get('text', '')
                
                if speaker:
                    all_speakers.add(speaker)
                
                # Check if any search term matches speaker or text
                speaker_lower = speaker.lower()
                text_lower = text.lower()
                
                for term in search_terms_lower:
                    if term in speaker_lower or term in text_lower:
                        matching_segments.append(segment)
                        break
            
            if matching_segments:
                matching_results.append({
                    'filename': filename,
                    'created_time': created_time,
                    'speakers': list(all_speakers),
                    'matching_segments': matching_segments,
                    'total_segments': len(segments)
                })
        
        logger.info(f"🔍 Found {len(matching_results)} matching transcript(s) for terms: {search_terms}")
        return matching_results[:limit]
    
    def update_transcript_speaker(self, speaker_id: str, real_name: str, limit: int = 5) -> int:
        """
        RETROACTIVE TRANSCRIPT UPDATE: Replace generic speaker IDs with real names.
        
        Finds recent transcripts containing the speaker_id and replaces all occurrences
        with the real name provided by the user.
        
        Args:
            speaker_id: The generic ID (e.g., "Unknown Speaker 2", "Speaker B")
            real_name: The real name to replace with (e.g., "שי", "Miri")
            limit: Maximum number of recent transcripts to update
            
        Returns:
            Number of transcripts updated
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive service not configured - cannot update transcripts")
            return 0
        
        self._refresh_credentials_if_needed()
        
        # Get the Transcripts folder
        transcripts_folder_id = self._ensure_transcripts_folder()
        if not transcripts_folder_id:
            logger.error("❌ Transcripts folder not available")
            return 0
        
        updated_count = 0
        
        try:
            # List recent transcripts
            query = f"'{transcripts_folder_id}' in parents and mimeType = 'application/json' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
                pageSize=limit
            ).execute()
            
            files = results.get('files', [])
            if not files:
                logger.info("ℹ️  No transcripts found to update")
                return 0
            
            logger.info(f"🔄 Checking {len(files)} recent transcript(s) for '{speaker_id}'...")
            
            for file_info in files:
                file_id = file_info.get('id')
                filename = file_info.get('name', '')
                
                try:
                    # Download transcript content
                    file_content = self.service.files().get_media(fileId=file_id).execute()
                    transcript_data = json.loads(file_content.decode('utf-8'))
                    
                    # Check if this transcript contains the speaker_id
                    segments = transcript_data.get('segments', [])
                    has_changes = False
                    
                    for segment in segments:
                        current_speaker = segment.get('speaker', '')
                        if current_speaker.lower() == speaker_id.lower():
                            segment['speaker'] = real_name
                            has_changes = True
                    
                    if has_changes:
                        # Upload updated transcript back to Drive
                        updated_content = json.dumps(transcript_data, ensure_ascii=False, indent=2)
                        
                        from googleapiclient.http import MediaIoBaseUpload
                        media = MediaIoBaseUpload(
                            io.BytesIO(updated_content.encode('utf-8')),
                            mimetype='application/json',
                            resumable=True
                        )
                        
                        self.service.files().update(
                            fileId=file_id,
                            media_body=media
                        ).execute()
                        
                        updated_count += 1
                        logger.info(f"✅ Updated transcript '{filename}': {speaker_id} -> {real_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error updating transcript {filename}: {e}")
                    continue
            
            logger.info(f"📝 Retroactive update complete: {updated_count} transcript(s) updated")
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Error in retroactive transcript update: {e}")
            return 0
    
    def update_summary_speaker(self, speaker_id: str, real_name: str, limit: int = 5) -> int:
        """
        RETROACTIVE SUMMARY UPDATE: Replace generic speaker IDs with real names in expert analysis summaries.
        
        This ensures that future RAG queries use correct names when searching through
        summaries stored in the memory file.
        
        Args:
            speaker_id: The generic ID (e.g., "Unknown Speaker 2", "Speaker B", "דובר 2")
            real_name: The real name to replace with (e.g., "שי", "Miri")
            limit: Maximum number of recent memory entries to update
            
        Returns:
            Number of summaries updated
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive service not configured - cannot update summaries")
            return 0
        
        self._refresh_credentials_if_needed()
        
        updated_count = 0
        
        try:
            # Get current memory
            memory = self.get_memory()
            chat_history = memory.get('chat_history', [])
            
            if not chat_history:
                logger.info("ℹ️  No chat history found to update")
                return 0
            
            # Look at recent audio entries (they contain transcripts and summaries)
            recent_audio_entries = []
            for i, entry in enumerate(reversed(chat_history)):
                if entry.get('type') == 'audio':
                    recent_audio_entries.append((len(chat_history) - 1 - i, entry))
                    if len(recent_audio_entries) >= limit:
                        break
            
            logger.info(f"🔄 Checking {len(recent_audio_entries)} recent audio entries for '{speaker_id}'...")
            
            for idx, entry in recent_audio_entries:
                has_changes = False
                
                # Update transcript segments
                transcript = entry.get('transcript', {})
                segments = transcript.get('segments', [])
                for segment in segments:
                    current_speaker = segment.get('speaker', '')
                    if current_speaker.lower() == speaker_id.lower():
                        segment['speaker'] = real_name
                        has_changes = True
                
                # Update speakers list
                speakers = entry.get('speakers', [])
                for i, speaker in enumerate(speakers):
                    if speaker.lower() == speaker_id.lower():
                        speakers[i] = real_name
                        has_changes = True
                
                # Update expert_analysis if present (for future queries)
                expert_analysis = entry.get('expert_analysis', {})
                if expert_analysis:
                    raw_analysis = expert_analysis.get('raw_analysis', '')
                    if speaker_id.lower() in raw_analysis.lower():
                        # Replace variations of speaker ID with real name
                        import re
                        # Case-insensitive replacement
                        pattern = re.compile(re.escape(speaker_id), re.IGNORECASE)
                        updated_analysis = pattern.sub(real_name, raw_analysis)
                        expert_analysis['raw_analysis'] = updated_analysis
                        has_changes = True
                        
                        # Also update speakers list in expert_analysis
                        analysis_speakers = expert_analysis.get('speakers', [])
                        for i, speaker in enumerate(analysis_speakers):
                            if speaker.lower() == speaker_id.lower():
                                analysis_speakers[i] = real_name
                
                if has_changes:
                    # Update the entry in place
                    chat_history[idx] = entry
                    updated_count += 1
                    logger.info(f"✅ Updated memory entry {idx}: {speaker_id} -> {real_name}")
            
            if updated_count > 0:
                # Save updated memory back to Drive
                memory['chat_history'] = chat_history
                self._upload_to_drive(memory)
                logger.info(f"📝 Retroactive summary update complete: {updated_count} entries updated")
            else:
                logger.info("ℹ️  No matching speaker IDs found in recent entries")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Error in retroactive summary update: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    # ================================================================
    # CURSOR INBOX: Remote Execution via Google Drive
    # ================================================================
    
    def _ensure_cursor_inbox_folder(self) -> Optional[str]:
        """
        Ensure the Cursor_Inbox subfolder exists in the main memory folder.
        This folder is monitored by the local Mac bridge for remote execution.
        
        Returns:
            Folder ID of Cursor_Inbox folder, or None if creation failed
        """
        if not self.is_configured or not self.service:
            return None
        
        self._refresh_credentials_if_needed()
        
        try:
            # Check if Cursor_Inbox folder already exists
            query = f"name = 'Cursor_Inbox' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Cursor_Inbox folder already exists (ID: {folder_id})")
                return folder_id

            # Create Cursor_Inbox folder
            folder_metadata = {
                'name': 'Cursor_Inbox',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created Cursor_Inbox folder (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring Cursor_Inbox folder: {e}")
            return None
    
    def save_cursor_command(self, prompt_content: str) -> Optional[str]:
        """
        Save a Cursor command to pending_task.md in the Cursor_Inbox folder.
        This file will be monitored by the local Mac bridge for remote execution.
        
        Args:
            prompt_content: The coding prompt to execute in Cursor
            
        Returns:
            File ID of saved command, or None if failed
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive service not configured - cannot save Cursor command")
            return None
        
        self._refresh_credentials_if_needed()
        
        # Get the Cursor_Inbox folder
        inbox_folder_id = self._ensure_cursor_inbox_folder()
        if not inbox_folder_id:
            logger.error("❌ Cannot save Cursor command: Cursor_Inbox folder not available")
            return None
        
        try:
            filename = "pending_task.md"
            
            # Check if file already exists (we want to overwrite)
            query = f"name = '{filename}' and '{inbox_folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            existing_files = results.get('files', [])
            
            # Prepare content with UTF-8 encoding
            file_content = prompt_content.encode('utf-8')
            
            from googleapiclient.http import MediaIoBaseUpload
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype='text/markdown',
                resumable=True
            )
            
            if existing_files:
                # Update existing file (overwrite)
                file_id = existing_files[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                logger.info(f"✅ Updated pending_task.md (overwrite mode)")
            else:
                # Create new file
                file_metadata = {
                    'name': filename,
                    'parents': [inbox_folder_id],
                    'mimeType': 'text/markdown'
                }
                
                result = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                file_id = result.get('id')
                logger.info(f"✅ Created pending_task.md (ID: {file_id})")
            
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Error saving Cursor command: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_pending_cursor_command(self) -> Optional[dict]:
        """
        Check if there's a pending_task.md in Cursor_Inbox and return its content.
        Used by the local bridge to poll for new tasks via HTTP instead of filesystem.
        
        Returns:
            Dict with 'content' and 'file_id' if a task exists, None otherwise
        """
        if not self.is_configured or not self.service:
            return None
        
        self._refresh_credentials_if_needed()
        
        inbox_folder_id = self._ensure_cursor_inbox_folder()
        if not inbox_folder_id:
            return None
        
        try:
            query = f"name = 'pending_task.md' and '{inbox_folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return None
            
            file_id = files[0]['id']
            
            # Download the file content
            content = self.service.files().get_media(fileId=file_id).execute()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            if not content or not content.strip():
                return None
            
            return {
                'content': content.strip(),
                'file_id': file_id,
                'modified_time': files[0].get('modifiedTime', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking pending cursor command: {e}")
            return None
    
    def ack_cursor_command(self) -> bool:
        """
        Acknowledge (delete) the pending_task.md after it has been processed.
        
        Returns:
            True if successfully deleted, False otherwise
        """
        if not self.is_configured or not self.service:
            return False
        
        self._refresh_credentials_if_needed()
        
        inbox_folder_id = self._ensure_cursor_inbox_folder()
        if not inbox_folder_id:
            return False
        
        try:
            query = f"name = 'pending_task.md' and '{inbox_folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return True  # Already gone
            
            # Delete the file (permanently)
            self.service.files().delete(fileId=files[0]['id']).execute()
            logger.info(f"✅ Deleted pending_task.md after acknowledgment")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error acknowledging cursor command: {e}")
            return False
    
    def upload_audio_to_archive(
        self,
        audio_path: str = None,
        audio_bytes: bytes = None,
        audio_file_obj = None,
        filename: str = None,
        mime_type: str = None
    ) -> Optional[Dict[str, str]]:
        """
        Upload an audio file to the audio_archive folder in Drive.
        
        NO TRY-EXCEPT: Let errors bubble up for transparent debugging.
        
        Args:
            audio_path: Path to the audio file on disk (optional if audio_file_obj or audio_bytes provided)
            audio_bytes: Binary audio data (optional if audio_file_obj or audio_path provided)
            audio_file_obj: File-like object (BytesIO stream) (optional if audio_bytes or audio_path provided)
            filename: Optional filename (uses path basename if not provided)
            mime_type: Optional MIME type (auto-detected from extension if not provided)
        
        Returns:
            Dictionary with 'file_id' and 'web_content_link', or None if upload failed
        
        Raises:
            HttpError: If Google Drive API call fails
            ValueError: If no audio source provided or service not configured
            TypeError: If stream handling fails
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot upload audio.")
            raise ValueError("Drive Memory Service not configured")
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        print("🔍 Checking for audio_archive folder...")
        # Ensure audio_archive folder exists
        archive_folder_id = self._ensure_audio_archive_folder()
        if not archive_folder_id:
            logger.error("❌ Cannot upload audio: audio_archive folder not available")
            raise ValueError("audio_archive folder not available")
        print(f"✅ Audio archive folder verified (ID: {archive_folder_id})")
        
        # Get file content - prioritize file_obj, then bytes, then path
        file_obj = None
        if audio_file_obj:
            print(f"📦 Using provided file-like object (stream)")
            file_obj = audio_file_obj
            # Ensure stream is at position 0
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            # Get size if possible (without consuming the stream)
            try:
                if hasattr(file_obj, 'getvalue'):
                    # BytesIO.getvalue() doesn't consume the stream
                    file_size = len(file_obj.getvalue())
                    print(f"   Stream size: {file_size} bytes")
                elif hasattr(file_obj, 'read'):
                    # Save current position
                    current_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
                    # Read to get size, then reset
                    content = file_obj.read()
                    file_size = len(content)
                    # Reset to beginning
                    file_obj.seek(0)
                    print(f"   Stream size: {file_size} bytes")
                else:
                    file_size = "unknown"
                    print(f"   Stream size: {file_size} (cannot determine)")
            except Exception as size_error:
                print(f"   ⚠️  Could not determine stream size: {size_error}")
                file_size = "unknown"
                # Ensure stream is at position 0
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
            if not filename:
                filename = "audio_message.ogg"  # Default for WhatsApp audio
        elif audio_bytes:
            print(f"📦 Using provided audio bytes (size: {len(audio_bytes)} bytes)")
            file_obj = io.BytesIO(audio_bytes)
            if not filename:
                filename = "audio_message.ogg"  # Default for WhatsApp audio
        elif audio_path:
            print(f"📂 Reading audio file from path: {audio_path}")
            with open(audio_path, 'rb') as f:
                file_content = f.read()
            print(f"✅ Audio file read successfully. Size: {len(file_content)} bytes")
            file_obj = io.BytesIO(file_content)
            if not filename:
                filename = Path(audio_path).name
        else:
            error_msg = "Either audio_path, audio_bytes, or audio_file_obj must be provided"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # Determine MIME type from extension if not provided
        if not mime_type:
            mime_type_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.wave': 'audio/wav',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.ogg': 'audio/ogg',
                '.oga': 'audio/ogg',
                '.flac': 'audio/flac',
                '.mp4': 'audio/mp4',
            }
            
            if audio_path:
                file_ext = Path(audio_path).suffix.lower()
            else:
                # Try to infer from filename
                file_ext = Path(filename).suffix.lower() if filename else '.ogg'
            
            mime_type = mime_type_map.get(file_ext, 'audio/ogg')  # Default to OGG for WhatsApp
        
        # Get file size for sanity check
        if hasattr(file_obj, 'getvalue'):
            audio_content_size = len(file_obj.getvalue())
        elif hasattr(file_obj, 'read'):
            current_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
            content = file_obj.read()
            audio_content_size = len(content)
            file_obj.seek(0)
        else:
            audio_content_size = "unknown"
        
        print(f"📤 Preparing to upload {audio_content_size} bytes to Folder ID: {self.folder_id}")
        print(f"   Filename: {filename}")
        print(f"   MIME type: {mime_type}")
        
        # Upload to Drive using MediaIoBaseUpload for file-like objects
        file_metadata = {
            'name': filename,
            'parents': [archive_folder_id]
        }
        
        # CRITICAL: Ensure stream is at position 0 before upload
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            print(f"   Stream position reset to: {file_obj.tell()}")
        elif hasattr(file_obj, 'tell'):
            current_pos = file_obj.tell()
            if current_pos != 0:
                print(f"   ⚠️  Warning: Stream position is {current_pos}, not 0")
        
        print(f"   Creating MediaIoBaseUpload with mime_type={mime_type}, resumable=True")
        media = MediaIoBaseUpload(
            file_obj,
            mimetype=mime_type,
            resumable=True
        )
        
        print(f"   Calling Drive API files().create()...")
        # NO TRY-EXCEPT: Let HttpError bubble up for transparent debugging
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webContentLink,webViewLink'
        ).execute()
        print(f"   ✅ Drive API call successful")
        
        file_id = file.get('id')
        web_content_link = file.get('webContentLink', '')
        web_view_link = file.get('webViewLink', '')
        
        logger.info(f"✅ Uploaded audio to archive: {filename} (ID: {file_id})")
        logger.debug(f"   Web content link: {web_content_link}")
        print(f"✅ Upload successful. File ID: {file_id}")
        print(f"   Web content link: {web_content_link}")
        
        return {
            'file_id': file_id,
            'web_content_link': web_content_link,
            'web_view_link': web_view_link,
            'filename': filename
        }
    
    def upload_to_context_folder(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str
    ) -> Optional[Dict[str, str]]:
        """
        Upload a file to the Second_Brain_Context folder in Google Drive.
        This makes the file immediately available for Knowledge Base queries.
        
        Args:
            file_bytes: Binary content of the file
            filename: Display name for the file in Drive
            mime_type: MIME type of the file (e.g., 'application/pdf', 'image/jpeg')
        
        Returns:
            Dictionary with 'file_id', 'filename', and 'web_view_link', or None if upload failed
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot upload to context.")
            return None
        
        self._refresh_credentials_if_needed()
        
        # Get the Second_Brain_Context folder ID
        context_folder_id = os.environ.get("CONTEXT_FOLDER_ID")
        if not context_folder_id:
            logger.error("❌ CONTEXT_FOLDER_ID not set — cannot upload to context folder")
            return None
        
        try:
            # ── DRIVE-LEVEL DEDUP: skip if file with same name already exists ──
            try:
                query = f"name = '{filename}' and '{context_folder_id}' in parents and trashed = false"
                existing = self.service.files().list(
                    q=query, fields="files(id, name)", pageSize=1
                ).execute().get('files', [])
                if existing:
                    print(f"⚠️  File '{filename}' already exists in context folder (ID: {existing[0]['id']}) — skipping duplicate upload")
                    return {
                        'file_id': existing[0]['id'],
                        'filename': filename,
                        'web_view_link': '',
                        'duplicate': True
                    }
            except Exception as dedup_err:
                print(f"⚠️  Dedup check failed (uploading anyway): {dedup_err}")
            
            print(f"📤 Uploading '{filename}' ({mime_type}) to Second_Brain_Context...")
            
            file_obj = io.BytesIO(file_bytes)
            media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
            
            file_metadata = {
                'name': filename,
                'parents': [context_folder_id]
            }
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_view_link = file.get('webViewLink', '')
            
            print(f"✅ Context file uploaded: {filename} (ID: {file_id})")
            logger.info(f"✅ Context file uploaded: {filename} (ID: {file_id})")
            
            return {
                'file_id': file_id,
                'filename': filename,
                'web_view_link': web_view_link
            }
        except Exception as e:
            logger.error(f"❌ Failed to upload to context folder: {e}")
            print(f"❌ Failed to upload to context folder: {e}")
            import traceback
            traceback.print_exc()
            return None

    def upload_voice_signature(self, file_path: str, person_name: str) -> Optional[str]:
        """
        Upload a voice signature (audio sample) to the Voice_Signatures folder in Drive.
        
        Args:
            file_path: Path to the audio file on disk
            person_name: Name of the person (will be sanitized and used as filename)
        
        Returns:
            File ID of the uploaded file, or None if upload failed
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot upload voice signature.")
            return None
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        # Sanitize person name for filename (remove invalid characters)
        import re
        sanitized_name = re.sub(r'[^\w\s-]', '', person_name).strip()
        sanitized_name = re.sub(r'[-\s]+', '_', sanitized_name)  # Replace spaces/hyphens with underscore
        if not sanitized_name:
            sanitized_name = "unknown_person"
        
        filename = f"{sanitized_name}.mp3"
        
        print(f"🎤 Uploading voice signature for '{person_name}' as '{filename}'...")
        
        # Ensure Voice_Signatures folder exists
        voice_signatures_folder_id = self._ensure_voice_signatures_folder()
        if not voice_signatures_folder_id:
            logger.error("❌ Cannot upload voice signature: Voice_Signatures folder not available")
            return None
        
        # Read audio file
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            print(f"✅ Audio file read successfully. Size: {len(file_content)} bytes")
        except Exception as e:
            logger.error(f"❌ Error reading audio file: {e}")
            return None
        
        file_obj = io.BytesIO(file_content)
        
        # Upload to Drive
        file_metadata = {
            'name': filename,
            'parents': [voice_signatures_folder_id]
        }
        
        media = MediaIoBaseUpload(
            file_obj,
            mimetype='audio/mpeg',
            resumable=False
        )
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"✅ Uploaded voice signature: {filename} (ID: {file_id})")
            print(f"✅ Voice signature uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"❌ Error uploading voice signature: {e}")
            print(f"❌ Error uploading voice signature: {e}")
            return None
    
    def _ensure_voice_signatures_folder(self) -> Optional[str]:
        """
        Ensure the Voice_Signatures subfolder exists in the main memory folder.
        Creates it if it doesn't exist.
        
        Returns:
            Folder ID of Voice_Signatures, or None if creation failed
        """
        if not self.is_configured or not self.service:
            return None
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        try:
            # Check if Voice_Signatures folder already exists
            query = f"name = 'Voice_Signatures' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Voice_Signatures folder already exists (ID: {folder_id})")
                return folder_id
            
            # Create Voice_Signatures folder
            folder_metadata = {
                'name': 'Voice_Signatures',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created Voice_Signatures folder (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring Voice_Signatures folder: {e}")
            return None
    
    def get_known_speaker_names(self) -> List[str]:
        """
        Get list of known speaker names from Voice_Signatures folder.
        This is a lightweight call that doesn't download files.
        
        Returns:
            List of speaker names (e.g., ['Miri', 'Itzik', 'Dan'])
        """
        if not self.is_configured or not self.service:
            return []
        
        self._refresh_credentials_if_needed()
        
        voice_signatures_folder_id = self._ensure_voice_signatures_folder()
        if not voice_signatures_folder_id:
            return []
        
        try:
            query = f"'{voice_signatures_folder_id}' in parents and mimeType = 'audio/mpeg' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(name)"
            ).execute()
            
            files = results.get('files', [])
            names = []
            for file_info in files:
                filename = file_info.get('name', '')
                # Extract person name from filename (remove .mp3 extension)
                name = filename.replace('.mp3', '').replace('_', ' ').strip()
                if name:
                    names.append(name)
            
            logger.info(f"📋 Known speaker names: {names}")
            return names
            
        except Exception as e:
            logger.error(f"❌ Error getting known speaker names: {e}")
            return []
    
    def get_voice_signatures(self, max_signatures: int = 2) -> List[Dict[str, str]]:
        """
        Retrieve voice signature files from the Voice_Signatures folder.
        Downloads each file to a temporary location.
        
        MEMORY OPTIMIZATION: Limited to max_signatures to prevent OOM on low-memory hosts.
        
        Args:
            max_signatures: Maximum number of voice signatures to download (default: 2)
                           Set to 0 to disable multimodal comparison entirely.
        
        Returns:
            List of dictionaries with 'name' (person name) and 'file_path' (temp file path)
            Example: [{'name': 'John', 'file_path': '/tmp/voice_john_abc123.mp3'}, ...]
        """
        # MEMORY OPTIMIZATION: Allow disabling multimodal comparison
        if max_signatures <= 0:
            logger.info("ℹ️  Voice signature download disabled (max_signatures=0)")
            return []
        
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot retrieve voice signatures.")
            return []
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        # Get Voice_Signatures folder ID
        voice_signatures_folder_id = self._ensure_voice_signatures_folder()
        if not voice_signatures_folder_id:
            logger.warning("⚠️  Voice_Signatures folder not found. No voice signatures available.")
            return []
        
        try:
            # List all MP3 files in Voice_Signatures folder
            query = f"'{voice_signatures_folder_id}' in parents and mimeType = 'audio/mpeg' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                logger.info("ℹ️  No voice signatures found in Voice_Signatures folder")
                return []
            
            logger.info(f"📥 Found {len(files)} voice signature(s)")
            
            # MEMORY OPTIMIZATION: Limit number of signatures
            if len(files) > max_signatures:
                logger.warning(f"⚠️  Limiting to {max_signatures} voice signatures (found {len(files)}) to save memory")
                files = files[:max_signatures]
            
            # Download each file to a temporary location
            voice_signatures = []
            for file_info in files:
                file_id = file_info.get('id')
                filename = file_info.get('name', 'unknown.mp3')
                file_size = file_info.get('size', 'unknown')
                
                # Extract person name from filename (remove .mp3 extension)
                person_name = filename.replace('.mp3', '').replace('_', ' ').strip()
                
                try:
                    logger.info(f"📥 Downloading voice signature: {person_name} (size: {file_size} bytes)")
                    
                    # Download file to temporary location
                    request = self.service.files().get_media(fileId=file_id)
                    file_content = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_content, request)
                    
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    
                    # Save to temporary file
                    file_content.seek(0)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', prefix=f'voice_{person_name}_') as tmp_file:
                        tmp_file.write(file_content.read())
                        tmp_path = tmp_file.name
                    
                    # MEMORY OPTIMIZATION: Clear BytesIO buffer immediately
                    file_content.close()
                    del file_content
                    
                    voice_signatures.append({
                        'name': person_name,
                        'file_path': tmp_path
                    })
                    logger.info(f"✅ Downloaded voice signature: {person_name} -> {tmp_path}")
                    
                except Exception as e:
                    logger.error(f"❌ Error downloading voice signature {filename}: {e}")
                    continue
            
            logger.info(f"✅ Retrieved {len(voice_signatures)} voice signature(s) (limited to {max_signatures})")
            return voice_signatures
            
        except Exception as e:
            logger.error(f"❌ Error retrieving voice signatures: {e}")
            return []
    
    def _find_memory_file(self) -> Optional[str]:
        """
        Find the memory file in the configured Drive folder.
        
        Returns:
            File ID if found, None otherwise
        """
        if not self.is_configured or not self.service:
            return None
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        try:
            # Explicitly exclude trashed files
            query = f"name = '{MEMORY_FILE_NAME}' and '{self.folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, trashed)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                file_id = files[0]['id']
                logger.debug(f"✅ Found memory file: {MEMORY_FILE_NAME} (ID: {file_id})")
                return file_id
            logger.debug(f"📝 Memory file '{MEMORY_FILE_NAME}' not found in folder")
            return None
        except HttpError as e:
            logger.error(f"❌ DRIVE API ERROR finding memory file: {e}")
            logger.error(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")
            logger.error(f"   Status code: {e.resp.status if hasattr(e, 'resp') else 'N/A'}")
            return None
    
    def _download_file(self, file_id: str, is_google_docs_file: bool = False) -> Dict[str, Any]:
        """
        Download and parse memory file from Google Drive.
        
        CRITICAL: This method does NOT return DEFAULT_MEMORY_STRUCTURE on error.
        It raises exceptions to prevent data loss.
        
        Args:
            file_id: Google Drive file ID
            is_google_docs_file: Whether this is a Google Docs file (needs export)
        
        Returns:
            Parsed memory dictionary
        
        Raises:
            HttpError: If download fails
            json.JSONDecodeError: If JSON parsing fails
            ValueError: If JSON structure is invalid
        """
        try:
            # Download or export the file
            if is_google_docs_file:
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/json'
                )
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            file_content = BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Parse JSON
            file_content.seek(0)
            content_str = file_content.read().decode('utf-8')
            
            # Debug logging: Print content length
            content_length = len(content_str)
            logger.info(f"📊 Downloaded file content length: {content_length} characters")
            
            # Validate JSON structure
            try:
                memory_data = json.loads(content_str)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON PARSING ERROR for file {file_id}: {e}")
                logger.error(f"   Error message: {str(e)}")
                logger.error(f"   Error position: line {e.lineno}, column {e.colno}" if hasattr(e, 'lineno') else f"   Error position: {e.pos}")
                logger.error(f"   Content length: {content_length} characters")
                logger.error(f"   Content preview (first 100 chars): {content_str[:100]}")
                logger.error(f"   Content preview (last 100 chars): {content_str[-100:] if len(content_str) > 100 else content_str}")
                # Re-raise with original message
                raise json.JSONDecodeError(
                    msg=f"JSON PARSING ERROR: {e.msg}",
                    doc=e.doc,
                    pos=e.pos
                ) from e
            
            # Validate required structure
            if not isinstance(memory_data, dict):
                raise ValueError(f"Invalid JSON structure: expected dict, got {type(memory_data)}")
            
            # Ensure required keys exist (merge with defaults, don't replace)
            if 'chat_history' not in memory_data:
                logger.warning("⚠️  Missing 'chat_history' key in JSON. Adding empty list.")
                memory_data['chat_history'] = []
            if 'user_profile' not in memory_data:
                logger.warning("⚠️  Missing 'user_profile' key in JSON. Adding empty dict.")
                memory_data['user_profile'] = {}
            
            # Validate types
            if not isinstance(memory_data.get('chat_history'), list):
                logger.warning("⚠️  'chat_history' is not a list. Converting...")
                memory_data['chat_history'] = []
            if not isinstance(memory_data.get('user_profile'), dict):
                logger.warning("⚠️  'user_profile' is not a dict. Converting...")
                memory_data['user_profile'] = {}
            
            logger.info(f"✅ Successfully downloaded and parsed file {file_id}")
            logger.info(f"   Content length: {content_length} characters")
            logger.info(f"   chat_history entries: {len(memory_data.get('chat_history', []))}")
            
            # Debug logging: Print user profile info
            user_profile = memory_data.get('user_profile', {})
            if user_profile:
                user_name = user_profile.get('name', 'Unknown')
                logger.info(f"✅ Successfully loaded profile for user: {user_name}")
                logger.info(f"   User profile keys: {list(user_profile.keys())}")
            else:
                logger.warning("⚠️  User profile is empty in downloaded file")
            
            return memory_data
            
        except HttpError as e:
            logger.error(f"❌ DRIVE API ERROR downloading file {file_id}: {e}")
            logger.error(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")
            logger.error(f"   Status code: {e.resp.status if hasattr(e, 'resp') else 'N/A'}")
            logger.error(f"   Error message: {e.error_msg if hasattr(e, 'error_msg') else str(e)}")
            # Re-raise with original message
            raise HttpError(
                resp=e.resp,
                content=e.content,
                uri=e.uri
            ) from e
        except json.JSONDecodeError as e:
            # This should already be caught and logged above, but just in case
            logger.error(f"❌ JSON PARSING ERROR in _download_file for file {file_id}: {e}")
            raise  # Re-raise to prevent silent data loss
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading file {file_id}: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise  # Re-raise to prevent silent data loss
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """
        Parse Google Drive RFC 3339 timestamp string to timezone-aware UTC datetime.
        
        Args:
            timestamp_str: RFC 3339 timestamp string from Google Drive API
        
        Returns:
            timezone-aware UTC datetime object, or None if parsing fails
        """
        if not timestamp_str:
            return None
        
        try:
            # Parse RFC 3339 timestamp (e.g., "2025-02-04T10:00:00.000Z")
            dt = date_parser.isoparse(timestamp_str)
            
            # Ensure timezone-aware (Google Drive timestamps are in UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC if not already
                dt = dt.astimezone(timezone.utc)
            
            return dt
        except Exception as e:
            logger.error(f"❌ Error parsing timestamp '{timestamp_str}': {e}")
            return None
    
    def get_memory(self) -> Dict[str, Any]:
        """
        Retrieve memory with robust Smart Cache (Stale-While-Revalidate).
        
        Strategy:
        1. ALWAYS fetch file metadata (ID and modifiedTime) from Drive API first
        2. Compare remote_modified_time vs local_cached_modified_time using datetime objects
        3. If remote > local OR cache is None: Download and update cache
        4. Else: Return cached data (fast path)
        
        Returns:
            Memory dictionary with chat_history and user_profile.
            Returns default structure if file doesn't exist.
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Returning empty memory.")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            return memory_data.copy()
        
        # Step 1: ALWAYS fetch file metadata first
        file_id = self._find_memory_file()
        
        if not file_id:
            # File doesn't exist yet - this is OK for first run
            logger.info(f"📝 Memory file '{MEMORY_FILE_NAME}' not found. File will be created on first save.")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            # Cache the default structure (no file_id, no modifiedTime)
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), None, None)
            return memory_data.copy()
        
        # Initialize variables (in case of exception)
        remote_modified_time = None
        file_mime_type = ''
        is_google_docs_file = False
        
        # Fetch file metadata (ID, modifiedTime, and mimeType) from Drive
        try:
            drive_file = self.service.files().get(
                fileId=file_id,
                fields='id,modifiedTime,mimeType'
            ).execute()
            
            remote_modified_time_str = drive_file.get('modifiedTime')
            remote_modified_time = self._parse_timestamp(remote_modified_time_str)
            file_mime_type = drive_file.get('mimeType', '')
            
            # Check if this is a Google Docs file (needs export, not download)
            is_google_docs_file = file_mime_type.startswith('application/vnd.google-apps.')
            
            if remote_modified_time is None:
                logger.warning(f"⚠️  Could not parse remote modifiedTime: {remote_modified_time_str}")
                logger.warning("   Proceeding with download to be safe...")
        except HttpError as e:
            logger.error(f"❌ DRIVE API ERROR fetching file metadata: {e}")
            logger.error(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")
            logger.error(f"   Status code: {e.resp.status if hasattr(e, 'resp') else 'N/A'}")
            # Fallback: try to use cached data if available (prevent data loss)
            with self._cache_lock:
                cached_data = self._memory_cache
            if cached_data is not None:
                cached_memory, _, cached_file_id = cached_data
                if cached_file_id == file_id:
                    logger.warning("⚠️  Using cached data due to metadata fetch error (preventing data loss)")
                    return cached_memory.copy()
            # No cache available - RAISE exception instead of returning default
            # Better to crash (500 Error) than to wipe the user's brain
            error_msg = (
                f"DRIVE API ERROR: Cannot fetch file metadata (file_id: {file_id}) and no cache available. "
                f"Original error: {str(e)}"
            )
            logger.error(f"❌ CRITICAL: {error_msg}")
            logger.error("   Raising exception to prevent data loss (better to crash than overwrite)")
            raise RuntimeError(error_msg) from e
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching file metadata: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Fallback: try to use cached data if available (prevent data loss)
            with self._cache_lock:
                cached_data = self._memory_cache
            if cached_data is not None:
                cached_memory, _, cached_file_id = cached_data
                if cached_file_id == file_id:
                    logger.warning("⚠️  Using cached data due to metadata fetch error (preventing data loss)")
                    return cached_memory.copy()
            # No cache available - RAISE exception instead of returning default
            error_msg = (
                f"Unexpected error fetching metadata (file_id: {file_id}) and no cache available. "
                f"Original error: {str(e)}"
            )
            logger.error(f"❌ CRITICAL: {error_msg}")
            logger.error("   Raising exception to prevent data loss (better to crash than overwrite)")
            raise RuntimeError(error_msg) from e
        
        # Step 2: Compare timestamps
        with self._cache_lock:
            cached_data = self._memory_cache
        
        local_cached_modified_time = None
        should_reload = False
        
        if cached_data is not None:
            cached_memory, local_cached_modified_time, cached_file_id = cached_data
            
            # Check if file_id matches
            if cached_file_id == file_id:
                # Compare timestamps using datetime objects
                if remote_modified_time is not None and local_cached_modified_time is not None:
                    # Both are datetime objects - compare directly
                    if remote_modified_time > local_cached_modified_time:
                        should_reload = True
                        logger.info(
                            f"🔄 Cache stale detected! "
                            f"Remote: {remote_modified_time.isoformat()} > "
                            f"Local: {local_cached_modified_time.isoformat()}. "
                            f"Reloading from Drive..."
                        )
                    else:
                        # Cache is fresh - return immediately (fast path)
                        logger.debug(
                            f"💨 Cache hit! "
                            f"Remote: {remote_modified_time.isoformat()}, "
                            f"Local: {local_cached_modified_time.isoformat()}. "
                            f"Returning cached data (0ms latency)"
                        )
                        logger.debug(f"   Chat history entries: {len(cached_memory.get('chat_history', []))}")
                        return cached_memory.copy()
                elif remote_modified_time is not None:
                    # Remote has timestamp but local doesn't - reload
                    should_reload = True
                    logger.info(
                        f"🔄 Cache missing timestamp. "
                        f"Remote: {remote_modified_time.isoformat()}. "
                        f"Reloading from Drive..."
                    )
                else:
                    # Remote timestamp parsing failed - reload to be safe
                    should_reload = True
                    logger.warning("⚠️  Remote timestamp parsing failed. Reloading to be safe...")
            else:
                # File ID changed - reload
                should_reload = True
                logger.info(f"🔄 File ID changed (cache: {cached_file_id}, drive: {file_id}). Reloading...")
        else:
            # Cache is None - reload
            should_reload = True
            logger.info("🔄 Cache is empty. Loading from Drive...")
        
        # Step 3: Download and update cache if needed
        if should_reload:
            try:
                # Download and parse file (raises exceptions on error - no silent data loss)
                memory_data = self._download_file(file_id, is_google_docs_file)
                
                # Update cache with data, modifiedTime (as datetime), and file_id
                with self._cache_lock:
                    self._memory_cache = (memory_data.copy(), remote_modified_time, file_id)
                
                logger.info(f"✅ Retrieved memory from Drive and cached (file ID: {file_id})")
                logger.info(f"   Modified time: {remote_modified_time.isoformat() if remote_modified_time else 'None'}")
                logger.info(f"   Chat history entries: {len(memory_data.get('chat_history', []))}")
                logger.info(f"   User profile keys: {list(memory_data.get('user_profile', {}).keys())}")
                
                return memory_data.copy()
            except HttpError as e:
                # CRITICAL: Don't return DEFAULT_MEMORY_STRUCTURE - try to use cache
                logger.error(f"❌ DRIVE API ERROR downloading/parsing memory file: {e}")
                logger.error(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")
                logger.error(f"   Status code: {e.resp.status if hasattr(e, 'resp') else 'N/A'}")
                logger.error("   Attempting to use cached data to prevent data loss...")
                
                # Try to use cached data if available
                with self._cache_lock:
                    cached_data = self._memory_cache
                if cached_data is not None:
                    cached_memory, _, cached_file_id = cached_data
                    if cached_file_id == file_id:
                        logger.warning("⚠️  Using cached data due to Drive API error (preventing data loss)")
                        return cached_memory.copy()
                
                # No cache available - RAISE exception with original message
                error_msg = (
                    f"DRIVE API ERROR: Cannot download memory file (file_id: {file_id}) and no cache available. "
                    f"Original error: {str(e)}"
                )
                logger.error(f"❌ CRITICAL: {error_msg}")
                logger.error("   Better to crash than overwrite existing data with empty structure")
                raise RuntimeError(error_msg) from e
            except json.JSONDecodeError as e:
                # CRITICAL: Don't return DEFAULT_MEMORY_STRUCTURE - try to use cache
                logger.error(f"❌ JSON PARSING ERROR in memory file: {e}")
                logger.error(f"   Error message: {str(e)}")
                logger.error("   Attempting to use cached data to prevent data loss...")
                
                # Try to use cached data if available
                with self._cache_lock:
                    cached_data = self._memory_cache
                if cached_data is not None:
                    cached_memory, _, cached_file_id = cached_data
                    if cached_file_id == file_id:
                        logger.warning("⚠️  Using cached data due to JSON parsing error (preventing data loss)")
                        return cached_memory.copy()
                
                # No cache available - RAISE exception with original message
                error_msg = (
                    f"JSON PARSING ERROR: Cannot parse memory file (file_id: {file_id}) and no cache available. "
                    f"Original error: {str(e)}"
                )
                logger.error(f"❌ CRITICAL: {error_msg}")
                logger.error("   Better to crash than overwrite existing data with empty structure")
                raise RuntimeError(error_msg) from e
            except ValueError as e:
                # CRITICAL: Don't return DEFAULT_MEMORY_STRUCTURE - try to use cache
                logger.error(f"❌ VALUE ERROR in memory file: {e}")
                logger.error(f"   Error message: {str(e)}")
                logger.error("   Attempting to use cached data to prevent data loss...")
                
                # Try to use cached data if available
                with self._cache_lock:
                    cached_data = self._memory_cache
                if cached_data is not None:
                    cached_memory, _, cached_file_id = cached_data
                    if cached_file_id == file_id:
                        logger.warning("⚠️  Using cached data due to value error (preventing data loss)")
                        return cached_memory.copy()
                
                # No cache available - RAISE exception with original message
                error_msg = (
                    f"VALUE ERROR: Invalid memory file structure (file_id: {file_id}) and no cache available. "
                    f"Original error: {str(e)}"
                )
                logger.error(f"❌ CRITICAL: {error_msg}")
                logger.error("   Better to crash than overwrite existing data with empty structure")
                raise RuntimeError(error_msg) from e
            except Exception as e:
                # Unexpected error - try cache first
                logger.error(f"❌ Unexpected error retrieving memory: {e}")
                with self._cache_lock:
                    cached_data = self._memory_cache
                if cached_data is not None:
                    cached_memory, _, cached_file_id = cached_data
                    if cached_file_id == file_id:
                        logger.warning("⚠️  Using cached data due to unexpected error (preventing data loss)")
                        return cached_memory.copy()
                
                # No cache - RAISE exception instead of returning default
                error_msg = (
                    f"Unexpected error retrieving memory (file_id: {file_id}) and no cache available. "
                    "Raising exception to prevent data loss."
                )
                logger.error(f"❌ CRITICAL: {error_msg}")
                raise RuntimeError(error_msg) from e
        
        # Should not reach here - if we do, raise exception
        raise RuntimeError("Unexpected code path in get_memory() - this should not happen")
    
    def update_memory(self, new_interaction: Dict[str, Any], background_tasks=None) -> bool:
        """
        Update memory with a new interaction.
        
        Strategy:
        1. Get current memory (triggers cache refresh check) - MUST contain user_profile
        2. Append new interaction to chat_history
        3. CRITICAL SAFETY CHECK: Ensure user_profile exists before saving
        4. Update in-memory cache immediately (0 latency)
        5. Sync to Drive in background (non-blocking)
        6. CRITICAL: Update cache timestamp after successful upload
        
        Args:
            new_interaction: Dictionary with 'user_message' and 'ai_response' keys.
                           Example: {
                               "user_message": "Hello",
                               "ai_response": "Hi there!",
                               "timestamp": "2025-02-04T10:00:00Z"
                           }
            background_tasks: FastAPI BackgroundTasks object for async Drive sync.
                            If None, syncs to Drive synchronously (backward compatibility).
        
        Returns:
            True if cache update successful (always returns immediately)
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot update memory.")
            return False
        
        try:
            # Step 1: Get current memory (this triggers cache refresh check if Drive is newer)
            # CRITICAL: This MUST contain user_profile
            memory = self.get_memory()
            
            # Step 2: Ensure required structure exists
            if 'chat_history' not in memory:
                memory['chat_history'] = []
            if 'user_profile' not in memory:
                memory['user_profile'] = {}
            
            # Step 3: Append new interaction to chat_history
            memory['chat_history'].append(new_interaction)
            
            # Step 4: STRICT SAFETY LOCK - Prevent overwriting with empty user_profile
            # CRITICAL: Before ANY upload logic, check if user_profile exists
            if "user_profile" not in memory or not memory.get("user_profile"):
                error_msg = (
                    "CRITICAL ERROR: Attempted to save memory without 'user_profile'. "
                    "Aborting to prevent data loss."
                )
                logger.error(f"❌ {error_msg}")
                logger.error(f"   Memory keys: {list(memory.keys())}")
                logger.error(f"   user_profile value: {memory.get('user_profile', 'MISSING')}")
                print(f"❌ {error_msg}")  # Also print to stdout for visibility
                raise ValueError("Safety Lock Engaged: Cannot overwrite Drive file because user_profile is missing.")
            
            # Log successful safety check
            user_name = memory.get('user_profile', {}).get('name', 'Unknown')
            logger.info(f"✅ Safety Lock: user_profile verified (user: {user_name})")
            
            # Step 5: Get file_id for cache update
            file_id = self._find_memory_file()
            
            # STRICT SAFETY LOCK: Final check before ANY upload logic
            # This is the last line of defense - if we reach here without user_profile, abort
            if "user_profile" not in memory or not memory.get("user_profile"):
                error_msg = (
                    "CRITICAL ERROR: Attempted to save memory without 'user_profile'. "
                    "Safety Lock engaged - aborting to prevent data loss."
                )
                logger.error(f"❌ {error_msg}")
                logger.error(f"   Memory keys: {list(memory.keys())}")
                logger.error(f"   user_profile value: {memory.get('user_profile', 'MISSING')}")
                print(f"❌ {error_msg}")  # Also print to stdout for visibility
                raise ValueError("Safety Lock Engaged: Cannot overwrite Drive file because user_profile is missing.")
            
            # Step 6: Update cache immediately (0 latency)
            # Note: modifiedTime will be updated after Drive upload completes
            # CRITICAL: Use deepcopy to prevent shared references between cache and
            # background upload tasks, which can cause circular reference errors.
            with self._cache_lock:
                # Keep existing modifiedTime temporarily (will be updated after upload)
                if self._memory_cache is not None:
                    _, cached_modified_time, cached_file_id = self._memory_cache
                    if cached_file_id == file_id:
                        # Keep the existing modifiedTime temporarily
                        self._memory_cache = (copy.deepcopy(memory), cached_modified_time, file_id)
                    else:
                        # New file or file_id changed
                        self._memory_cache = (copy.deepcopy(memory), None, file_id)
                else:
                    # No cache yet
                    self._memory_cache = (copy.deepcopy(memory), None, file_id)
            
            logger.info(f"💨 Updated memory cache immediately (0ms latency)")
            logger.info(f"   Total chat history entries: {len(memory['chat_history'])}")
            logger.info(f"   User profile keys: {list(memory.get('user_profile', {}).keys())}")
            
            # Step 7: Sync to Drive in background (non-blocking)
            # CRITICAL: Pass a deepcopy to background task to prevent race conditions
            # with future update_memory calls that modify the same objects.
            upload_snapshot = copy.deepcopy(memory)
            if background_tasks:
                # Add background task for Drive sync
                background_tasks.add_task(self._upload_to_drive, upload_snapshot)
                logger.debug("📤 Added Drive sync to background tasks")
            else:
                # Backward compatibility: sync synchronously
                self._upload_to_drive(upload_snapshot)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Unexpected error updating memory cache: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _upload_to_drive(self, memory: Dict[str, Any]) -> bool:
        """
        Internal method to upload memory to Google Drive.
        Called in background task for async sync.
        
        CRITICAL: Updates cache with new modifiedTime after successful upload
        to prevent false reload on next read.
        
        Args:
            memory: Memory dictionary to upload
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured or not self.service:
            return False
        
        # Refresh credentials if needed before API call
        self._refresh_credentials_if_needed()
        
        try:
            # Deep copy to avoid circular references from shared shallow-copy refs
            memory_safe = copy.deepcopy(memory)
            
            # Convert to JSON string (with fallback for non-serializable objects)
            try:
                memory_json = json.dumps(memory_safe, ensure_ascii=False, indent=2)
            except (ValueError, TypeError) as json_err:
                logger.warning(f"⚠️ JSON serialization issue ({json_err}), sanitizing memory...")
                memory_json = json.dumps(memory_safe, ensure_ascii=False, indent=2, default=str)
            memory_bytes = memory_json.encode('utf-8')
            
            # Find existing file or create new one
            file_id = self._find_memory_file()
            
            if file_id:
                # Update existing file
                media = MediaIoBaseUpload(
                    BytesIO(memory_bytes),
                    mimetype='application/json',
                    resumable=False
                )
                
                # Update file and get new modifiedTime
                updated_file = self.service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id,modifiedTime'
                ).execute()
                
                new_modified_time_str = updated_file.get('modifiedTime')
                new_modified_time = self._parse_timestamp(new_modified_time_str)
                
                # CRITICAL: Update cache with new modifiedTime immediately
                # This prevents false reload on next read
                with self._cache_lock:
                    self._memory_cache = (memory.copy(), new_modified_time, file_id)
                
                logger.info(f"✅ Synced memory to Drive (file ID: {file_id})")
                logger.info(
                    f"   Updated cache with new modifiedTime: "
                    f"{new_modified_time.isoformat() if new_modified_time else 'None'}"
                )
            else:
                # Create new file
                file_metadata = {
                    'name': MEMORY_FILE_NAME,
                    'parents': [self.folder_id]
                }
                
                media = MediaIoBaseUpload(
                    BytesIO(memory_bytes),
                    mimetype='application/json',
                    resumable=False
                )
                
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,modifiedTime'
                ).execute()
                
                new_file_id = file['id']
                new_modified_time_str = file.get('modifiedTime')
                new_modified_time = self._parse_timestamp(new_modified_time_str)
                
                # CRITICAL: Update cache with new file_id and modifiedTime
                with self._cache_lock:
                    self._memory_cache = (memory.copy(), new_modified_time, new_file_id)
                
                logger.info(f"✅ Created new memory file in Drive (file ID: {new_file_id})")
                logger.info(
                    f"   Updated cache with modifiedTime: "
                    f"{new_modified_time.isoformat() if new_modified_time else 'None'}"
                )
            
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error syncing memory to Drive (background): {e}")
            # Accept minor data loss for speed - just log the error
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error syncing memory to Drive (background): {e}")
            # Accept minor data loss for speed - just log the error
            import traceback
            traceback.print_exc()
            return False
    
    def clear_memory(self) -> bool:
        """
        Clear all memory (reset to default structure).
        Clears both cache and Drive.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot clear memory.")
            return False
        
        try:
            # Clear cache
            with self._cache_lock:
                self._memory_cache = (DEFAULT_MEMORY_STRUCTURE.copy(), None, None)
            
            file_id = self._find_memory_file()
            if file_id:
                # Update with default structure
                memory_json = json.dumps(DEFAULT_MEMORY_STRUCTURE, ensure_ascii=False, indent=2)
                memory_bytes = memory_json.encode('utf-8')
                
                media = MediaIoBaseUpload(
                    BytesIO(memory_bytes),
                    mimetype='application/json',
                    resumable=False
                )
                
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                
                logger.info(f"✅ Cleared memory file in Drive and cache")
                return True
            else:
                logger.info("📝 No memory file to clear")
                return True
        except Exception as e:
            logger.error(f"❌ Error clearing memory: {e}")
            return False
    
    def preload_memory(self) -> bool:
        """
        Pre-load memory from Drive into cache (for startup).
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔥 Pre-warming memory cache...")
        try:
            self.get_memory()  # This will populate the cache
            logger.info("✅ Memory cache pre-warmed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error pre-warming memory cache: {e}")
            return False
