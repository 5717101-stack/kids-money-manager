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

        # Step 1: Retrieve voice signatures
        known_speaker_names = []
        if drive_memory_service.is_configured and settings.enable_multimodal_voice:
            try:
                max_sigs = settings.max_voice_signatures
                print(f"🎤 Retrieving voice signatures (max: {max_sigs})...")
                reference_voices = drive_memory_service.get_voice_signatures(max_signatures=max_sigs)
                known_speaker_names = [rv['name'].lower() for rv in reference_voices]
                if reference_voices:
                    print(f"✅ Retrieved {len(reference_voices)} voice signature(s)")
            except Exception as e:
                print(f"⚠️  Error retrieving voice signatures: {e}")
                reference_voices = []

        # Step 2: Process with Gemini (COMBINED Diarization + Expert Analysis)
        print("🤖 [Combined Analysis] Processing audio with Gemini...")
        print(f"   Stage: COMBINED - Diarization + Expert Analysis in ONE call")
        result = gemini_service.analyze_day(
            audio_paths=[tmp_path],
            audio_file_metadata=[audio_metadata],
            reference_voices=reference_voices
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
            israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
            expert_analysis_result = {
                "success": True,
                "raw_analysis": expert_summary,
                "source": "combined",
                "timestamp": israel_time.isoformat(),
                "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
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

        # ============================================================
        # Step 3: Save transcript + memory
        # ============================================================

        # Save FULL transcript as separate file in Transcripts/
        transcript_file_id = None
        try:
            transcript_save_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": source,
                "original_filename": audio_metadata.get('filename', ''),
                "segments": segments,
                "summary": summary_text,
                "speakers": speaker_names,
                "audio_file_id": audio_metadata.get('file_id', ''),
                "duration_segments": len(segments),
            }
            if expert_analysis_result and expert_analysis_result.get('success'):
                transcript_save_data["expert_analysis"] = expert_analysis_result.get("raw_analysis", "")
                transcript_save_data["persona"] = expert_analysis_result.get("persona", "")

            transcript_file_id = drive_memory_service.save_transcript(
                transcript_data=transcript_save_data,
                speakers=speaker_names
            )
            if transcript_file_id:
                print(f"📄 [Transcript] Saved to Transcripts/ folder (ID: {transcript_file_id})")
            else:
                print("⚠️  [Transcript] Failed to save to Transcripts/ — continuing anyway")
        except Exception as transcript_err:
            print(f"⚠️  [Transcript] Error saving: {transcript_err}")

        # Save SLIM entry to memory.json (summary + reference only)
        print("💾 [Drive Upload] Saving slim audio interaction to memory...")
        audio_interaction = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
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

        # UPDATE WORKING MEMORY for Zero Latency RAG
        try:
            from app.main import update_last_session_context, _voice_map_cache as vm_cache
            update_last_session_context(
                summary=summary_text,
                speakers=list(speaker_names),
                timestamp=datetime.utcnow().isoformat() + "Z",
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
        # Step 5: Speaker Identification — WebRTC VAD SMART SLICING
        # ============================================================
        unknown_speakers_processed = []
        # Import pending_identifications from main module for voice imprinting
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

        print(f"🔇 Self-identification skip list: {self_names}")

        try:
            from pydub import AudioSegment

            audio_segment = AudioSegment.from_file(tmp_path)
            print(f"✅ Loaded audio for slicing: {len(audio_segment)}ms")

            # ============================================================
            # SMART SLICING ENGINE v3 — WebRTC VAD
            # ============================================================
            TARGET_MIN_MS = 5000
            TARGET_MAX_MS = 7000
            ABS_MIN_MS = 1500
            PAD_BUFFER_MS = 500
            FADE_MS = 40
            OVERLAP_MARGIN_MS = 300
            VAD_AGGRESSIVENESS = 1
            VAD_FRAME_MS = 30
            VAD_SAMPLE_RATE = 16000
            MIN_SPEECH_CLUSTER_MS = 1500
            MIN_SPEECH_RATIO = 0.40
            MAX_SCAN_MS = 30000
            FALLBACK_SLICE_MS = 5000
            MAX_VAD_RETRIES = 2

            # ── Build segment map for ALL speakers ──
            all_segments_by_speaker = {}
            unknown_speakers: Set[str] = set()

            for segment in segments:
                speaker = segment.get('speaker', '')
                if not speaker:
                    continue

                start = segment.get('start', 0)
                end = segment.get('end', 0)
                if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                    continue
                if end <= start:
                    continue

                if speaker not in all_segments_by_speaker:
                    all_segments_by_speaker[speaker] = []
                all_segments_by_speaker[speaker].append({
                    'speaker': speaker,
                    'start': start,
                    'end': end,
                    'start_ms': int(start * 1000),
                    'end_ms': int(end * 1000),
                    'text': segment.get('text', '')
                })

                speaker_lower = speaker.lower()
                is_unknown = (
                    speaker_lower.startswith('speaker ') or
                    speaker.startswith('דובר ') or
                    'unknown' in speaker_lower or
                    speaker_lower == 'speaker'
                )

                if is_unknown and speaker_lower not in self_names:
                    unknown_speakers.add(speaker)

            print(f"📊 All speakers: {list(all_segments_by_speaker.keys())}")
            print(f"📊 Unknown speakers needing ID: {list(unknown_speakers)}")

            if not unknown_speakers and summary_text:
                print("⚠️  No unknown speakers detected - all identified or skipped.")

            # ── WebRTC VAD helpers ──
            vad = None
            try:
                import webrtcvad
                vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
                print(f"✅ [VAD] WebRTC VAD initialized (aggressiveness={VAD_AGGRESSIVENESS})")
            except ImportError:
                print("⚠️  [VAD] webrtcvad not installed — falling back to RMS-based detection")
            except Exception as vad_init_err:
                print(f"⚠️  [VAD] WebRTC VAD init failed ({vad_init_err}) — falling back to RMS")

            def get_other_segments(target_speaker):
                other = []
                for spk, segs in all_segments_by_speaker.items():
                    if spk != target_speaker:
                        other.extend(segs)
                return other

            def calc_overlap_ms(seg_start_ms, seg_end_ms, other_segs):
                total = 0
                for o in other_segs:
                    o_start = o['start_ms'] - OVERLAP_MARGIN_MS
                    o_end = o['end_ms'] + OVERLAP_MARGIN_MS
                    overlap_start = max(seg_start_ms, o_start)
                    overlap_end = min(seg_end_ms, o_end)
                    if overlap_end > overlap_start:
                        total += (overlap_end - overlap_start)
                return total

            def calc_safe_padding(start_ms, end_ms, other_segs, audio_len_ms):
                safe_start = max(0, start_ms - PAD_BUFFER_MS)
                safe_end = min(audio_len_ms, end_ms + PAD_BUFFER_MS)

                for o in other_segs:
                    if o['end_ms'] > safe_start and o['end_ms'] <= start_ms:
                        safe_start = max(safe_start, o['end_ms'] + 100)
                for o in other_segs:
                    if o['start_ms'] >= end_ms and o['start_ms'] < safe_end:
                        safe_end = min(safe_end, o['start_ms'] - 100)

                return safe_start, safe_end

            def vad_analyze_clip(audio_clip, log_format=False):
                if vad is None:
                    return None

                try:
                    pcm_clip = audio_clip.set_frame_rate(VAD_SAMPLE_RATE).set_channels(1).set_sample_width(2)
                    raw_data = pcm_clip.raw_data

                    if log_format:
                        print(f"      📐 [VAD] Audio format: {pcm_clip.frame_rate}Hz, {pcm_clip.channels}ch, {pcm_clip.sample_width*8}-bit, {len(raw_data)} bytes")

                    if pcm_clip.frame_rate != VAD_SAMPLE_RATE:
                        print(f"      ❌ [VAD] ERROR: frame_rate={pcm_clip.frame_rate} (expected {VAD_SAMPLE_RATE})")
                        return None
                    if pcm_clip.channels != 1:
                        print(f"      ❌ [VAD] ERROR: channels={pcm_clip.channels} (expected 1)")
                        return None
                    if pcm_clip.sample_width != 2:
                        print(f"      ❌ [VAD] ERROR: sample_width={pcm_clip.sample_width} (expected 2)")
                        return None

                    bytes_per_frame = VAD_SAMPLE_RATE * 2 * VAD_FRAME_MS // 1000
                    total_frames = len(raw_data) // bytes_per_frame

                    if total_frames == 0:
                        print(f"      ⚠️  [VAD] No complete frames in {len(raw_data)} bytes")
                        return None

                    results = []
                    for i in range(total_frames):
                        offset = i * bytes_per_frame
                        frame = raw_data[offset:offset + bytes_per_frame]
                        if len(frame) < bytes_per_frame:
                            break
                        is_speech = vad.is_speech(frame, VAD_SAMPLE_RATE)
                        frame_offset_ms = i * VAD_FRAME_MS
                        results.append((frame_offset_ms, is_speech))

                    return results
                except Exception as vad_err:
                    print(f"      ⚠️  [VAD] Frame analysis failed: {vad_err}")
                    traceback.print_exc()
                    return None

            def find_best_speech_cluster(vad_results, clip_duration_ms):
                if not vad_results:
                    return None

                total_frames = len(vad_results)
                speech_flags = [is_speech for (_, is_speech) in vad_results]

                GAP_TOLERANCE = 3

                smoothed = list(speech_flags)
                for i in range(len(smoothed)):
                    if not smoothed[i]:
                        left_speech = any(smoothed[max(0, i-GAP_TOLERANCE):i])
                        right_speech = any(smoothed[i+1:min(len(smoothed), i+1+GAP_TOLERANCE)])
                        if left_speech and right_speech:
                            smoothed[i] = True

                clusters = []
                cluster_start = None

                for i, is_speech in enumerate(smoothed):
                    if is_speech and cluster_start is None:
                        cluster_start = i
                    elif not is_speech and cluster_start is not None:
                        cluster_end = i
                        clusters.append((cluster_start, cluster_end))
                        cluster_start = None

                if cluster_start is not None:
                    clusters.append((cluster_start, len(smoothed)))

                if not clusters:
                    return None

                best = None
                best_score = -1

                for c_start, c_end in clusters:
                    c_len_frames = c_end - c_start
                    c_duration_ms = c_len_frames * VAD_FRAME_MS

                    if c_duration_ms < MIN_SPEECH_CLUSTER_MS:
                        continue

                    actual_speech = sum(1 for f in speech_flags[c_start:c_end] if f)
                    ratio = actual_speech / c_len_frames if c_len_frames > 0 else 0

                    if ratio < MIN_SPEECH_RATIO:
                        continue

                    score = c_duration_ms * ratio

                    if score > best_score:
                        best_score = score
                        start_ms = vad_results[c_start][0]
                        end_ms = vad_results[min(c_end, total_frames) - 1][0] + VAD_FRAME_MS
                        confidence = 'High' if ratio >= 0.75 else 'Low'
                        best = (start_ms, end_ms, ratio, confidence)

                return best

            def rms_fallback_check(audio_clip):
                clip_rms = audio_clip.rms
                if clip_rms < 200:
                    return False, 0.0, 'None'

                window_ms = 500
                total_windows = max(1, len(audio_clip) // window_ms)
                active = sum(1 for i in range(total_windows)
                             if audio_clip[i*window_ms:min((i+1)*window_ms, len(audio_clip))].rms >= 200)
                ratio = active / total_windows

                if ratio < 0.3:
                    return False, ratio, 'None'

                confidence = 'High' if ratio >= 0.6 else 'Low'
                return True, ratio, confidence

            # ── Process each unknown speaker with VAD SMART SLICING ──

            def export_and_send_clip(audio_slice, speaker, clip_label):
                import tempfile as tf
                slice_path = None

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
                        sent_msg_id = audio_result.get('caption_message_id') or audio_result.get('wam_id') or audio_result.get('message_id')
                        if sent_msg_id:
                            pending_identifications[sent_msg_id] = {
                                'file_path': slice_path,
                                'speaker_id': speaker
                            }
                            _save_pending_identifications()  # Persist to disk
                            print(f"   📝 Pending identification stored: {sent_msg_id} -> {speaker}")
                            unknown_speakers_processed.append(speaker)
                            if slice_path in slice_files_to_cleanup:
                                slice_files_to_cleanup.remove(slice_path)
                        return True
                    else:
                        print(f"   ⚠️  Failed to send audio slice: {audio_result.get('error')}")
                        return False
                return False

            for speaker in unknown_speakers:
                print(f"\n{'═'*60}")
                print(f"❓ [VAD] SMART SLICING for unknown speaker: {speaker}")
                print(f"{'═'*60}")

                other_segs = get_other_segments(speaker)
                target_segs = all_segments_by_speaker.get(speaker, [])

                if not target_segs:
                    print(f"   ⚠️  No segments found for {speaker} - SKIPPING")
                    continue

                target_segs_sorted = sorted(target_segs, key=lambda s: s['start_ms'])

                print(f"   📋 Speaker has {len(target_segs_sorted)} turn(s):")
                for idx, s in enumerate(target_segs_sorted):
                    dur = s['end_ms'] - s['start_ms']
                    overlap = calc_overlap_ms(s['start_ms'], s['end_ms'], other_segs)
                    print(f"      Turn {idx}: {s['start']:.1f}s-{s['end']:.1f}s ({dur}ms) overlap={overlap}ms")

                clip_sent = False
                vad_rejections = 0

                for turn_idx, turn_seg in enumerate(target_segs_sorted):
                    if clip_sent:
                        break

                    turn_start_ms = turn_seg['start_ms']
                    turn_end_ms = turn_seg['end_ms']
                    turn_duration = turn_end_ms - turn_start_ms

                    if turn_duration < 500:
                        print(f"\n   ⏭️  Turn {turn_idx}: too short ({turn_duration}ms) - skipping")
                        continue

                    scan_end_ms = min(turn_end_ms, turn_start_ms + MAX_SCAN_MS)

                    print(f"\n   🔍 [VAD] Analyzing Turn {turn_idx}: {turn_start_ms}ms → {scan_end_ms}ms ({scan_end_ms - turn_start_ms}ms)")

                    turn_audio = audio_segment[turn_start_ms:scan_end_ms]

                    if len(turn_audio) < 500:
                        print(f"      ⏭️  Audio too short after extraction - skipping")
                        continue

                    vad_results = vad_analyze_clip(turn_audio, log_format=(turn_idx == 0))

                    speech_cluster = None
                    vad_confidence = 'None'

                    if vad_results is not None:
                        total_frames = len(vad_results)
                        speech_frames = sum(1 for _, is_speech in vad_results if is_speech)
                        overall_ratio = speech_frames / total_frames if total_frames > 0 else 0

                        print(f"      📊 [VAD] Frames: {total_frames} total, {speech_frames} speech ({overall_ratio:.0%})")

                        speech_cluster = find_best_speech_cluster(vad_results, len(turn_audio))

                        if speech_cluster:
                            cl_start, cl_end, cl_ratio, vad_confidence = speech_cluster
                            print(f"      🎯 [VAD] Best speech cluster: {cl_start}ms-{cl_end}ms ({cl_end-cl_start}ms, {cl_ratio:.0%} speech, confidence={vad_confidence})")
                        else:
                            vad_rejections += 1
                            print(f"      ❌ [VAD] Rejected clip for {speaker} (No speech cluster ≥{MIN_SPEECH_CLUSTER_MS}ms found, rejection #{vad_rejections})")

                            if vad_rejections >= MAX_VAD_RETRIES:
                                print(f"      🔄 [VAD] {MAX_VAD_RETRIES} rejections reached — triggering FALLBACK SLICER")
                                break
                            continue
                    else:
                        print(f"      📊 [RMS Fallback] Running RMS-based check...")
                        rms_passed, rms_ratio, vad_confidence = rms_fallback_check(turn_audio)

                        if not rms_passed:
                            vad_rejections += 1
                            print(f"      ❌ [VAD] Rejected clip for {speaker} (RMS confidence too low: {rms_ratio:.0%}, rejection #{vad_rejections})")
                            if vad_rejections >= MAX_VAD_RETRIES:
                                print(f"      🔄 [VAD] {MAX_VAD_RETRIES} rejections reached — triggering FALLBACK SLICER")
                                break
                            continue

                        print(f"      ✅ [RMS] Passed: speech ratio={rms_ratio:.0%}, confidence={vad_confidence}")
                        speech_cluster = (0, len(turn_audio), rms_ratio, vad_confidence)

                    # ── DYNAMIC SLICING around the speech cluster ──
                    cluster_start_in_turn, cluster_end_in_turn, cluster_ratio, confidence = speech_cluster

                    abs_cluster_start = turn_start_ms + cluster_start_in_turn
                    abs_cluster_end = turn_start_ms + cluster_end_in_turn
                    cluster_duration = abs_cluster_end - abs_cluster_start

                    print(f"      📍 Cluster in absolute audio: {abs_cluster_start}ms → {abs_cluster_end}ms ({cluster_duration}ms)")

                    if cluster_duration >= TARGET_MIN_MS:
                        if cluster_duration > TARGET_MAX_MS:
                            center = (abs_cluster_start + abs_cluster_end) // 2
                            slice_start = center - TARGET_MAX_MS // 2
                            slice_end = center + TARGET_MAX_MS // 2
                        else:
                            slice_start = abs_cluster_start
                            slice_end = abs_cluster_end
                    else:
                        center = (abs_cluster_start + abs_cluster_end) // 2
                        slice_start = center - TARGET_MIN_MS // 2
                        slice_end = center + TARGET_MIN_MS // 2

                    slice_start, slice_end = calc_safe_padding(
                        slice_start, slice_end, other_segs, len(audio_segment)
                    )

                    slice_start = max(0, slice_start)
                    slice_end = min(len(audio_segment), slice_end)

                    if (slice_end - slice_start) < ABS_MIN_MS:
                        print(f"      ⚠️  Slice too short after padding ({slice_end - slice_start}ms) - skipping turn")
                        vad_rejections += 1
                        if vad_rejections >= MAX_VAD_RETRIES:
                            break
                        continue

                    if (slice_end - slice_start) > TARGET_MAX_MS:
                        slice_end = slice_start + TARGET_MAX_MS

                    print(f"      ✂️  Slice window: {slice_start}ms → {slice_end}ms ({slice_end - slice_start}ms)")

                    audio_slice = audio_segment[slice_start:slice_end]

                    # ── FINAL VAD VERIFICATION ──
                    if vad is not None:
                        final_vad = vad_analyze_clip(audio_slice)
                        if final_vad:
                            final_speech = sum(1 for _, s in final_vad if s)
                            final_ratio = final_speech / len(final_vad) if final_vad else 0
                            if final_ratio < 0.20:
                                vad_rejections += 1
                                print(f"      ❌ [VAD] Final clip verification FAILED: only {final_ratio:.0%} speech (rejection #{vad_rejections})")
                                print(f"      ❌ [VAD] Rejected clip for {speaker} (Confidence too low: {final_ratio:.0%})")
                                if vad_rejections >= MAX_VAD_RETRIES:
                                    break
                                continue
                            print(f"      ✅ [VAD] Final clip verified: {final_ratio:.0%} speech ({final_speech}/{len(final_vad)} frames)")

                    # ── AUDIO ENHANCEMENTS ──
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

                    # ── [VAD] VERIFICATION LOG ──
                    final_duration = len(audio_slice)
                    print(f"\n   ✂️  ═══ [VAD] FINAL CLIP for {speaker} ═══")
                    print(f"      📍 Turn {turn_idx}: {turn_start_ms}ms → {turn_end_ms}ms")
                    print(f"      📍 Speech cluster: {abs_cluster_start}ms → {abs_cluster_end}ms ({cluster_duration}ms)")
                    print(f"      📍 Final slice: {slice_start}ms → {slice_end}ms ({final_duration}ms / {final_duration/1000:.1f}s)")
                    print(f"      🔊 Volume: {audio_slice.dBFS:.1f} dBFS")
                    print(f"      🎯 Speech ratio: {cluster_ratio:.0%} | Confidence: {confidence}")
                    print(f"      💬 Text: \"{turn_seg.get('text', '')[:80]}\"")
                    print(f"   [VAD] Clip generated for {speaker} at {slice_start}ms-{slice_end}ms with confidence {confidence}")

                    # ── EXPORT & SEND ──
                    if export_and_send_clip(audio_slice, speaker, f"VAD-{confidence}"):
                        clip_sent = True
                        break

                # ══════════════════════════════════════════════════════════
                # FALLBACK SLICER
                # ══════════════════════════════════════════════════════════
                if not clip_sent and target_segs_sorted:
                    print(f"\n   🔄 ═══ FALLBACK SLICER for {speaker} ═══")
                    print(f"      VAD rejected {vad_rejections} clip(s). Using brute-force slice.")

                    longest_seg = max(target_segs_sorted, key=lambda s: s['end_ms'] - s['start_ms'])
                    fb_start = longest_seg['start_ms']
                    fb_end = min(longest_seg['end_ms'], fb_start + FALLBACK_SLICE_MS)
                    fb_duration = fb_end - fb_start

                    print(f"      📍 Longest segment: {longest_seg['start']:.1f}s-{longest_seg['end']:.1f}s ({longest_seg['end_ms'] - longest_seg['start_ms']}ms)")
                    print(f"      📍 Fallback slice: {fb_start}ms → {fb_end}ms ({fb_duration}ms)")

                    if fb_duration >= 500:
                        fb_start, fb_end = calc_safe_padding(fb_start, fb_end, other_segs, len(audio_segment))
                        fb_start = max(0, fb_start)
                        fb_end = min(len(audio_segment), fb_end)

                        fallback_slice = audio_segment[fb_start:fb_end]

                        try:
                            target_dbfs = -16.0
                            current_dbfs = fallback_slice.dBFS
                            if current_dbfs != float('-inf') and current_dbfs < 0:
                                gain = target_dbfs - current_dbfs
                                gain = max(min(gain, 20.0), -10.0)
                                fallback_slice = fallback_slice.apply_gain(gain)
                            fallback_slice = fallback_slice.fade_in(FADE_MS).fade_out(FADE_MS)
                        except Exception:
                            pass

                        print(f"      🔊 Fallback volume: {fallback_slice.dBFS:.1f} dBFS | Duration: {len(fallback_slice)}ms")
                        print(f"   [VAD] Clip generated for {speaker} at {fb_start}ms-{fb_end}ms with confidence Fallback")

                        if export_and_send_clip(fallback_slice, speaker, "FALLBACK"):
                            clip_sent = True

                    if not clip_sent:
                        print(f"      ❌ Fallback also failed for {speaker}")

                # ── Final status ──
                if not clip_sent:
                    print(f"\n   🚫 [VAD] No clear speech detected for {speaker}")
                    print(f"      Scanned {len(target_segs_sorted)} turn(s), {vad_rejections} VAD rejection(s).")
                    print(f"      ❌ NOT sending 'מי זה?' — no valid audio clip available.")

        except ImportError:
            print("⚠️  pydub not installed - cannot slice audio for speaker identification")
        except Exception as slice_error:
            print(f"⚠️  Error during speaker identification slicing: {slice_error}")
            traceback.print_exc()

        print(f"✅ [Diarization] Speaker identification: {len(unknown_speakers_processed)} unknown speakers queued")

        # ============================================================
        # Step 6: SMART NOTIFICATION SEQUENCE
        # ============================================================
        print("📱 [WhatsApp Notification] Building smart notification sequence...")

        all_speakers = set()
        for seg in segments:
            speaker = seg.get('speaker', '')
            if speaker:
                all_speakers.add(speaker)

        identified_speakers = []
        unidentified_count = 0

        for speaker in all_speakers:
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

        # ── MESSAGE 1: EXPERT SUMMARY ──
        print(f"📊 [WhatsApp] Decision point:")
        print(f"   expert_analysis_result is None: {expert_analysis_result is None}")
        if expert_analysis_result:
            print(f"   expert_analysis_result.get('success'): {expert_analysis_result.get('success')}")
            print(f"   expert_analysis_result.get('persona'): {expert_analysis_result.get('persona')}")
            raw_len = len(expert_analysis_result.get('raw_analysis', ''))
            print(f"   raw_analysis length: {raw_len} chars")

        if whatsapp_provider:
            # Add source header for Drive inbox files
            source_header = ""
            if source == "drive_inbox":
                filename = audio_metadata.get('filename', '')
                source_header = f"📥 *הקלטה חדשה מתיקיית Inbox:*\n📁 {filename}\n\n"

            if expert_analysis_result and expert_analysis_result.get('success'):
                from app.services.expert_analysis_service import expert_analysis_service
                expert_message = expert_analysis_service.format_for_whatsapp(expert_analysis_result)
                print(f"   📝 Expert message length: {len(expert_message)} chars")

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
                    print("✅ [WhatsApp] Message 1 (Expert Summary) sent")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send expert summary: {reply_result.get('error')}")
            else:
                print(f"   ⚠️  [CRITICAL] Using FALLBACK - expert analysis failed!")
                if expert_analysis_result:
                    print(f"   Error details: {expert_analysis_result.get('error', 'unknown')}")

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
                    if len(summary_text) > 1200:
                        summary_text = summary_text[:1000] + "..."
                    reply_message += f"📝 *סיכום:*\n{summary_text}\n\n"
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
                    print("✅ [WhatsApp] Message 1 (Fallback Summary) sent")
                else:
                    print(f"⚠️  [WhatsApp] Failed to send fallback: {reply_result.get('error')}")

        if unknown_speakers_processed:
            print(f"✅ [WhatsApp] Message 2 (Speaker ID queries) sent for: {unknown_speakers_processed}")

        # ============================================================
        # Step 7: NOTEBOOKLM DEEP ANALYSIS (if enabled)
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

                israel_time = datetime.now(timezone.utc) + timedelta(hours=2)
                nb_metadata = {
                    "filename": audio_metadata.get('filename', ''),
                    "timestamp": israel_time.strftime('%d/%m/%Y %H:%M'),
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
                    infographic_msg = notebooklm_service.format_infographic(notebooklm_analysis)
                    if infographic_msg:
                        nb_result = whatsapp_provider.send_whatsapp(
                            message=infographic_msg,
                            to=f"+{from_number}"
                        )
                        if nb_result.get('success'):
                            print("📓 [NotebookLM] Infographic sent via WhatsApp")
                        else:
                            print(f"⚠️ [NotebookLM] Failed to send infographic: {nb_result.get('error')}")
            else:
                print("ℹ️ [NotebookLM] Disabled — skipping deep analysis")

        except Exception as nb_err:
            print(f"⚠️ [NotebookLM] Error (non-fatal): {nb_err}")
            import traceback
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
