"""
Google Drive Memory Service
Manages persistent conversation memory stored in Google Drive.
Uses in-memory caching for fast response times with background Drive sync.
"""

import os
import json
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from io import BytesIO
import logging
from threading import Lock

logger = logging.getLogger(__name__)

MEMORY_FILE_NAME = "second_brain_memory.json"
DEFAULT_MEMORY_STRUCTURE = {
    "chat_history": [],
    "user_profile": {}
}


class DriveMemoryService:
    """Service for managing persistent memory in Google Drive with in-memory caching."""
    
    # Class-level in-memory cache
    # Structure: (memory_data: Dict, modified_time: str, file_id: str)
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
    
    def get_memory(self) -> Dict[str, Any]:
        """
        Retrieve memory with Smart Cache (Stale-While-Revalidate).
        
        Strategy:
        1. If cache exists, do lightweight check of Drive modifiedTime
        2. If Drive is newer, download and update cache
        3. If timestamps match, return cached data (fast path)
        
        Returns:
            Memory dictionary with chat_history and user_profile.
            Returns default structure if file doesn't exist.
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Returning empty memory.")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            return memory_data.copy()
        
        file_id = self._find_memory_file()
        
        if not file_id:
            logger.info(f"📝 Memory file '{MEMORY_FILE_NAME}' not found. Returning empty memory.")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            # Cache the default structure (no file_id, no modifiedTime)
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), None, None)
            return memory_data.copy()
        
        # Check cache and compare with Drive modifiedTime
        with self._cache_lock:
            cached_data = self._memory_cache
        
        if cached_data is not None:
            cached_memory, cached_modified_time, cached_file_id = cached_data
            
            # If file_id matches, check if Drive file is newer
            if cached_file_id == file_id:
                try:
                    # Lightweight check: get only modifiedTime from Drive
                    drive_file = self.service.files().get(
                        fileId=file_id,
                        fields='modifiedTime'
                    ).execute()
                    
                    drive_modified_time = drive_file.get('modifiedTime')
                    
                    # If timestamps match, return cached data (fast path)
                    if drive_modified_time == cached_modified_time:
                        logger.debug(f"💨 Retrieved memory from cache (0ms latency, timestamps match)")
                        logger.debug(f"   Chat history entries: {len(cached_memory.get('chat_history', []))}")
                        return cached_memory.copy()
                    
                    # Drive is newer - need to reload
                    logger.info(f"🔄 Drive file is newer (cache: {cached_modified_time}, drive: {drive_modified_time})")
                    logger.info(f"   Reloading from Drive to sync with manual edits...")
                except HttpError as e:
                    logger.warning(f"⚠️  Error checking Drive modifiedTime: {e}. Using cached data.")
                    return cached_memory.copy()
                except Exception as e:
                    logger.warning(f"⚠️  Unexpected error checking Drive modifiedTime: {e}. Using cached data.")
                    return cached_memory.copy()
        
        # Cache miss or Drive is newer - fetch from Drive
        try:
            # Get file metadata (including modifiedTime)
            drive_file = self.service.files().get(
                fileId=file_id,
                fields='modifiedTime'
            ).execute()
            drive_modified_time = drive_file.get('modifiedTime')
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            file_content = BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Parse JSON
            file_content.seek(0)
            content_str = file_content.read().decode('utf-8')
            memory_data = json.loads(content_str)
            
            # Populate cache with data, modifiedTime, and file_id
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), drive_modified_time, file_id)
            
            logger.info(f"✅ Retrieved memory from Drive and cached (file ID: {file_id})")
            logger.info(f"   Modified time: {drive_modified_time}")
            logger.info(f"   Chat history entries: {len(memory_data.get('chat_history', []))}")
            
            return memory_data.copy()
        except HttpError as e:
            logger.error(f"❌ Error downloading memory file: {e}")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), None, None)
            return memory_data.copy()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing memory file JSON: {e}")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), None, None)
            return memory_data.copy()
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving memory: {e}")
            memory_data = DEFAULT_MEMORY_STRUCTURE.copy()
            with self._cache_lock:
                self._memory_cache = (memory_data.copy(), None, None)
            return memory_data.copy()
    
    def update_memory(self, new_interaction: Dict[str, Any], background_tasks=None) -> bool:
        """
        Update memory with a new interaction.
        
        Strategy:
        1. Update in-memory cache immediately (0 latency)
        2. Sync to Drive in background (non-blocking)
        
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
            # Get current memory (from cache if available)
            memory = self.get_memory()
            
            # Append new interaction to chat_history
            if 'chat_history' not in memory:
                memory['chat_history'] = []
            
            memory['chat_history'].append(new_interaction)
            
            # Update cache immediately (0 latency)
            # Note: modifiedTime will be updated after Drive upload completes
            file_id = self._find_memory_file()
            with self._cache_lock:
                # Keep existing modifiedTime if available, will be updated after upload
                if self._memory_cache is not None:
                    _, cached_modified_time, cached_file_id = self._memory_cache
                    if cached_file_id == file_id:
                        # Keep the existing modifiedTime temporarily (will be updated after upload)
                        self._memory_cache = (memory.copy(), cached_modified_time, file_id)
                    else:
                        # New file or file_id changed
                        self._memory_cache = (memory.copy(), None, file_id)
                else:
                    # No cache yet
                    self._memory_cache = (memory.copy(), None, file_id)
            
            logger.info(f"💨 Updated memory cache immediately (0ms latency)")
            logger.info(f"   Total chat history entries: {len(memory['chat_history'])}")
            
            # Sync to Drive in background (non-blocking)
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
        Updates cache with new modifiedTime after successful upload.
        
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
                    fields='modifiedTime'
                ).execute()
                
                new_modified_time = updated_file.get('modifiedTime')
                
                # Update cache with new modifiedTime
                with self._cache_lock:
                    self._memory_cache = (memory.copy(), new_modified_time, file_id)
                
                logger.info(f"✅ Synced memory to Drive (file ID: {file_id})")
                logger.debug(f"   Updated cache with new modifiedTime: {new_modified_time}")
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
                new_modified_time = file.get('modifiedTime')
                
                # Update cache with new file_id and modifiedTime
                with self._cache_lock:
                    self._memory_cache = (memory.copy(), new_modified_time, new_file_id)
                
                logger.info(f"✅ Created new memory file in Drive (file ID: {new_file_id})")
                logger.debug(f"   Updated cache with modifiedTime: {new_modified_time}")
            
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