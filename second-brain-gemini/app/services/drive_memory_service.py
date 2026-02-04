"""
Google Drive Memory Service
Manages persistent conversation memory stored in Google Drive.
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

logger = logging.getLogger(__name__)

MEMORY_FILE_NAME = "second_brain_memory.json"
DEFAULT_MEMORY_STRUCTURE = {
    "chat_history": [],
    "user_profile": {}
}


class DriveMemoryService:
    """Service for managing persistent memory in Google Drive."""
    
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
        Retrieve memory from Google Drive.
        
        Returns:
            Memory dictionary with chat_history and user_profile.
            Returns default structure if file doesn't exist.
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Returning empty memory.")
            return DEFAULT_MEMORY_STRUCTURE.copy()
        
        file_id = self._find_memory_file()
        
        if not file_id:
            logger.info(f"📝 Memory file '{MEMORY_FILE_NAME}' not found. Returning empty memory.")
            return DEFAULT_MEMORY_STRUCTURE.copy()
        
        try:
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
            
            logger.info(f"✅ Retrieved memory from Drive (file ID: {file_id})")
            logger.info(f"   Chat history entries: {len(memory_data.get('chat_history', []))}")
            
            return memory_data
        except HttpError as e:
            logger.error(f"❌ Error downloading memory file: {e}")
            return DEFAULT_MEMORY_STRUCTURE.copy()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing memory file JSON: {e}")
            return DEFAULT_MEMORY_STRUCTURE.copy()
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving memory: {e}")
            return DEFAULT_MEMORY_STRUCTURE.copy()
    
    def update_memory(self, new_interaction: Dict[str, Any]) -> bool:
        """
        Update memory with a new interaction.
        
        Args:
            new_interaction: Dictionary with 'user_message' and 'ai_response' keys.
                           Example: {
                               "user_message": "Hello",
                               "ai_response": "Hi there!",
                               "timestamp": "2025-02-04T10:00:00Z"
                           }
        
        Returns:
            True if update successful, False otherwise
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot update memory.")
            return False
        
        try:
            # Get current memory
            memory = self.get_memory()
            
            # Append new interaction to chat_history
            if 'chat_history' not in memory:
                memory['chat_history'] = []
            
            memory['chat_history'].append(new_interaction)
            
            # Convert to JSON string
            memory_json = json.dumps(memory, ensure_ascii=False, indent=2)
            memory_bytes = memory_json.encode('utf-8')
            
            # Find existing file or create new one
            file_id = self._find_memory_file()
            
            if file_id:
                # Update existing file
                # Use MediaIoBaseUpload for in-memory content
                from googleapiclient.http import MediaIoBaseUpload
                media = MediaIoBaseUpload(
                    BytesIO(memory_bytes),
                    mimetype='application/json',
                    resumable=False
                )
                
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                
                logger.info(f"✅ Updated memory file in Drive (file ID: {file_id})")
            else:
                # Create new file
                file_metadata = {
                    'name': MEMORY_FILE_NAME,
                    'parents': [self.folder_id]
                }
                
                from googleapiclient.http import MediaIoBaseUpload
                media = MediaIoBaseUpload(
                    BytesIO(memory_bytes),
                    mimetype='application/json',
                    resumable=False
                )
                
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                logger.info(f"✅ Created new memory file in Drive (file ID: {file['id']})")
            
            logger.info(f"   Total chat history entries: {len(memory['chat_history'])}")
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error updating memory file: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error updating memory: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear_memory(self) -> bool:
        """
        Clear all memory (reset to default structure).
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured or not self.service:
            logger.warning("⚠️  Drive Memory Service not configured. Cannot clear memory.")
            return False
        
        try:
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
                
                logger.info(f"✅ Cleared memory file in Drive")
                return True
            else:
                logger.info("📝 No memory file to clear")
                return True
        except Exception as e:
            logger.error(f"❌ Error clearing memory: {e}")
            return False
