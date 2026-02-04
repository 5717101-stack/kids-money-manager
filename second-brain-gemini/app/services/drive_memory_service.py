"""
Google Drive Memory Service
Manages persistent conversation memory stored in Google Drive.
Uses in-memory caching with robust timestamp-based stale-while-revalidate logic.
"""

import os
import json
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
from google.oauth2 import service_account
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
        Initialize Drive Memory Service.
        
        Args:
            folder_id: Google Drive folder ID where memory file is stored.
                      If None, uses DRIVE_MEMORY_FOLDER_ID from environment.
        """
        self.folder_id = folder_id or os.environ.get("DRIVE_MEMORY_FOLDER_ID")
        
        if not self.folder_id:
            logger.warning("⚠️  DRIVE_MEMORY_FOLDER_ID not set. Memory service will not work.")
            self.service = None
            self.is_configured = False
            return
        
        # Initialize Google Drive service (reuse auth logic from process_meetings.py)
        service_account_info = {
            "type": "service_account",
            "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
            "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": os.environ.get("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ.get("GOOGLE_CLIENT_X509_CERT_URL", "")
        }
        
        if not all([
            service_account_info["private_key"],
            service_account_info["client_email"],
            service_account_info["project_id"]
        ]):
            logger.warning(
                "⚠️  Missing Google Drive credentials. Required: "
                "GOOGLE_PRIVATE_KEY, GOOGLE_CLIENT_EMAIL, GOOGLE_PROJECT_ID"
            )
            self.service = None
            self.is_configured = False
            return
        
        try:
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            self.is_configured = True
            logger.info("✅ Drive Memory Service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Drive Memory Service: {e}")
            self.service = None
            self.is_configured = False
    
    def _find_memory_file(self) -> Optional[str]:
        """
        Find the memory file in the configured Drive folder.
        
        Returns:
            File ID if found, None otherwise
        """
        if not self.is_configured or not self.service:
            return None
        
        try:
            query = f"'{self.folder_id}' in parents and name='{MEMORY_FILE_NAME}' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
        except HttpError as e:
            logger.error(f"❌ Error finding memory file: {e}")
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
                logger.error(f"❌ JSON parsing failed for file {file_id}: {e}")
                logger.error(f"   Content length: {content_length} characters")
                logger.error(f"   Content preview (first 500 chars): {content_str[:500]}")
                raise  # Re-raise to prevent silent data loss
            
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
            logger.error(f"❌ HttpError downloading file {file_id}: {e}")
            raise  # Re-raise to prevent silent data loss
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSONDecodeError parsing file {file_id}: {e}")
            raise  # Re-raise to prevent silent data loss
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading file {file_id}: {e}")
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
            logger.error(f"❌ Error fetching file metadata from Drive: {e}")
            # Fallback: try to use cached data if available
            with self._cache_lock:
                cached_data = self._memory_cache
            if cached_data is not None:
                cached_memory, _, cached_file_id = cached_data
                if cached_file_id == file_id:
                    logger.warning("⚠️  Using cached data due to metadata fetch error")
                    return cached_memory.copy()
            # No cache available, return default
            return DEFAULT_MEMORY_STRUCTURE.copy()
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching file metadata: {e}")
            # Fallback: try to use cached data if available
            with self._cache_lock:
                cached_data = self._memory_cache
            if cached_data is not None:
                cached_memory, _, cached_file_id = cached_data
                if cached_file_id == file_id:
                    logger.warning("⚠️  Using cached data due to metadata fetch error")
                    return cached_memory.copy()
            # No cache available, return default
            return DEFAULT_MEMORY_STRUCTURE.copy()
        
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
            except (HttpError, json.JSONDecodeError, ValueError) as e:
                # CRITICAL: Don't return DEFAULT_MEMORY_STRUCTURE - try to use cache
                logger.error(f"❌ Error downloading/parsing memory file: {e}")
                logger.error("   Attempting to use cached data to prevent data loss...")
                
                # Try to use cached data if available
                with self._cache_lock:
                    cached_data = self._memory_cache
                if cached_data is not None:
                    cached_memory, _, cached_file_id = cached_data
                    if cached_file_id == file_id:
                        logger.warning("⚠️  Using cached data due to download/parse error (preventing data loss)")
                        return cached_memory.copy()
                
                # No cache available - RAISE exception instead of returning default
                # Better to crash (500 Error) than to wipe the user's brain
                error_msg = (
                    f"Cannot download/parse memory file (file_id: {file_id}) and no cache available. "
                    "Raising exception to prevent data loss."
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
            
            # Step 6: Update cache immediately (0 latency)
            # Note: modifiedTime will be updated after Drive upload completes
            with self._cache_lock:
                # Keep existing modifiedTime temporarily (will be updated after upload)
                if self._memory_cache is not None:
                    _, cached_modified_time, cached_file_id = self._memory_cache
                    if cached_file_id == file_id:
                        # Keep the existing modifiedTime temporarily
                        self._memory_cache = (memory.copy(), cached_modified_time, file_id)
                    else:
                        # New file or file_id changed
                        self._memory_cache = (memory.copy(), None, file_id)
                else:
                    # No cache yet
                    self._memory_cache = (memory.copy(), None, file_id)
            
            logger.info(f"💨 Updated memory cache immediately (0ms latency)")
            logger.info(f"   Total chat history entries: {len(memory['chat_history'])}")
            logger.info(f"   User profile keys: {list(memory.get('user_profile', {}).keys())}")
            
            # Step 7: Sync to Drive in background (non-blocking)
            if background_tasks:
                # Add background task for Drive sync
                background_tasks.add_task(self._upload_to_drive, memory)
                logger.debug("📤 Added Drive sync to background tasks")
            else:
                # Backward compatibility: sync synchronously
                self._upload_to_drive(memory)
            
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
        
        try:
            # Convert to JSON string
            memory_json = json.dumps(memory, ensure_ascii=False, indent=2)
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
