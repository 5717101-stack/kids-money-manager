"""
PyAnnote Speaker Service — Diarization + Embedding Extraction
=============================================================
Wraps pyannote.audio for:
  1. Speaker Diarization — who speaks when (language-agnostic, acoustic-only)
  2. Speaker Embedding Extraction — 256-dim voice fingerprint vectors
  3. Speaker Matching — cosine similarity against enrollment database

Requires:
  - pyannote.audio >= 3.1
  - torch (CPU or CUDA)
  - HUGGINGFACE_TOKEN env var (models are gated on HuggingFace)

GPU support:
  - Auto-detects CUDA GPU and uses it if available
  - On GPU L4: ~0.05x real-time (34min audio → ~1.5min)
  - On CPU:    ~0.5x real-time  (34min audio → ~17min)
  - Models are lazy-loaded on first use to keep startup fast.
"""

import os
import logging
import traceback
import subprocess
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# ─── Lazy-loaded models ──────────────────────────────────────
_diarization_pipeline = None
_embedding_model = None
_device = None                  # torch.device — set during model loading
_models_lock = Lock()
_models_loaded = False          # True only after SUCCESSFUL load
_models_load_failed = False     # True after permanent failure (e.g. ImportError)
_models_last_attempt = 0.0      # Timestamp of last failed attempt
_RETRY_COOLDOWN = 120.0         # Retry loading after 2 minutes on transient failures


def _get_hf_token() -> Optional[str]:
    """Get HuggingFace token from environment."""
    return (os.environ.get("HUGGINGFACE_TOKEN")
            or os.environ.get("HF_TOKEN")
            or None)


def _detect_device():
    """Auto-detect best available device (GPU > CPU)."""
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🚀 GPU detected: {gpu_name} — using CUDA for pyannote")
        return torch.device("cuda")
    else:
        print("ℹ️  No GPU detected — using CPU for pyannote (slower)")
        return torch.device("cpu")


def _ensure_models() -> bool:
    """Lazy-load pyannote models on first use.

    Returns True if models are ready.
    - On success: caches forever (models stay in memory).
    - On ImportError: permanent failure, never retries.
    - On other errors (auth, network): retries after cooldown.
    """
    global _diarization_pipeline, _embedding_model, _device
    global _models_loaded, _models_load_failed, _models_last_attempt

    # Fast path: already loaded successfully
    if _models_loaded:
        return True

    # Permanent failure (missing library)
    if _models_load_failed:
        return False

    # Transient failure cooldown — don't hammer HuggingFace on every request
    import time
    now = time.time()
    if _models_last_attempt > 0 and (now - _models_last_attempt) < _RETRY_COOLDOWN:
        return False

    with _models_lock:
        # Re-check inside lock
        if _models_loaded:
            return True
        if _models_load_failed:
            return False

        hf_token = _get_hf_token()
        if not hf_token:
            logger.error("❌ HUGGINGFACE_TOKEN not set — pyannote models require authentication")
            logger.error("   1. Go to https://huggingface.co/pyannote/speaker-diarization-3.1")
            logger.error("   2. Accept the license agreement")
            logger.error("   3. Create a token at https://huggingface.co/settings/tokens")
            logger.error("   4. Set HUGGINGFACE_TOKEN env var")
            # Not permanent — user might set the token later
            _models_last_attempt = now
            return False

        try:
            import torch
            from pyannote.audio import Pipeline

            _device = _detect_device()

            # ── Try loading from local cache first (no network needed) ────
            # Models are pre-downloaded into the Docker image at build time
            # via HF_HOME=/app/.hf_cache. This avoids HuggingFace 429 errors.
            hf_home = os.environ.get("HF_HOME", "")
            local_cache_exists = hf_home and os.path.isdir(hf_home)

            if local_cache_exists:
                print(f"📦 Found local model cache at {hf_home} — loading offline...")
                try:
                    print("🔄 Loading pyannote diarization pipeline (local cache)...")
                    _diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        token=hf_token,
                        local_files_only=True
                    )
                    _diarization_pipeline.to(_device)
                    print(f"✅ pyannote diarization pipeline loaded from cache (device: {_device})")

                    print("🔄 Loading pyannote embedding model (local cache)...")
                    from pyannote.audio import Inference, Model
                    emb_model = Model.from_pretrained(
                        "pyannote/wespeaker-voxceleb-resnet34-LM",
                        token=hf_token,
                        local_files_only=True
                    )
                    emb_model.to(_device)
                    _embedding_model = Inference(emb_model, window="whole", device=_device)
                    print(f"✅ pyannote embedding model loaded from cache (device: {_device})")

                    _models_loaded = True
                    return True
                except Exception as cache_err:
                    print(f"⚠️ Local cache load failed ({cache_err}), falling back to HuggingFace download...")

            # ── Fallback: download from HuggingFace ───────────────────────
            print("🔄 Loading pyannote diarization pipeline (downloading from HuggingFace)...")
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )
            _diarization_pipeline.to(_device)
            print(f"✅ pyannote diarization pipeline loaded (device: {_device})")

            print("🔄 Loading pyannote embedding model (downloading from HuggingFace)...")
            from pyannote.audio import Inference, Model
            emb_model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM",
                token=hf_token
            )
            emb_model.to(_device)
            _embedding_model = Inference(emb_model, window="whole", device=_device)
            print(f"✅ pyannote embedding model loaded (device: {_device})")

            _models_loaded = True
            return True

        except ImportError as e:
            logger.error(f"❌ pyannote.audio not installed: {e}")
            logger.error("   Run: pip install pyannote.audio torch torchaudio")
            _models_load_failed = True  # Permanent — won't fix without redeploy
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load pyannote models: {e}")
            traceback.print_exc()
            # Transient failure — will retry after cooldown
            _models_last_attempt = now
            _diarization_pipeline = None
            _embedding_model = None
            _device = None
            return False


