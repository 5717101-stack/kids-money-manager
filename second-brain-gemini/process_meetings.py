#!/usr/bin/env python3
"""
Inbox Poller — Process new audio files from Google Drive inbox.

This module is called by the APScheduler cron inside main.py every 5 minutes.
When a new audio file appears in the DRIVE_INBOX_ID folder, it goes through
the EXACT same pipeline as a WhatsApp audio message (via audio_pipeline.py):

  1. Download from Drive → temp file
  2. Delegate to process_audio_core() (the SINGLE SOURCE OF TRUTH)
  3. Move processed file to archive

Usage (called from main.py scheduler):
    from process_meetings import check_inbox_and_process
    check_inbox_and_process()
"""

import os
import io
import sys
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Audio MIME types we support
AUDIO_MIME_TYPES = {
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
    'audio/x-wav', 'audio/m4a', 'audio/x-m4a', 'audio/aac',
    'audio/ogg', 'audio/flac', 'audio/mp4', 'audio/x-m4a',
    'video/mp4',  # Some recordings save as video/mp4
}


def check_inbox_and_process():
    """
    Main entry point — called by APScheduler every 5 minutes.
    
    Checks DRIVE_INBOX_ID for new audio files and processes each one
    through the unified audio pipeline (same as WhatsApp >30s flow).
    """
    inbox_folder_id = os.environ.get("DRIVE_INBOX_ID", "")
    archive_folder_id = os.environ.get("DRIVE_ARCHIVE_ID", "")
    
    if not inbox_folder_id:
        return  # Not configured — skip silently
    
    try:
        from app.services.drive_memory_service import DriveMemoryService
        
        drive_service = DriveMemoryService()
        if not drive_service.is_configured or not drive_service.service:
            logger.warning("⚠️  [InboxPoller] Drive service not configured — skipping")
            return
        
        drive_service._refresh_credentials_if_needed()
        
        # List files in inbox folder
        query = f"'{inbox_folder_id}' in parents and trashed = false"
        results = drive_service.service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, createdTime)",
            orderBy="createdTime asc"  # Process oldest first
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return  # Empty inbox — normal
        
        # Filter to audio files only
        audio_files = [f for f in files if f.get('mimeType', '') in AUDIO_MIME_TYPES]
        
        if not audio_files:
            logger.info(f"📭 [InboxPoller] Found {len(files)} file(s) in inbox, but none are audio")
            return
        
        logger.info(f"📥 [InboxPoller] Found {len(audio_files)} audio file(s) to process")
        
        for file_meta in audio_files:
            try:
                _process_inbox_file(
                    drive_service=drive_service,
                    file_meta=file_meta,
                    inbox_folder_id=inbox_folder_id,
                    archive_folder_id=archive_folder_id,
                )
            except Exception as file_err:
                logger.error(f"❌ [InboxPoller] Error processing {file_meta.get('name')}: {file_err}")
                import traceback
                traceback.print_exc()
                continue
    
    except Exception as e:
        logger.error(f"❌ [InboxPoller] Fatal error: {e}")
        import traceback
        traceback.print_exc()


def _process_inbox_file(
    drive_service,
    file_meta: Dict[str, Any],
    inbox_folder_id: str,
    archive_folder_id: str,
):
    """
    Process a single audio file from the inbox.
    
    This is a THIN WRAPPER that:
      1. Downloads audio from Google Drive
      2. Delegates ALL processing to process_audio_core()
      3. Moves the file to archive after processing
    """
    file_id = file_meta['id']
    file_name = file_meta.get('name', 'unknown')
    mime_type = file_meta.get('mimeType', 'audio/mpeg')
    
    print(f"\n{'='*60}")
    print(f"📥 [InboxPoller] Processing: {file_name}")
    print(f"   File ID: {file_id}")
    print(f"   MIME: {mime_type}")
    print(f"{'='*60}\n")
    
    tmp_path = None
    
    try:
        # ── Step 1: Download audio from Drive ──
        from googleapiclient.http import MediaIoBaseDownload
        
        request = drive_service.service.files().get_media(fileId=file_id)
        audio_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(audio_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        print(f"✅ Downloaded: {len(audio_bytes)} bytes")
        
        # ── Step 2: Save to temp file ──
        file_ext = Path(file_name).suffix or '.ogg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # ── Step 3: Extract recording date & build metadata ──
        from app.services.audio_date_extractor import extract_recording_date
        recording_date = extract_recording_date(tmp_path)
        
        audio_metadata = {
            "file_id": file_id,
            "filename": file_name,
        }
        
        if recording_date:
            audio_metadata["recording_date"] = recording_date.isoformat() + "Z"
            print(f"📅 Recording date extracted: {recording_date.isoformat()}Z")
        else:
            print(f"📅 No recording date found — will use processing time")
        
        # ── Step 4: Delegate to unified audio pipeline ──
        from app.services.audio_pipeline import process_audio_core
        from app.services.whatsapp_provider import WhatsAppProviderFactory
        
        wp = WhatsAppProviderFactory.create_provider(fallback=False)
        phone = os.environ.get("MY_PHONE_NUMBER", "")
        if phone:
            phone = phone.lstrip("+")
        
        process_audio_core(
            tmp_path=tmp_path,
            from_number=phone,
            audio_metadata=audio_metadata,
            whatsapp_provider=wp,
            drive_memory_service=drive_service,
            source="drive_inbox",
        )
        
        # ── Step 5: Move to archive ──
        if archive_folder_id:
            try:
                file_info = drive_service.service.files().get(
                    fileId=file_id, fields='parents'
                ).execute()
                previous_parents = ",".join(file_info.get('parents', []))
                
                drive_service.service.files().update(
                    fileId=file_id,
                    addParents=archive_folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
                
                print(f"📦 Moved to archive folder")
            except Exception as move_err:
                print(f"⚠️  Failed to move to archive: {move_err}")
        else:
            print("ℹ️  No DRIVE_ARCHIVE_ID configured — file stays in inbox")
        
        print(f"\n✅ [InboxPoller] Successfully processed: {file_name}")
        print(f"{'='*60}\n")
        
    finally:
        # Clean up temp file
        if tmp_path:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass


# Legacy entry point — kept for backward compatibility with external cron jobs
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    print("🚀 Starting inbox processing (standalone mode)...")
    check_inbox_and_process()
    print("✅ Done.")
