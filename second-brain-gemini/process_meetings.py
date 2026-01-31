#!/usr/bin/env python3
"""
Background process to process meeting recordings from Google Drive.

This script:
1. Checks Google Drive folder for new audio files
2. Downloads and processes them with Gemini 1.5 Pro
3. Sends summary via Twilio SMS
4. Moves processed files to Archive folder
"""

import os
import sys
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

# Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# Google Gemini AI
import google.generativeai as genai

# Twilio
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('process_meetings.log')
    ]
)
logger = logging.getLogger(__name__)

# System Instruction for Gemini
SYSTEM_INSTRUCTION = """You are an expert AI assistant. Listen to the attached audio meeting and generate a Hebrew summary.

Step 1: CLASSIFY CONTEXT

If conversation involves children/family -> Context: FAMILY (Persona: Adler Institute Counselor - focus on encouragement, cooperation).

If conversation involves work/tech/management -> Context: WORK (Persona: Simon Sinek Leadership Coach - focus on The Why, safety, infinite game).

Step 2: OUTPUT FORMAT (Hebrew Only):
📌 נושא הפגישה: [3-5 words summary]
🗣️ משתתפים: [Names or count]
[MOOD_ICON] סנטימנט: [חיובי/נייטרלי/שלילי]
💾 לשימור: [One strong point based on persona]
🚀 לשיפור: [One constructive point based on persona]
✅ אקשן אייטמס:
[Item 1]
[Item 2]
(Or "אין משימות להמשך")
"""


class GoogleDriveService:
    """Service for interacting with Google Drive."""
    
    def __init__(self):
        """Initialize Google Drive service with service account credentials."""
        # Get credentials from environment variables
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
            raise ValueError(
                "Missing Google Drive credentials. Required: "
                "GOOGLE_PRIVATE_KEY, GOOGLE_CLIENT_EMAIL, GOOGLE_PROJECT_ID"
            )
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        self.service = build('drive', 'v3', credentials=credentials)
        logger.info("✅ Google Drive service initialized")
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📁 Found {len(files)} files in folder {folder_id}")
            return files
            
        except HttpError as e:
            logger.error(f"❌ Error listing files in folder: {e}")
            raise
    
    def download_file(self, file_id: str, file_name: str, output_path: Path) -> Path:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            output_path: Path to save the file
            
        Returns:
            Path to downloaded file
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"⏬ Download progress: {int(status.progress() * 100)}%")
            
            logger.info(f"✅ Downloaded: {file_name} -> {output_path}")
            return output_path
            
        except HttpError as e:
            logger.error(f"❌ Error downloading file {file_id}: {e}")
            raise
    
    def move_file_to_folder(self, file_id: str, source_folder_id: str, target_folder_id: str) -> bool:
        """
        Move a file from one folder to another.
        
        Args:
            file_id: Google Drive file ID
            source_folder_id: Source folder ID (to remove from)
            target_folder_id: Target folder ID (to add to)
            
        Returns:
            True if successful
        """
        try:
            # Get current parents
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move file: remove from source, add to target
            self.service.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            logger.info(f"✅ Moved file {file_id} to archive folder")
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error moving file {file_id}: {e}")
            return False