# ─── Public API ──────────────────────────────────────────────

def is_available() -> bool:
    """Check if pyannote is available (without loading models).

    Returns True if the library is installed AND a HuggingFace token is set.
    """
    try:
        import pyannote.audio  # noqa: F401
        return _get_hf_token() is not None
    except ImportError:
        return False


_DIARIZATION_TIMEOUT_SEC = 1800  # 30 minutes max — fallback to Gemini if exceeded


def _convert_to_wav(audio_path: str) -> Optional[str]:
    """Convert audio to 16kHz mono WAV for optimal pyannote performance.

    pyannote internally resamples to 16kHz mono, but feeding WAV directly
    avoids slow OGG/Opus decoding that can make GPU processing appear hung.

    Returns path to WAV file (caller must clean up), or None on failure.
    """
    import tempfile
    wav_path = tempfile.mktemp(suffix=".wav")
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1",
             "-c:a", "pcm_s16le", wav_path],
            capture_output=True, timeout=120
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            orig_size = os.path.getsize(audio_path)
            wav_size = os.path.getsize(wav_path)
            print(f"   🔄 Converted to WAV: {orig_size//1024}KB → {wav_size//1024}KB (16kHz mono)")
            return wav_path
        else:
            stderr = result.stderr.decode(errors='ignore')[-200:]
            print(f"   ⚠️  ffmpeg conversion failed: {stderr}")
            return None
    except Exception as e:
        print(f"   ⚠️  Audio conversion failed: {e}")
        return None


def is_gpu() -> bool:
    """Check if pyannote models are on GPU."""
    return _device is not None and _device.type == "cuda"


