"""
Unified Audio Processing Pipeline
==================================
Single source of truth for ALL audio processing — whether the audio
comes from WhatsApp, Google Drive inbox, or any future source.

Both entry points call `process_audio_core()`:
  - WhatsApp webhook (main.py)     → downloads from WhatsApp API → calls process_audio_core()
  - Drive inbox poller (process_meetings.py) → downloads from Drive → calls process_audio_core()

This guarantees identical behavior: diarization, expert analysis,
speaker identification (VAD), fact identification, transcript saving,
working memory injection, and WhatsApp notifications.
"""

import os
import io
import json
import logging
import tempfile
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Set

logger = logging.getLogger(__name__)


def process_audio_core(
    tmp_path: str,
    from_number: str,
    audio_metadata: Dict[str, Any],
    whatsapp_provider,
    drive_memory_service,
    source: str = "whatsapp",
) -> Dict[str, Any]:
    """
    Core audio processing pipeline — THE SINGLE SOURCE OF TRUTH.

    This function handles everything AFTER the audio file is downloaded
    and saved to a local temp file:

      1. Smart Voice Router (short ≤30s → Conversation Engine)
      2. Retrieve voice signatures
      3. Combined Diarization + Expert Analysis (Gemini)
      4. Segment validation
      5. Save transcript to Transcripts/ folder
      6. Save slim entry to memory.json
      7. Inject Working Memory into Conversation Engine
      8. Proactive Fact Identification
      9. Speaker Identification (WebRTC VAD Smart Slicing)
     10. WhatsApp notification (formatted expert summary)
     11. Cleanup slice files

    Args:
        tmp_path: Path to the audio file on disk
        from_number: User's phone number (without +)
        audio_metadata: Dict with file_id, filename, web_content_link, etc.
        whatsapp_provider: WhatsApp provider instance for sending messages
        drive_memory_service: DriveMemoryService instance
        source: "whatsapp" or "drive_inbox" — for logging/metadata only

    Returns:
        Dict with processing results (summary, speakers, transcript_file_id, etc.)
    """
    from app.core.config import settings
    from app.services.gemini_service import gemini_service
    from app.services.conversation_engine import conversation_engine

    slice_files_to_cleanup = []
    reference_voices = []
    result_info = {"success": False, "source": source}

    # ============================================================
    # RECORDING DATE RESOLUTION
    # Use the REAL recording date (from file metadata) instead of
    # datetime.utcnow() so meetings are indexed by when they
    # actually happened, not when they were uploaded/processed.
    # ============================================================
    recording_date_str = audio_metadata.get("recording_date")
    if recording_date_str:
        try:
            # Parse ISO format from audio_metadata (already UTC)
            recording_date = datetime.fromisoformat(recording_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
            print(f"📅 [RecordingDate] Using date from metadata: {recording_date.isoformat()}Z")
        except (ValueError, AttributeError):
            recording_date = None
    else:
        recording_date = None

    if recording_date is None:
        # Try extracting directly from the audio file
        try:
            from app.services.audio_date_extractor import extract_recording_date
            recording_date = extract_recording_date(tmp_path)
            if recording_date:
                print(f"📅 [RecordingDate] Extracted from file: {recording_date.isoformat()}Z")
        except Exception as date_err:
            print(f"⚠️  [RecordingDate] Extraction failed: {date_err}")

    if recording_date is None:
        recording_date = datetime.utcnow()
        print(f"📅 [RecordingDate] Fallback to processing time: {recording_date.isoformat()}Z")

    # recording_date is now a naive UTC datetime representing the REAL meeting time
    recording_date_iso = recording_date.isoformat() + "Z"
    # Israel time for display purposes (UTC+2)
    recording_date_israel = recording_date + timedelta(hours=2)

    try:
        # ============================================================
        # 🎯 SMART VOICE ROUTER
        # Short voice notes (≤30s) = voice COMMANDS → Conversation Engine
        # Long recordings (>30s) = meetings → Full Analysis Pipeline
        # ============================================================
        VOICE_COMMAND_THRESHOLD_SEC = 30

        try:
            from pydub import AudioSegment as RouteCheckSegment
            voice_check = RouteCheckSegment.from_file(tmp_path)
            duration_sec = len(voice_check) / 1000.0
            print(f"⏱️  [Voice Router] Audio duration: {duration_sec:.1f}s (threshold: {VOICE_COMMAND_THRESHOLD_SEC}s)")

            if duration_sec <= VOICE_COMMAND_THRESHOLD_SEC:
                print(f"💬 [Voice Router] SHORT voice note ({duration_sec:.1f}s) → Conversation Engine")
                print(f"   Skipping: diarization, expert analysis, speaker ID, VAD")

                try:
                    from app.services.model_discovery import MODEL_MAPPING, configure_genai as md_configure
                    import google.generativeai as genai_voice
                    import time as route_time

                    md_configure(settings.google_api_key)
                    flash_model = genai_voice.GenerativeModel(MODEL_MAPPING["flash"])

                    print(f"   📤 Uploading for quick transcription (Flash)...")
                    file_ref = genai_voice.upload_file(
                        path=tmp_path,
                        display_name=f"voice_cmd_{audio_metadata.get('filename', 'audio')}.ogg",
                        mime_type="audio/ogg"
                    )

                    max_upload_wait = 30
                    wait_start = route_time.time()
                    while route_time.time() - wait_start < max_upload_wait:
                        file_ref = genai_voice.get_file(file_ref.name)
                        state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                        if state == "ACTIVE":
                            break
                        elif state == "FAILED":
                            raise Exception(f"Gemini file processing failed: {file_ref.name}")
                        route_time.sleep(1)

                    transcription_response = flash_model.generate_content([
                        file_ref,
                        "תמלל את ההקלטה הקולית הזאת. "
                        "החזר אך ורק את הטקסט שנאמר, בשפה המקורית. "
                        "אל תוסיף כותרות, תיאורים, שמות דוברים או הערות. רק הטקסט עצמו."
                    ])

                    transcribed_text = ""
                    if transcription_response and transcription_response.text:
                        transcribed_text = transcription_response.text.strip()

                    print(f"   📝 Transcription: \"{transcribed_text[:200]}{'...' if len(transcribed_text) > 200 else ''}\"")

                    try:
                        genai_voice.delete_file(file_ref.name)
                    except Exception:
                        pass

                    if not transcribed_text:
                        print(f"   ⚠️  Empty transcription — falling through to full pipeline")
                    else:
                        print(f"   🧠 Routing to Conversation Engine...")

                        ai_response = conversation_engine.process_message(
                            phone=from_number,
                            message=transcribed_text
                        )

                        print(f"   🤖 Response: {ai_response[:200]}{'...' if len(ai_response) > 200 else ''}")

                        if whatsapp_provider and ai_response:
                            reply_result = whatsapp_provider.send_whatsapp(
                                message=ai_response,
                                to=f"+{from_number}"
                            )
                            if reply_result.get('success'):
                                print(f"   ✅ [Voice Router] Response sent successfully")
                            else:
                                print(f"   ⚠️  [Voice Router] Send failed: {reply_result.get('error')}")

                        print(f"\n{'='*60}")
                        print(f"✅ [Voice Router] Short voice note processed via Conversation Engine — DONE")
                        print(f"{'='*60}\n")
                        result_info["success"] = True
                        result_info["route"] = "voice_command"
                        return result_info

                except Exception as transcription_err:
                    print(f"   ❌ [Voice Router] Quick transcription failed: {transcription_err}")
                    traceback.print_exc()
                    print(f"   ↩️  Falling through to full audio pipeline as fallback...")
            else:
                print(f"📊 [Voice Router] LONG recording ({duration_sec:.1f}s > {VOICE_COMMAND_THRESHOLD_SEC}s) → Full Analysis Pipeline")

        except ImportError:
            print(f"⚠️  [Voice Router] pydub not available — using full pipeline for all audio")
        except Exception as router_err:
            print(f"⚠️  [Voice Router] Duration check failed: {router_err} — using full pipeline")

        # ============================================================
        # FULL MEETING ANALYSIS PIPELINE (for recordings >30s)
        # ============================================================

        # Ensure duration_sec is available (may not be set if pydub import failed)
        if 'duration_sec' not in dir() and 'duration_sec' not in locals():
            try:
                from pydub import AudioSegment as FallbackSeg
                _fb = FallbackSeg.from_file(tmp_path)
                duration_sec = len(_fb) / 1000.0
            except Exception:
                duration_sec = 0

        # ============================================================
        # Step 1: pyannote DIARIZATION + SPEAKER IDENTIFICATION
        # If available: pre-compute who speaks when + match to known voices
        # If unavailable: fall back to Gemini-only mode (legacy)
        # ============================================================
        diarization_hints = None
        pyannote_speaker_results = {}
        pyannote_segments = []

        try:
            from app.services.pyannote_service import is_available as pyannote_available, diarize, identify_speakers
            from app.services.speaker_identity_service import speaker_identity_service

            if pyannote_available():
                print("🎤 [pyannote] Speaker diarization engine available")

                # Scale timeout based on audio duration and device
                # GPU L4: ~0.05x real-time (34min → 1.5min). CPU: ~0.5x real-time.
                from app.services.pyannote_service import is_gpu
                if is_gpu():
                    # GPU: generous timeout of 0.2x real-time, min 60s, max 600s
                    diar_timeout = min(max(int(duration_sec * 0.2), 60), 600) if duration_sec else 300
                else:
                    # CPU: 0.5x real-time, min 120s, max 1800s
                    diar_timeout = min(max(int(duration_sec * 0.5), 120), 1800) if duration_sec else 1800
                print(f"   ⏱️  Audio: {duration_sec:.0f}s → diarization timeout: {diar_timeout}s ({'GPU' if is_gpu() else 'CPU'})")

                # Step 1a: Run diarization
                pyannote_segments = diarize(tmp_path, min_speakers=1, max_speakers=6, timeout=diar_timeout)

                if pyannote_segments:
                    print(f"✅ [pyannote] Diarization: {len(pyannote_segments)} segments")

                    # Step 1b: Get known voice centroids from Speaker Identity Graph
                    known_centroids = speaker_identity_service.get_centroid_embeddings()
                    print(f"   📊 Known voice centroids: {len(known_centroids)} people")

                    # Step 1c: Identify speakers via embedding matching
                    pyannote_speaker_results = identify_speakers(
                        audio_path=tmp_path,
                        known_centroids=known_centroids,
                        diarization_segments=pyannote_segments,
                        auto_threshold=settings.pyannote_auto_threshold,
                        suggest_threshold=settings.pyannote_suggest_threshold,
                    )

                    if pyannote_speaker_results:
                        # Build diarization hints for Gemini
                        # Replace SPEAKER_XX labels with real names where identified
                        speaker_name_map = {}
                        speakers_info = {}
                        for spk_label, info in pyannote_speaker_results.items():
                            pid = info.get("person_id")
                            if pid and info["status"] == "identified":
                                real_name = speaker_identity_service.get_person_canonical_name(pid) or pid
                                speaker_name_map[spk_label] = real_name
                                speakers_info[spk_label] = {
                                    "name": real_name,
                                    "person_id": pid,
                                    "confidence": info["confidence"]
                                }
                            elif pid and info["status"] == "suggested":
                                real_name = speaker_identity_service.get_person_canonical_name(pid) or pid
                                speaker_name_map[spk_label] = f"{real_name} (unconfirmed)"
                                speakers_info[spk_label] = {
                                    "name": f"{real_name} (unconfirmed)",
                                    "person_id": pid,
                                    "confidence": info["confidence"]
                                }
                            else:
                                # Unknown — assign friendly label
                                idx = list(pyannote_speaker_results.keys()).index(spk_label) + 1
                                speaker_name_map[spk_label] = f"Unknown Speaker {idx}"
                                speakers_info[spk_label] = {
                                    "name": f"Unknown Speaker {idx}",
                                    "person_id": None,
                                    "confidence": 0
                                }

                        # Build named segments for Gemini
                        named_segments = []
                        for seg in pyannote_segments:
                            named_seg = dict(seg)
                            named_seg["speaker"] = speaker_name_map.get(
                                seg["speaker"], seg["speaker"]
                            )
                            named_segments.append(named_seg)

                        diarization_hints = {
                            "segments": named_segments,
                            "speakers": speakers_info
                        }

                        identified_count = sum(1 for s in speakers_info.values() if s.get("person_id"))
                        print(f"✅ [pyannote] Speaker identification: "
                              f"{identified_count}/{len(speakers_info)} identified")
                    else:
                        print("⚠️ [pyannote] Embedding extraction/matching failed — Gemini will diarize")
                else:
                    print("⚠️ [pyannote] Diarization returned no segments — Gemini will diarize")
            else:
                print("ℹ️ [pyannote] Not available (missing HUGGINGFACE_TOKEN or dependencies)")
                print("   Falling back to Gemini-only diarization (legacy mode)")
        except ImportError:
            print("ℹ️ [pyannote] Not installed — using Gemini-only diarization")
        except Exception as pya_err:
            print(f"⚠️ [pyannote] Error (non-fatal, falling back to Gemini): {pya_err}")
            traceback.print_exc()

        # ============================================================
        # Step 1-legacy: Retrieve voice signatures (only if pyannote is NOT handling ID)
        # ============================================================
        known_speaker_names = []
        if diarization_hints is None:
            # Legacy mode: Gemini does diarization with reference voice comparison
            if drive_memory_service.is_configured and settings.enable_multimodal_voice:
                try:
                    max_sigs = settings.max_voice_signatures
                    print(f"🎤 [Legacy] Retrieving voice signatures (max: {max_sigs})...")
                    reference_voices = drive_memory_service.get_voice_signatures(max_signatures=max_sigs)
                    known_speaker_names = [rv['name'].lower() for rv in reference_voices]
                    if reference_voices:
                        print(f"✅ Retrieved {len(reference_voices)} voice signature(s)")
                except Exception as e:
                    print(f"⚠️  Error retrieving voice signatures: {e}")
                    reference_voices = []
        else:
            print("🎤 [pyannote] Skipping legacy voice signature download (pyannote handled it)")

        # Step 2: Process with Gemini (transcription + expert analysis)
        if diarization_hints:
            print("🤖 [Gemini] Transcription + Expert Analysis (pyannote-assisted)")
        else:
            print("🤖 [Gemini] COMBINED Diarization + Expert Analysis (legacy)")

        result = gemini_service.analyze_day(
            audio_paths=[tmp_path],
            audio_file_metadata=[audio_metadata],
            reference_voices=reference_voices,
            diarization_hints=diarization_hints,
        )

        print("✅ [Combined Analysis] Gemini analysis complete")

        # Extract transcript, segments, and expert summary from SINGLE Gemini call
        transcript_json = result.get('transcript', {})
        segments = transcript_json.get('segments', [])
        summary_text = result.get('summary', '')
        expert_summary = result.get('expert_summary', '')

        print(f"📊 [Combined Analysis] Results:")
        print(f"   Segments: {len(segments)}")
        print(f"   Expert Summary: {len(expert_summary)} chars")

        if segments:
            first_seg = segments[0]
            print(f"   First segment: {first_seg.get('speaker', 'N/A')} - {first_seg.get('text', 'N/A')[:50]}...")
            unique_speakers = set(seg.get('speaker', 'Unknown') for seg in segments)
            print(f"   Unique speakers: {unique_speakers}")

        if expert_summary:
            print(f"   Expert preview: {expert_summary[:100]}...")
        else:
            print("   ⚠️  NO EXPERT SUMMARY - using basic summary as fallback")

        # ============================================================
        # BUILD EXPERT ANALYSIS RESULT
        # ============================================================
        expert_analysis_result = None

        if expert_summary and len(expert_summary.strip()) > 50:
            expert_analysis_result = {
                "success": True,
                "raw_analysis": expert_summary,
                "source": "combined",
                "timestamp": recording_date_israel.isoformat(),
                "timestamp_display": recording_date_israel.strftime('%d/%m/%Y %H:%M')
            }
            print(f"✅ [Expert Analysis] SUCCESS from combined prompt: {len(expert_summary)} chars")
        else:
            print(f"⚠️  [Expert Analysis] No expert summary - using basic fallback")
            expert_analysis_result = {
                "success": False,
                "error": "Expert summary not generated",
                "source": "combined"
            }

        # Validate segments
        valid_segments = []
        for seg in segments:
            start = seg.get('start')
            end = seg.get('end')
            if start is not None and end is not None:
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    if end > start and start >= 0:
                        valid_segments.append(seg)
        segments = valid_segments

        # Extract speaker names
        speaker_names = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker and not speaker.lower().startswith('speaker '):
                speaker_names.add(speaker)
        speaker_names = list(speaker_names)

        # Extract topics and sentiment from pyannote-assisted Gemini output
        topics = transcript_json.get('topics', [])
        speaker_sentiment = transcript_json.get('speaker_sentiment', {})

        # ============================================================
        # Step 3: SEND WHATSAPP IMMEDIATELY (before Drive saves!)
        # Critical: user gets analysis even if Drive/container crashes
        # ============================================================
        print("📱 [WhatsApp] Sending analysis FIRST (before Drive saves)...")

        all_speakers_set = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker:
                all_speakers_set.add(speaker)

        identified_speakers = []
        unidentified_count = 0
        for speaker in all_speakers_set:
            speaker_lower = speaker.lower()
            is_unknown = (
                speaker_lower.startswith('speaker ') or
                speaker.startswith('דובר ') or
                'unknown' in speaker_lower or
                speaker_lower == 'speaker' or
                speaker_lower == 'unknown' or
                speaker == ''
            )
            if is_unknown:
                unidentified_count += 1
            else:
                identified_speakers.append(speaker)

        if whatsapp_provider:
            source_header = ""
            if source == "drive_inbox":
                filename = audio_metadata.get('filename', '')
                source_header = f"📥 *הקלטה חדשה מתיקיית Inbox:*\n📁 {filename}\n\n"

            if expert_analysis_result and expert_analysis_result.get('success'):
                from app.services.expert_analysis_service import expert_analysis_service
                expert_message = expert_analysis_service.format_for_whatsapp(expert_analysis_result)

                header = source_header
                header += "✅ *ההקלטה נשמרה ונותחה!*\n\n"
                header += "👥 *משתתפים:* "
                if identified_speakers:
                    header += ", ".join(sorted(identified_speakers))
                if unidentified_count > 0:
                    header += f" (+{unidentified_count} לא מזוהים)"
                if not identified_speakers and unidentified_count == 0:
                    header += "(לא זוהו)"
                header += "\n\n"

                full_message = header + expert_message
                print(f"   📤 Total message length: {len(full_message)} chars")

                reply_result = whatsapp_provider.send_whatsapp(
                    message=full_message,
                    to=f"+{from_number}"
                )
                if reply_result.get('success'):
                    print("✅ [WhatsApp] Expert Summary sent IMMEDIATELY")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send expert summary: {reply_result.get('error')}")
            else:
                reply_message = source_header
                reply_message += "✅ *ההקלטה נשמרה!*\n\n"
                reply_message += "👥 *משתתפים:* "
                if identified_speakers:
                    reply_message += ", ".join(sorted(identified_speakers))
                if unidentified_count > 0:
                    if identified_speakers:
                        reply_message += f" (+{unidentified_count} לא מזוהים)"
                    else:
                        reply_message += f"{unidentified_count} דוברים לא מזוהים"
                if not identified_speakers and unidentified_count == 0:
                    reply_message += "(לא זוהו)"
                reply_message += "\n\n"
                if summary_text and len(summary_text.strip()) > 20:
                    st = summary_text[:1000] + "..." if len(summary_text) > 1200 else summary_text
                    reply_message += f"📝 *סיכום:*\n{st}\n\n"
                else:
                    reply_message += "📝 *סיכום:* לא הצלחתי לייצר סיכום מפורט.\n\n"
                reply_message += "📈 *קאיזן:*\n"
                reply_message += "✓ לשימור: השיחה התקיימה והוקלטה\n"
                reply_message += "→ לשיפור: בדוק את איכות ההקלטה\n\n"
                reply_message += "📄 התמלול המלא זמין בדרייב."

                reply_result = whatsapp_provider.send_whatsapp(
                    message=reply_message,
                    to=f"+{from_number}"
                )
                if reply_result.get('success'):
                    print("✅ [WhatsApp] Fallback Summary sent IMMEDIATELY")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send fallback: {reply_result.get('error')}")

        # ============================================================
        # Step 3a: Unknown Speaker Clip Extraction & Send
        # IMMEDIATELY after analysis — before any Drive saves!
        # Critical: clips sent even if container crashes during Drive ops
        # ============================================================
        unknown_speakers_processed = []
        slice_files_to_cleanup = []
        try:
            from app.main import pending_identifications, _voice_map_cache, _save_pending_identifications
        except ImportError:
            pending_identifications = {}
            _voice_map_cache = {}
            _save_pending_identifications = lambda: None

        # SELF-IDENTIFICATION SKIP
        self_names = {'itzik', 'itzhak', 'איציק', 'יצחק', 'speaker 1', 'speaker a', 'דובר 1'}
        for rv in reference_voices:
            self_names.add(rv['name'].lower())

        # Update voice map cache with pyannote-identified speakers
        if pyannote_speaker_results:
            for spk_label, info in pyannote_speaker_results.items():
                if info.get("person_id") and info["status"] == "identified":
                    from app.services.speaker_identity_service import speaker_identity_service as _sig
                    real_name = _sig.get_person_canonical_name(info["person_id"]) or info["person_id"]
                    _voice_map_cache[spk_label.lower()] = real_name
                    self_names.add(real_name.lower())

        print(f"🔇 Self-identification skip list: {self_names}")

        # ── Shared helper: export clip and send via WhatsApp ──
        def _export_and_send_clip(audio_slice, speaker, clip_label, embedding=None):
            """Export an audio slice to OGG and send via WhatsApp for identification."""
            import tempfile as tf
            FADE_MS = 40
            slice_path = None

            # Audio enhancements
            try:
                target_dbfs = -16.0
                current_dbfs = audio_slice.dBFS
                if current_dbfs != float('-inf') and current_dbfs < 0:
                    gain = target_dbfs - current_dbfs
                    gain = max(min(gain, 20.0), -10.0)
                    audio_slice = audio_slice.apply_gain(gain)
                audio_slice = audio_slice.fade_in(FADE_MS).fade_out(FADE_MS)
            except Exception as enhance_err:
                print(f"      ⚠️  Enhancement failed: {enhance_err}")

            try:
                with tf.NamedTemporaryFile(delete=False, suffix='.ogg') as slice_file:
                    audio_slice.export(
                        slice_file.name,
                        format='ogg',
                        codec='libopus',
                        parameters=['-b:a', '64k', '-ar', '48000']
                    )
                    slice_path = slice_file.name
                    slice_size = os.path.getsize(slice_path)
                    print(f"   💾 Exported: OGG/Opus ({slice_size} bytes) [{clip_label}]")
            except Exception as ogg_err:
                print(f"   ⚠️  OGG export failed ({ogg_err}), falling back to MP3...")
                with tf.NamedTemporaryFile(delete=False, suffix='.mp3') as slice_file:
                    audio_slice.export(
                        slice_file.name,
                        format='mp3',
                        bitrate='128k',
                        parameters=['-ar', '44100']
                    )
                    slice_path = slice_file.name
                    slice_size = os.path.getsize(slice_path)
                    print(f"   💾 Exported: MP3/128k ({slice_size} bytes) [{clip_label}]")

            slice_files_to_cleanup.append(slice_path)

            if whatsapp_provider and hasattr(whatsapp_provider, 'send_audio'):
                caption = f"🔊 זוהה דובר חדש: *{speaker}*\nמי זה/זו? (הגב עם השם)"
                audio_result = whatsapp_provider.send_audio(
                    audio_path=slice_path,
                    caption=caption,
                    to=f"+{from_number}"
                )

                if audio_result.get('success'):
                    # Store pending data under BOTH audio and caption message IDs.
                    # WhatsApp sends audio + caption as 2 separate messages; the user
                    # can reply to EITHER one, so we need both IDs in the lookup dict.
                    audio_msg_id = audio_result.get('wam_id') or audio_result.get('message_id')
                    caption_msg_id = audio_result.get('caption_message_id')

                    if audio_msg_id or caption_msg_id:
                        pending_data = {
                            'file_path': slice_path,
                            'speaker_id': speaker
                        }
                        if embedding is not None:
                            pending_data['embedding'] = embedding
                            print(f"   🧬 Embedding stored for auto-enrollment ({len(embedding)} dims)")

                        stored_ids = []
                        if audio_msg_id:
                            pending_identifications[audio_msg_id] = pending_data
                            stored_ids.append(f"audio={audio_msg_id}")
                        if caption_msg_id and caption_msg_id != audio_msg_id:
                            pending_identifications[caption_msg_id] = pending_data
                            stored_ids.append(f"caption={caption_msg_id}")
                        _save_pending_identifications()
                        print(f"   📝 Pending identification stored: [{', '.join(stored_ids)}] -> {speaker}")
                        unknown_speakers_processed.append(speaker)
                        if slice_path in slice_files_to_cleanup:
                            slice_files_to_cleanup.remove(slice_path)
                    return True
                else:
                    print(f"   ⚠️  Failed to send audio slice: {audio_result.get('error')}")
                    return False
            return False

        # ══════════════════════════════════════════════════════════════
        # PATH A: pyannote-powered clip extraction (PREFERRED)
        # pyannote already found the best segment per speaker — use it!
        # ══════════════════════════════════════════════════════════════
        _used_pyannote_clips = False

        if pyannote_speaker_results:
            try:
                from pydub import AudioSegment
                audio_segment = AudioSegment.from_file(tmp_path)
                audio_len_ms = len(audio_segment)

                unknown_pyannote = {
                    spk: info for spk, info in pyannote_speaker_results.items()
                    if info.get("status") == "unknown"
                }

                if unknown_pyannote:
                    _used_pyannote_clips = True
                    print(f"\n{'='*60}")
                    print(f"🎯 [pyannote] DIRECT CLIP EXTRACTION for {len(unknown_pyannote)} unknown speaker(s)")
                    print(f"{'='*60}")

                    for spk_label, info in unknown_pyannote.items():
                        best_seg = info.get("best_segment", {})
                        start_sec = best_seg.get("start", 0)
                        end_sec = best_seg.get("end", 0)
                        duration_sec = best_seg.get("duration", end_sec - start_sec)
                        embedding = info.get("embedding")

                        # Get the friendly name from diarization_hints
                        friendly_name = "Unknown Speaker"
                        if diarization_hints:
                            friendly_name = diarization_hints.get("speakers", {}).get(spk_label, {}).get("name", spk_label)

                        # Skip self
                        if friendly_name.lower() in self_names:
                            print(f"   🔇 Skipping self: {friendly_name}")
                            continue

                        print(f"\n   🎤 {friendly_name} ({spk_label})")
                        print(f"      📍 Best segment: {start_sec:.1f}s → {end_sec:.1f}s ({duration_sec:.1f}s)")

                        if duration_sec < 1.0:
                            print(f"      ⚠️  Segment too short ({duration_sec:.1f}s) — skipping")
                            continue

                        # Convert to ms and apply bounds
                        start_ms = int(start_sec * 1000)
                        end_ms = int(end_sec * 1000)

                        # Cap at 7 seconds, centered on segment
                        TARGET_MAX_MS = 7000
                        if (end_ms - start_ms) > TARGET_MAX_MS:
                            center = (start_ms + end_ms) // 2
                            start_ms = center - TARGET_MAX_MS // 2
                            end_ms = center + TARGET_MAX_MS // 2

                        start_ms = max(0, start_ms)
                        end_ms = min(audio_len_ms, end_ms)

                        print(f"      ✂️  Clip window: {start_ms}ms → {end_ms}ms ({end_ms - start_ms}ms)")

                        audio_slice = audio_segment[start_ms:end_ms]
                        print(f"      🔊 Volume: {audio_slice.dBFS:.1f} dBFS | Duration: {len(audio_slice)}ms")

                        if _export_and_send_clip(audio_slice, friendly_name, f"pyannote-direct", embedding=embedding):
                            print(f"      ✅ Clip sent for {friendly_name}")
                        else:
                            print(f"      ❌ Failed to send clip for {friendly_name}")
                else:
                    print("✅ [pyannote] All speakers identified — no clips needed")

            except ImportError:
                print("⚠️  pydub not installed — cannot extract clips")
            except Exception as pya_clip_err:
                print(f"⚠️  [pyannote] Clip extraction error: {pya_clip_err}")
                traceback.print_exc()

        # PATH B: Legacy VAD Smart Slicer (when pyannote is NOT available)
        if not _used_pyannote_clips and unidentified_count > 0:
            print("ℹ️  [Legacy] Using VAD Smart Slicer (pyannote not available or no unknowns from pyannote)")
            # Legacy clip extraction runs later if needed (Step 5)

        print(f"✅ [Clips] {len(unknown_speakers_processed)} unknown speaker clip(s) sent to user")

        # ============================================================
        # Step 3.5: Save transcript + memory (Drive operations)
        # Non-critical: wrapped in try/except so crashes don't lose analysis
        # ============================================================

        # Save FULL transcript as separate file in Transcripts/
        transcript_file_id = None

        try:
            transcript_save_data = {
                "timestamp": recording_date_iso,
                "source": source,
                "original_filename": audio_metadata.get('filename', ''),
                "segments": segments,
                "summary": summary_text,
                "speakers": speaker_names,
                "audio_file_id": audio_metadata.get('file_id', ''),
                "duration_segments": len(segments),
                "topics": topics,
                "speaker_sentiment": speaker_sentiment,
                "diarization_engine": "pyannote" if diarization_hints else "gemini",
            }

            # Add person_id linkage if pyannote identified speakers
            if pyannote_speaker_results:
                person_ids = {}
                for spk_label, info in pyannote_speaker_results.items():
                    if info.get("person_id"):
                        person_ids[spk_label] = info["person_id"]
                if person_ids:
                    transcript_save_data["person_ids"] = person_ids

            if expert_analysis_result and expert_analysis_result.get('success'):
                transcript_save_data["expert_analysis"] = expert_analysis_result.get("raw_analysis", "")
                transcript_save_data["persona"] = expert_analysis_result.get("persona", "")

            transcript_file_id = drive_memory_service.save_transcript(
                transcript_data=transcript_save_data,
                speakers=speaker_names,
                recording_date=recording_date,
            )
            if transcript_file_id:
                print(f"📄 [Transcript] Saved to Transcripts/ folder (ID: {transcript_file_id})")
            else:
                print("⚠️  [Transcript] Failed to save to Transcripts/ — continuing anyway")
        except Exception as transcript_err:
            print(f"⚠️  [Transcript] Error saving: {transcript_err}")

        # Save SLIM entry to memory.json (summary + reference only)
        try:
            print("💾 [Drive Upload] Saving slim audio interaction to memory...")
            audio_interaction = {
                "timestamp": recording_date_iso,
                "type": "audio",
                "source": source,
                "file_id": audio_metadata.get('file_id', ''),
                "web_content_link": audio_metadata.get('web_content_link', ''),
                "web_view_link": audio_metadata.get('web_view_link', ''),
                "filename": audio_metadata.get('filename', ''),
                "summary": summary_text,
                "speakers": speaker_names,
                "segment_count": len(segments),
                "transcript_file_id": transcript_file_id,
                "from_number": from_number
            }

            if expert_analysis_result and expert_analysis_result.get('success'):
                audio_interaction["expert_analysis"] = {
                    "persona": expert_analysis_result.get("persona"),
                    "persona_keys": expert_analysis_result.get("persona_keys"),
                    "context": expert_analysis_result.get("context"),
                    "speakers": expert_analysis_result.get("speakers"),
                    "raw_analysis": expert_analysis_result.get("raw_analysis", "")[:1000],
                    "timestamp": expert_analysis_result.get("timestamp")
                }
                print(f"📊 Including expert analysis summary in memory (persona: {expert_analysis_result.get('persona')})")

            drive_memory_service.update_memory(audio_interaction)
            print("✅ Saved slim audio interaction to memory")
        except Exception as mem_err:
            print(f"⚠️  [Drive] Memory save failed (non-fatal, analysis already sent): {mem_err}")

        # ============================================================
        # Step 3.5: UPDATE SPEAKER IDENTITY GRAPH
        # ============================================================
        try:
            from app.services.speaker_identity_service import speaker_identity_service

            if pyannote_speaker_results:
                israel_date = recording_date_israel.strftime('%Y-%m-%d')

                for spk_label, info in pyannote_speaker_results.items():
                    person_id = info.get("person_id")
                    if not person_id:
                        continue

                    # Add conversation entry for each identified speaker
                    speaker_sentiment_data = speaker_sentiment.get(
                        speaker_identity_service.get_person_canonical_name(person_id) or spk_label,
                        {}
                    )
                    sentiment_score = speaker_sentiment_data.get("score") if isinstance(speaker_sentiment_data, dict) else None

                    speaker_identity_service.add_conversation(
                        person_id=person_id,
                        date=israel_date,
                        transcript_id=transcript_file_id,
                        audio_file_id=audio_metadata.get('file_id', ''),
                        topics=topics,
                        sentiment=sentiment_score,
                        summary=summary_text[:500] if summary_text else None
                    )
                    print(f"   📊 [SIG] Updated conversation index for {person_id}")

                # Record voice mapping for this session
                mapping_record = {}
                for spk_label, info in pyannote_speaker_results.items():
                    mapping_record[spk_label] = {
                        "person_id": info.get("person_id"),
                        "confidence": info.get("confidence", 0)
                    }
                speaker_identity_service.record_voice_mapping(
                    date=israel_date,
                    audio_file_id=audio_metadata.get('file_id', ''),
                    mappings=mapping_record
                )

                # Save to Drive
                speaker_identity_service.save_if_dirty()
                print(f"✅ [SIG] Speaker Identity Graph updated and saved")

        except ImportError:
            pass  # SpeakerIdentityService not available
        except Exception as sig_err:
            print(f"⚠️ [SIG] Error updating Speaker Identity Graph (non-fatal): {sig_err}")
            traceback.print_exc()

        # UPDATE WORKING MEMORY for Zero Latency RAG
        try:
            from app.main import update_last_session_context, _voice_map_cache as vm_cache
            update_last_session_context(
                summary=summary_text,
                speakers=list(speaker_names),
                timestamp=recording_date_iso,
                transcript_file_id=audio_metadata.get('file_id', ''),
                segments=segments,
                full_transcript=transcript_json,
                identified_speakers=vm_cache.copy(),
                expert_analysis=expert_analysis_result if expert_analysis_result and expert_analysis_result.get('success') else None
            )
        except Exception as wm_legacy_err:
            print(f"⚠️  [WorkingMemory] Legacy update failed: {wm_legacy_err}")

        # Inject Working Memory into Conversation Engine
        try:
            expert_snippet = ""
            if expert_analysis_result and expert_analysis_result.get('success'):
                expert_snippet = expert_analysis_result.get("raw_analysis", "")[:500]

            conversation_engine.inject_session_context(
                phone=from_number,
                summary=summary_text,
                speakers=speaker_names,
                segments=segments,
                expert_analysis=expert_snippet
            )
            print("💾 [ConvEngine] Working memory injected for next chat interaction")
        except Exception as wm_err:
            print(f"⚠️  [ConvEngine] Working memory injection failed: {wm_err}")

        # ============================================================
        # Step 4: PROACTIVE FACT IDENTIFICATION
        # ============================================================
        try:
            from app.services.context_writer_service import context_writer

            print("🧠 [FactID] Scanning transcript for new facts...")
            new_facts = context_writer.identify_facts(summary_text, segments)

            if new_facts:
                confirmation_msg = context_writer.format_fact_confirmation(new_facts)
                if confirmation_msg and whatsapp_provider:
                    send_result = whatsapp_provider.send_whatsapp(
                        message=confirmation_msg,
                        to=f"+{from_number}"
                    )
                    msg_id = send_result.get("message_id", "")
                    context_writer.store_pending(from_number, new_facts, msg_id)
                    print(f"   ✅ [FactID] Sent {len(new_facts)} fact(s) for confirmation")
            else:
                print("   ℹ️ [FactID] No new facts detected")
        except Exception as fact_err:
            print(f"   ⚠️ [FactID] Error: {fact_err}")
            traceback.print_exc()

        # ============================================================
        # Step 5: NOTEBOOKLM DEEP ANALYSIS (if enabled)
        # ============================================================
        notebooklm_analysis = None
        try:
            from app.services.notebooklm_service import notebooklm_service

            if notebooklm_service.is_enabled:
                print("📓 [NotebookLM] Starting deep analysis...")

                # Build full transcript text from segments
                full_transcript_text = "\n".join(
                    f"{seg.get('speaker', '?')}: {seg.get('text', '')}"
                    for seg in segments
                    if seg.get('text')
                )

                nb_metadata = {
                    "filename": audio_metadata.get('filename', ''),
                    "timestamp": recording_date_israel.strftime('%d/%m/%Y %H:%M'),
                    "source": source,
                    "file_id": audio_metadata.get('file_id', ''),
                }

                notebooklm_analysis = notebooklm_service.analyze_recording(
                    transcript_text=full_transcript_text,
                    expert_summary=expert_summary if expert_summary else "",
                    speakers=list(speaker_names),
                    segments=segments,
                    metadata=nb_metadata,
                    drive_memory_service=drive_memory_service,
                )

                if notebooklm_analysis and whatsapp_provider:
                    print(f"📓 [NotebookLM] Analysis complete — generating infographic...")
                    print(f"   Analysis keys: {list(notebooklm_analysis.keys()) if isinstance(notebooklm_analysis, dict) else type(notebooklm_analysis)}")
                    # Try to generate a visual infographic image
                    image_sent = False
                    try:
                        from app.services.infographic_generator import generate_infographic
                        print("📓 [NotebookLM] Calling generate_infographic()...")
                        infographic_path = generate_infographic(notebooklm_analysis)
                        print(f"📓 [NotebookLM] Infographic path: {infographic_path}")
                        if infographic_path:
                            file_size = os.path.getsize(infographic_path) if os.path.exists(infographic_path) else 0
                            print(f"📓 [NotebookLM] Infographic file size: {file_size} bytes")
                        if infographic_path and hasattr(whatsapp_provider, 'send_image'):
                            print(f"📓 [NotebookLM] Sending image via WhatsApp...")
                            img_result = whatsapp_provider.send_image(
                                image_path=infographic_path,
                                caption="📓 ניתוח מעמיק — Second Brain",
                                to=f"+{from_number}"
                            )
                            if img_result.get('success'):
                                print("🖼️ [NotebookLM] Infographic IMAGE sent via WhatsApp ✅")
                                image_sent = True
                            else:
                                print(f"⚠️ [NotebookLM] Image send failed: {img_result}")
                            # Cleanup temp file
                            try:
                                os.remove(infographic_path)
                            except Exception:
                                pass
                        elif not infographic_path:
                            print("⚠️ [NotebookLM] generate_infographic returned None/empty")
                        elif not hasattr(whatsapp_provider, 'send_image'):
                            print("⚠️ [NotebookLM] WhatsApp provider missing send_image method")
                    except Exception as img_err:
                        print(f"⚠️ [NotebookLM] Image generation failed: {img_err}")
                        traceback.print_exc()

                    # Fallback: send text infographic if image failed
                    if not image_sent:
                        print("📓 [NotebookLM] Falling back to text infographic...")
                        infographic_msg = notebooklm_service.format_infographic(notebooklm_analysis)
                        if infographic_msg:
                            nb_result = whatsapp_provider.send_whatsapp(
                                message=infographic_msg,
                                to=f"+{from_number}"
                            )
                            if nb_result.get('success'):
                                print("📓 [NotebookLM] Text infographic sent (fallback)")
                            else:
                                print(f"⚠️ [NotebookLM] Text fallback also failed: {nb_result.get('error')}")
            else:
                print("ℹ️ [NotebookLM] Disabled — skipping deep analysis")

        except Exception as nb_err:
            print(f"⚠️ [NotebookLM] Error (non-fatal): {nb_err}")
            traceback.print_exc()

        print(f"\n{'='*60}")
        print(f"✅ AUDIO PROCESSING COMPLETED (source: {source})")
        print(f"{'='*60}\n")

        result_info.update({
            "success": True,
            "route": "full_pipeline",
            "speakers": speaker_names,
            "unknown_speakers_processed": unknown_speakers_processed,
            "transcript_file_id": transcript_file_id,
            "summary": summary_text,
            "expert_analysis": expert_analysis_result,
            "notebooklm_analysis": notebooklm_analysis,
            "diarization_engine": "pyannote" if diarization_hints else "gemini",
            "pyannote_speakers": {
                k: {"person_id": v.get("person_id"), "status": v.get("status"), "confidence": v.get("confidence")}
                for k, v in pyannote_speaker_results.items()
            } if pyannote_speaker_results else None,
        })

    except Exception as e:
        print(f"❌ AUDIO PROCESSING ERROR: {e}")
        traceback.print_exc()
        result_info["error"] = str(e)

        if whatsapp_provider:
            try:
                whatsapp_provider.send_whatsapp(
                    message="⚠️ שגיאה בעיבוד האודיו. נסה שוב מאוחר יותר.",
                    to=f"+{from_number}"
                )
            except Exception:
                pass

    finally:
        # Cleanup slice files
        for f in slice_files_to_cleanup:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except Exception:
                pass

        # Cleanup reference voice temp files
        for rv in reference_voices:
            try:
                file_path = rv.get('file_path', '')
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass

    return result_info