class GeminiService:
    """Service for processing audio with Gemini 1.5 Pro."""
    
    def __init__(self):
        """Initialize Gemini service."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        logger.info("✅ Gemini service initialized")
    
    def process_audio(self, audio_path: Path) -> str:
        """
        Process audio file with Gemini and generate summary.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Generated summary text
        """
        try:
            logger.info(f"📤 Uploading audio file: {audio_path.name}")
            
            # Determine MIME type from file extension
            mime_type_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.wave': 'audio/wav',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
                '.mp4': 'audio/mp4',  # Some MP4 files are audio-only
            }
            
            file_ext = audio_path.suffix.lower()
            mime_type = mime_type_map.get(file_ext, 'audio/mpeg')  # Default to MP3
            
            logger.info(f"📋 Detected MIME type: {mime_type} for extension: {file_ext}")
            
            # Upload file to Gemini with explicit MIME type
            file_ref = genai.upload_file(
                path=str(audio_path),
                display_name=audio_path.name,
                mime_type=mime_type
            )
            
            # Wait for file to be processed
            logger.info("⏳ Waiting for file processing...")
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                file_ref = genai.get_file(file_ref.name)
                state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                
                if state == "ACTIVE":
                    logger.info("✅ File processing complete")
                    break
                elif state == "FAILED":
                    raise ValueError(f"File processing failed: {file_ref.name}")
                
                time.sleep(2)
            else:
                raise TimeoutError("File processing timeout")
            
            # Generate content
            logger.info("🤖 Generating summary with Gemini...")
            contents = [
                SYSTEM_INSTRUCTION,
                file_ref
            ]
            
            response = self.model.generate_content(
                contents,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                },
                request_options={'timeout': 600}  # 10 minutes
            )
            
            summary = response.text
            logger.info(f"✅ Generated summary ({len(summary)} characters)")
            
            # Clean up uploaded file
            try:
                genai.delete_file(file_ref.name)
                logger.info("🗑️  Deleted uploaded file from Gemini")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete file from Gemini: {e}")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
            raise


class TwilioService:
    """Service for sending SMS via Twilio."""
    
    def __init__(self):
        """Initialize Twilio service."""
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
        
        self.client = TwilioClient(account_sid, auth_token)
        logger.info("✅ Twilio service initialized")
    
    def send_sms(self, message: str, to: str) -> bool:
        """
        Send SMS message.
        
        Args:
            message: Message text
            to: Recipient phone number (format: +972XXXXXXXXX)
            
        Returns:
            True if successful
        """
        try:
            from_number = os.environ.get("TWILIO_SMS_FROM")
            if not from_number:
                raise ValueError("TWILIO_SMS_FROM not set")
            
            # Limit message length to 1500 characters
            if len(message) > 1500:
                message = message[:1500] + "... (הודעה קוצרה)"
            
            logger.info(f"📱 Sending SMS to {to}...")
            
            sms = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to
            )
            
            logger.info(f"✅ SMS sent successfully (SID: {sms.sid})")
            return True
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending SMS: {e}")
            return False


def process_meeting_file(
    drive_service: GoogleDriveService,
    gemini_service: GeminiService,
    twilio_service: TwilioService,
    file_metadata: Dict[str, Any],
    inbox_folder_id: str,
    archive_folder_id: str,
    phone_number: str
) -> bool:
    """
    Process a single meeting file.
    
    Args:
        drive_service: Google Drive service instance
        gemini_service: Gemini service instance
        twilio_service: Twilio service instance
        file_metadata: File metadata from Google Drive
        inbox_folder_id: Source folder ID
        archive_folder_id: Archive folder ID
        phone_number: Phone number to send SMS to
        
    Returns:
        True if processing was successful
    """
    file_id = file_metadata['id']
    file_name = file_metadata['name']
    mime_type = file_metadata.get('mimeType', '')
    
    # Check if file is audio
    audio_mime_types = [
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
        'audio/x-wav', 'audio/m4a', 'audio/x-m4a', 'audio/aac'
    ]
    
    if mime_type not in audio_mime_types:
        logger.warning(f"⚠️  Skipping non-audio file: {file_name} (type: {mime_type})")
        return False
    
    temp_file = None
    
    try:
        # Create temporary file
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"meeting_{file_id}_{int(time.time())}"
        
        # Download file
        logger.info(f"📥 Processing: {file_name}")
        drive_service.download_file(file_id, file_name, temp_file)
        
        # Process with Gemini
        summary = gemini_service.process_audio(temp_file)
        
        # Send SMS
        sms_sent = twilio_service.send_sms(summary, phone_number)
        if not sms_sent:
            logger.warning(f"⚠️  SMS not sent, but continuing...")
        
        # Move to archive
        moved = drive_service.move_file_to_folder(
            file_id,
            inbox_folder_id,
            archive_folder_id
        )
        
        if moved:
            logger.info(f"✅ Successfully processed: {file_name}")
            return True
        else:
            logger.error(f"❌ Failed to move file to archive: {file_name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing file {file_name}: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up temporary file
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                logger.info(f"🗑️  Deleted temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete temp file: {e}")


def main():
    """Main function to process meeting recordings."""
    logger.info("🚀 Starting meeting processing job...")
    
    # Get environment variables
    inbox_folder_id = os.environ.get("DRIVE_INBOX_ID")
    archive_folder_id = os.environ.get("DRIVE_ARCHIVE_ID")
    phone_number = os.environ.get("MY_PHONE_NUMBER")
    
    if not all([inbox_folder_id, archive_folder_id, phone_number]):
        logger.error(
            "❌ Missing required environment variables: "
            "DRIVE_INBOX_ID, DRIVE_ARCHIVE_ID, MY_PHONE_NUMBER"
        )
        sys.exit(1)
    
    try:
        # Initialize services
        drive_service = GoogleDriveService()
        gemini_service = GeminiService()
        twilio_service = TwilioService()
        
        # List files in inbox
        files = drive_service.list_files_in_folder(inbox_folder_id)
        
        if not files:
            logger.info("📭 No files to process")
            return
        
        # Process each file
        success_count = 0
        error_count = 0
        
        for file_metadata in files:
            try:
                success = process_meeting_file(
                    drive_service,
                    gemini_service,
                    twilio_service,
                    file_metadata,
                    inbox_folder_id,
                    archive_folder_id,
                    phone_number
                )
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to process file {file_metadata.get('name', 'unknown')}: {e}")
                error_count += 1
                continue
        
        logger.info(f"✅ Processing complete: {success_count} succeeded, {error_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
