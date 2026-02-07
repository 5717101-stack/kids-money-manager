#!/usr/bin/env python3
"""
Inbox Poller — Process new audio files from Google Drive inbox.

This module is called by the APScheduler cron inside main.py every 5 minutes.
When a new audio file appears in the DRIVE_INBOX_ID folder, it goes through
the EXACT same pipeline as a WhatsApp audio message >30s:

  1. Download from Drive
  2. Combined Diarization + Expert Analysis (Gemini — single call)
  3. Speaker Identification (VAD + WhatsApp clips)
  4. Save transcript to Transcripts/ folder
  5. Save summary to memory.json
  6. Inject working memory into Conversation Engine
  7. Send summary via WhatsApp (Meta)
  8. Move file to archive

Usage (called from main.py scheduler):
    from process_meetings import check_inbox_and_process
    check_inbox_and_process()
"""

import os
import io
import sys
import json
import time
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

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
    through the full audio pipeline (same as WhatsApp >30s flow).
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
    Process a single audio file from the inbox through the full pipeline.
    
    This replicates the process_audio_in_background() flow from main.py
    but reads from Drive instead of WhatsApp media API.
    """
    file_id = file_meta['id']
    file_name = file_meta.get('name', 'unknown')
    mime_type = file_meta.get('mimeType', 'audio/mpeg')
    
    print(f"\n{'='*60}")
    print(f"📥 [InboxPoller] Processing: {file_name}")
    print(f"   File ID: {file_id}")
    print(f"   MIME: {mime_type}")
    print(f"{'='*60}\n")
    
    temp_files = []
    
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
            temp_files.append(tmp_path)
        
        # ── Step 3: Retrieve voice signatures for speaker ID ──
        from app.services.gemini_service import gemini_service as gs
        from app.core.config import settings
        
        reference_voices = []
        if drive_service.is_configured and settings.enable_multimodal_voice:
            try:
                max_sigs = settings.max_voice_signatures
                print(f"🎤 Retrieving voice signatures (max: {max_sigs})...")
                reference_voices = drive_service.get_voice_signatures(max_signatures=max_sigs)
                if reference_voices:
                    print(f"✅ Retrieved {len(reference_voices)} voice signature(s)")
            except Exception as e:
                print(f"⚠️  Error retrieving voice signatures: {e}")
        
        # ── Step 4: Combined Diarization + Expert Analysis (single Gemini call) ──
        # This is the same call as process_audio_in_background in main.py
        audio_metadata = {
            "file_id": file_id,
            "filename": file_name,
        }
        
        print("🤖 [Combined Analysis] Processing audio with Gemini...")
        result = gs.analyze_day(
            audio_paths=[tmp_path],
            audio_file_metadata=[audio_metadata],
            reference_voices=reference_voices
        )
        
        print("✅ [Combined Analysis] Gemini analysis complete")
        
        # Extract transcript, segments, and expert summary
        transcript_json = result.get('transcript', {})
        segments = transcript_json.get('segments', [])
        summary_text = result.get('summary', '')
        expert_summary = result.get('expert_summary', '')
        
        print(f"📊 Segments: {len(segments)}, Expert: {len(expert_summary)} chars")
        
        if segments:
            unique_speakers = set(seg.get('speaker', 'Unknown') for seg in segments)
            print(f"   Unique speakers: {unique_speakers}")
        
        # ── Step 5: Build expert analysis result ──
        expert_analysis_result = None
        
        if expert_summary and len(expert_summary.strip()) > 50:
            israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
            expert_analysis_result = {
                "success": True,
                "raw_analysis": expert_summary,
                "source": "combined",
                "timestamp": israel_time.isoformat(),
                "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
            }
            print(f"✅ Expert analysis ready: {len(expert_summary)} chars")
        else:
            print("⚠️  No expert summary — using basic summary")
        
        # ── Step 6: Extract speaker names ──
        speaker_names = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker and not speaker.lower().startswith('speaker '):
                speaker_names.add(speaker)
        speaker_names = list(speaker_names)
        
        # ── Step 7: Save transcript to Transcripts/ folder ──
        transcript_file_id = None
        try:
            transcript_save_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "drive_inbox",
                "original_filename": file_name,
                "segments": segments,
                "summary": summary_text,
                "speakers": speaker_names,
                "audio_file_id": file_id,
                "duration_segments": len(segments),
            }
            if expert_analysis_result and expert_analysis_result.get('success'):
                transcript_save_data["expert_analysis"] = expert_analysis_result.get("raw_analysis", "")
                transcript_save_data["persona"] = expert_analysis_result.get("persona", "")
            
            transcript_file_id = drive_service.save_transcript(
                transcript_data=transcript_save_data,
                speakers=speaker_names
            )
            if transcript_file_id:
                print(f"📄 Transcript saved (ID: {transcript_file_id})")
        except Exception as ts_err:
            print(f"⚠️  Transcript save failed: {ts_err}")
        
        # ── Step 8: Save slim entry to memory.json ──
        audio_interaction = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "audio",
            "source": "drive_inbox",
            "file_id": file_id,
            "filename": file_name,
            "summary": summary_text,
            "speakers": speaker_names,
            "segment_count": len(segments),
            "transcript_file_id": transcript_file_id,
        }
        if expert_analysis_result and expert_analysis_result.get('success'):
            audio_interaction["expert_analysis"] = {
                "persona": expert_analysis_result.get("persona"),
                "raw_analysis": expert_analysis_result.get("raw_analysis", "")[:1000],
                "timestamp": expert_analysis_result.get("timestamp"),
            }
        
        drive_service.update_memory(audio_interaction)
        print("✅ Saved to memory.json")
        
        # ── Step 9: Inject Working Memory into Conversation Engine ──
        try:
            from app.services.conversation_engine import conversation_engine
            
            phone = os.environ.get("MY_PHONE_NUMBER", "")
            if phone:
                phone = phone.lstrip("+")
                
                expert_snippet = ""
                if expert_analysis_result and expert_analysis_result.get('success'):
                    expert_snippet = expert_analysis_result.get("raw_analysis", "")[:500]
                
                conversation_engine.inject_session_context(
                    phone=phone,
                    summary=summary_text,
                    speakers=speaker_names,
                    segments=segments,
                    expert_analysis=expert_snippet,
                )
                print("💾 Working memory injected into Conversation Engine")
        except Exception as wm_err:
            print(f"⚠️  Working memory injection failed: {wm_err}")
        
        # ── Step 10: Send summary via WhatsApp (Meta) ──
        try:
            from app.services.whatsapp_provider import WhatsAppProviderFactory
            
            wp = WhatsAppProviderFactory.create_provider(fallback=False)
            phone = os.environ.get("MY_PHONE_NUMBER", "")
            
            if wp and phone:
                summary_msg = f"📥 *הקלטה חדשה מתיקיית Inbox:*\n"
                summary_msg += f"📁 {file_name}\n\n"
                
                if expert_analysis_result and expert_analysis_result.get('success'):
                    raw = expert_analysis_result.get("raw_analysis", "")
                    if raw:
                        summary_msg += raw
                    else:
                        summary_msg += summary_text
                else:
                    summary_msg += summary_text
                
                if len(summary_msg) > 4000:
                    summary_msg = summary_msg[:3950] + "\n\n... (הודעה קוצרה)"
                
                send_result = wp.send_whatsapp(
                    message=summary_msg,
                    to=f"+{phone.lstrip('+')}"
                )
                
                if send_result.get('success'):
                    print(f"📤 Summary sent via WhatsApp ({len(summary_msg)} chars)")
                else:
                    print(f"⚠️  WhatsApp send failed: {send_result.get('error')}")
            else:
                print("⚠️  No WhatsApp provider or phone number — summary not sent")
        except Exception as wa_err:
            print(f"⚠️  WhatsApp send failed: {wa_err}")
        
        # ── Step 11: Move to archive ──
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
        # Clean up temp files
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except:
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