def diarize(audio_path: str,
            num_speakers: int = None,
            min_speakers: int = None,
            max_speakers: int = None,
            timeout: int = None) -> List[Dict[str, Any]]:
    """Run speaker diarization on an audio file.

    Args:
        audio_path: Path to audio file
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        timeout: Max seconds to wait (default: auto based on GPU/CPU)

    Returns:
        List of segments: [{"speaker": "SPEAKER_00", "start": 0.5, "end": 5.2, "duration": 4.7}, ...]
    """
    if not _ensure_models() or _diarization_pipeline is None:
        logger.error("❌ Diarization not available — models not loaded")
        return []

    max_wait = timeout or _DIARIZATION_TIMEOUT_SEC
    wav_path = None

    try:
        # Convert OGG/MP3/etc to WAV for faster processing
        file_ext = os.path.splitext(audio_path)[1].lower()
        actual_path = audio_path
        if file_ext != ".wav":
            wav_path = _convert_to_wav(audio_path)
            if wav_path:
                actual_path = wav_path

        device_tag = "GPU" if is_gpu() else "CPU"
        print(f"🎤 Running pyannote diarization on {actual_path} ({device_tag})...")
        print(f"   ⏱️  Timeout: {max_wait}s — will fall back to Gemini if exceeded")

        kwargs = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        # Run diarization with timeout to prevent hangs on long audio
        import concurrent.futures
        import time as _time
        _diar_start = _time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_diarization_pipeline, actual_path, **kwargs)
            try:
                diarization_result = future.result(timeout=max_wait)
            except concurrent.futures.TimeoutError:
                elapsed = _time.time() - _diar_start
                print(f"⏱️  pyannote TIMEOUT after {elapsed:.0f}s (limit: {max_wait}s)")
                print(f"   ↩️  Falling back to Gemini-only diarization")
                if wav_path and os.path.exists(wav_path):
                    try:
                        os.unlink(wav_path)
                    except Exception:
                        pass
                return []

        elapsed = _time.time() - _diar_start
        print(f"   ⏱️  Diarization completed in {elapsed:.1f}s ({device_tag})")

        # pyannote 3.1 returns a DiarizeOutput dataclass with:
        #   .speaker_diarization  — the Annotation (who speaks when)
        #   .speaker_embeddings   — pre-computed embeddings per speaker
        #   .exclusive_speaker_diarization
        # Older versions return Annotation directly.
        annotation = None
        for attr_name in ('speaker_diarization', 'annotation'):
            candidate = getattr(diarization_result, attr_name, None)
            if candidate is not None and hasattr(candidate, 'itertracks'):
                annotation = candidate
                print(f"✅ Extracted annotation via .{attr_name}")
                break

        if annotation is None:
            # Maybe it IS the annotation directly
            if hasattr(diarization_result, 'itertracks'):
                annotation = diarization_result
                print("✅ Diarization result is already an Annotation")
            elif isinstance(diarization_result, tuple) and len(diarization_result) > 0:
                annotation = diarization_result[0]
                print("✅ Extracted annotation from tuple[0]")
            else:
                print(f"❌ Cannot extract annotation from {type(diarization_result).__name__}")
                print(f"   Available attrs: {[a for a in dir(diarization_result) if not a.startswith('_')]}")
                return []

        segments = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "duration": round(turn.end - turn.start, 2)
            })

        unique_speakers = set(s["speaker"] for s in segments)
        print(f"✅ Diarization complete: {len(segments)} segments, "
              f"{len(unique_speakers)} speakers ({', '.join(sorted(unique_speakers))})")

        return segments

    except Exception as e:
        logger.error(f"❌ Diarization failed: {e}")
        traceback.print_exc()
        return []
    finally:
        # Clean up temp WAV file
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass


def extract_embedding(audio_path: str,
                      start: float = None,
                      end: float = None) -> Optional[np.ndarray]:
    """Extract a speaker embedding from an audio file or segment.

    Args:
        audio_path: Path to audio file
        start: Start time in seconds (None = from beginning)
        end: End time in seconds (None = to end)

    Returns:
        numpy array of shape (256,) or None on failure
    """
    if not _ensure_models() or _embedding_model is None:
        return None

    try:
        if start is not None and end is not None:
            from pyannote.core import Segment
            excerpt = Segment(start, end)
            embedding = _embedding_model.crop(audio_path, excerpt)
        else:
            embedding = _embedding_model(audio_path)

        # Normalize to unit vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    except Exception as e:
        logger.error(f"❌ Embedding extraction failed: {e}")
        traceback.print_exc()
        return None


