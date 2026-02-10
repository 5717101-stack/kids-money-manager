"""
PyAnnote Speaker Service — Diarization + Embedding Extraction
=============================================================
Wraps pyannote.audio for:
  1. Speaker Diarization — who speaks when (language-agnostic, acoustic-only)
  2. Speaker Embedding Extraction — 256-dim voice fingerprint vectors
  3. Speaker Matching — cosine similarity against enrollment database

Requires:
  - pyannote.audio >= 3.1
  - torch (CPU version sufficient)
  - HUGGINGFACE_TOKEN env var (models are gated on HuggingFace)

Memory: ~1.2GB for diarization pipeline + ~300MB for embedding model
Total: ~1.5GB — fits in 4GB RAM with headroom.
Models are lazy-loaded on first use to keep startup fast.
"""

import os
import logging
import traceback
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# ─── Lazy-loaded models ──────────────────────────────────────
_diarization_pipeline = None
_embedding_model = None
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


def _ensure_models() -> bool:
    """Lazy-load pyannote models on first use.

    Returns True if models are ready.
    - On success: caches forever (models stay in memory).
    - On ImportError: permanent failure, never retries.
    - On other errors (auth, network): retries after cooldown.
    """
    global _diarization_pipeline, _embedding_model
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
            logger.error("   4. Set HUGGINGFACE_TOKEN env var on Render")
            # Not permanent — user might set the token later
            _models_last_attempt = now
            return False

        try:
            import torch
            from pyannote.audio import Pipeline

            print("🔄 Loading pyannote diarization pipeline (first run downloads ~1.5GB)...")
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )
            _diarization_pipeline.to(torch.device("cpu"))
            print("✅ pyannote diarization pipeline loaded")

            print("🔄 Loading pyannote embedding model...")
            from pyannote.audio import Inference, Model
            _embedding_model = Inference(
                Model.from_pretrained(
                    "pyannote/wespeaker-voxceleb-resnet34-LM",
                    token=hf_token
                ),
                window="whole"
            )
            print("✅ pyannote embedding model loaded")

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


def diarize(audio_path: str,
            num_speakers: int = None,
            min_speakers: int = None,
            max_speakers: int = None) -> List[Dict[str, Any]]:
    """Run speaker diarization on an audio file.

    Args:
        audio_path: Path to audio file
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers

    Returns:
        List of segments: [{"speaker": "SPEAKER_00", "start": 0.5, "end": 5.2, "duration": 4.7}, ...]
    """
    if not _ensure_models() or _diarization_pipeline is None:
        logger.error("❌ Diarization not available — models not loaded")
        return []

    try:
        print(f"🎤 Running pyannote diarization on {audio_path}...")

        kwargs = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        diarization_result = _diarization_pipeline(audio_path, **kwargs)

        # pyannote 3.1+ returns DiarizeOutput (namedtuple with .annotation)
        # older versions return Annotation directly
        annotation = getattr(diarization_result, 'annotation', diarization_result)
        if not hasattr(annotation, 'itertracks'):
            # Some versions return a tuple (annotation, embeddings)
            if isinstance(diarization_result, tuple):
                annotation = diarization_result[0]
            else:
                print(f"⚠️ Unexpected diarization output type: {type(diarization_result)}")
                print(f"   Attributes: {dir(diarization_result)}")
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