def extract_embeddings_per_speaker(audio_path: str,
                                   diarization_segments: List[Dict],
                                   min_duration: float = 2.0,
                                   prefer_duration: float = 5.0) -> Dict[str, Dict[str, Any]]:
    """Extract one embedding per speaker from their best (longest) segment.

    Args:
        audio_path: Path to audio file
        diarization_segments: Output from diarize()
        min_duration: Minimum segment duration in seconds
        prefer_duration: Preferred minimum (longer = higher quality embedding)

    Returns:
        {
            "SPEAKER_00": {
                "embedding": np.array([...]),
                "segment": {"start": 12.5, "end": 20.0, "duration": 7.5}
            }, ...
        }
    """
    if not _ensure_models():
        return {}

    # Find the longest segment per speaker
    best_segments = {}
    for seg in diarization_segments:
        speaker = seg["speaker"]
        duration = seg["duration"]
        if duration < min_duration:
            continue
        if (speaker not in best_segments
                or duration > best_segments[speaker]["duration"]):
            best_segments[speaker] = seg

    embeddings = {}
    for speaker, seg in best_segments.items():
        quality = "good" if seg["duration"] >= prefer_duration else "ok"
        print(f"   🔊 Extracting embedding for {speaker} "
              f"({seg['start']:.1f}s-{seg['end']:.1f}s, {seg['duration']:.1f}s, {quality})")
        emb = extract_embedding(audio_path, seg["start"], seg["end"])
        if emb is not None:
            embeddings[speaker] = {
                "embedding": emb,
                "segment": {"start": seg["start"], "end": seg["end"],
                            "duration": seg["duration"]}
            }

    print(f"✅ Extracted {len(embeddings)} speaker embeddings")
    return embeddings


def match_speaker(embedding: np.ndarray,
                  known_centroids: Dict[str, List[float]],
                  threshold: float = 0.75) -> Tuple[Optional[str], float]:
    """Match a speaker embedding against known enrollment centroids.

    Args:
        embedding: The unknown speaker's embedding (unit vector)
        known_centroids: {"person_id": [centroid_values], ...}
        threshold: Minimum cosine similarity for a match

    Returns:
        (person_id, confidence) or (None, best_score) if no match above threshold
    """
    if not known_centroids:
        return None, 0.0

    best_match = None
    best_score = 0.0

    for person_id, centroid in known_centroids.items():
        centroid_arr = np.array(centroid)
        # Cosine similarity (both are unit vectors, so dot product = cosine)
        score = float(np.dot(embedding, centroid_arr))
        if score > best_score:
            best_score = score
            best_match = person_id

    if best_score >= threshold:
        return best_match, best_score
    else:
        return None, best_score


def identify_speakers(audio_path: str,
                      known_centroids: Dict[str, List[float]],
                      diarization_segments: List[Dict] = None,
                      auto_threshold: float = 0.80,
                      suggest_threshold: float = 0.65) -> Dict[str, Dict[str, Any]]:
    """Full pipeline: diarize → embed → match → identify.

    Args:
        audio_path: Path to audio file
        known_centroids: Centroid embeddings from SpeakerIdentityService
        diarization_segments: Pre-computed diarization (or None to compute)
        auto_threshold: Auto-identify if confidence >= this
        suggest_threshold: Suggest match if confidence >= this (but < auto)

    Returns:
        {
            "SPEAKER_00": {
                "person_id": "yuval_laikin" or None,
                "confidence": 0.87,
                "status": "identified" | "suggested" | "unknown",
                "embedding": [0.23, ...],
                "best_segment": {"start": 12.5, "end": 20.0, "duration": 7.5}
            }, ...
        }
    """
    # Step 1: Diarize if not provided
    if diarization_segments is None:
        diarization_segments = diarize(audio_path)
        if not diarization_segments:
            return {}

    # Step 2: Extract embeddings per speaker
    speaker_data = extract_embeddings_per_speaker(
        audio_path, diarization_segments, min_duration=2.0
    )

    # Step 3: Match each speaker
    results = {}
    for speaker_label, data in speaker_data.items():
        embedding = data["embedding"]
        segment = data["segment"]

        person_id, confidence = match_speaker(
            embedding, known_centroids, threshold=suggest_threshold
        )

        if confidence >= auto_threshold and person_id:
            status = "identified"
        elif confidence >= suggest_threshold and person_id:
            status = "suggested"
        else:
            status = "unknown"
            person_id = None

        results[speaker_label] = {
            "person_id": person_id,
            "confidence": round(confidence, 3),
            "status": status,
            "embedding": embedding.tolist(),
            "best_segment": segment
        }

        if person_id:
            print(f"   🎯 {speaker_label} → {person_id} "
                  f"({confidence:.1%} confidence, {status})")
        else:
            print(f"   ❓ {speaker_label} → unknown (best score: {confidence:.1%})")

    return results
