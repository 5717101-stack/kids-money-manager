"""
Audio Recording Date Extractor
================================
Extracts the REAL recording date from audio files, instead of using
the upload/processing date.

Strategy (in priority order):
  1. MP4/M4A mvhd atom — embedded creation timestamp (most reliable,
     survives uploads to Drive/WhatsApp). Works for Apple Voice Memos
     and most M4A/MP4 recordings.
  2. Filename pattern — Apple Voice Memos names files as
     "YYYYMMDD HHMMSS.m4a". Easy to parse, but user can rename.
  3. Fallback — returns None, caller should use datetime.utcnow().
"""

import re
import struct
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# MP4 epoch: 1904-01-01 00:00:00 UTC
_MP4_EPOCH = datetime(1904, 1, 1)

# Filename patterns for common recording apps
# Apple Voice Memos: "20260126 165443.m4a"
_FILENAME_PATTERNS = [
    # YYYYMMDD HHMMSS (Apple Voice Memos)
    re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{2})(\d{2})(\d{2})"),
    # YYYY-MM-DD HH-MM-SS or YYYY-MM-DD_HH-MM-SS
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[_\s](\d{2})-(\d{2})-(\d{2})"),
    # YYYYMMDD_HHMMSS (alternative naming)
    re.compile(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"),
]


def extract_recording_date(file_path: str) -> Optional[datetime]:
    """
    Extract the original recording date from an audio file.

    Tries multiple strategies in order of reliability:
      1. MP4 mvhd atom (embedded in file, survives uploads)
      2. Filename timestamp patterns (Apple Voice Memos, etc.)
      3. Returns None if no date can be extracted

    Args:
        file_path: Path to the audio file on disk

    Returns:
        datetime (UTC, naive) of the recording, or None if not extractable.
        The returned datetime is ALWAYS in UTC.
    """
    path = Path(file_path)

    # ── Strategy 1: MP4/M4A mvhd atom ──
    if path.suffix.lower() in ('.m4a', '.mp4', '.aac', '.mov'):
        date = _extract_mp4_creation_time(file_path)
        if date:
            logger.info(f"📅 [DateExtractor] Recording date from mvhd atom: {date.isoformat()}Z")
            return date

    # ── Strategy 2: Filename pattern ──
    filename = path.stem  # filename without extension
    date = _extract_date_from_filename(filename)
    if date:
        logger.info(f"📅 [DateExtractor] Recording date from filename: {date.isoformat()}Z")
        return date

    # ── Strategy 3: No date found ──
    logger.info(f"📅 [DateExtractor] Could not extract recording date from {path.name} — will use processing time")
    return None


def _extract_mp4_creation_time(file_path: str) -> Optional[datetime]:
    """
    Extract creation_time from the MP4/M4A mvhd (Movie Header) atom.

    The mvhd atom contains a 32-bit or 64-bit creation_time field
    measured in seconds since 1904-01-01 00:00:00 UTC.

    This is embedded BY THE RECORDING DEVICE and does not change
    when the file is copied, uploaded, or moved.

    Args:
        file_path: Path to the MP4/M4A file

    Returns:
        datetime (UTC, naive) or None if extraction fails
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Find 'mvhd' atom marker
        idx = data.find(b'mvhd')
        if idx == -1:
            logger.debug("[DateExtractor] mvhd atom not found in file")
            return None

        # Version byte (0 = 32-bit timestamps, 1 = 64-bit)
        version = data[idx + 4]

        if version == 0:
            # 32-bit: creation_time at offset +8, modification_time at +12
            if idx + 12 > len(data):
                return None
            creation_time = struct.unpack('>I', data[idx + 8:idx + 12])[0]
        elif version == 1:
            # 64-bit: creation_time at offset +8, modification_time at +16
            if idx + 16 > len(data):
                return None
            creation_time = struct.unpack('>Q', data[idx + 8:idx + 16])[0]
        else:
            logger.debug(f"[DateExtractor] Unknown mvhd version: {version}")
            return None

        if creation_time == 0:
            logger.debug("[DateExtractor] mvhd creation_time is 0 (not set)")
            return None

        # Convert from MP4 epoch (1904-01-01) to regular datetime
        creation_dt = _MP4_EPOCH + timedelta(seconds=creation_time)

        # Sanity check: date should be between 2000 and 2100
        if creation_dt.year < 2000 or creation_dt.year > 2100:
            logger.warning(f"[DateExtractor] mvhd date out of range: {creation_dt}")
            return None

        return creation_dt

    except Exception as e:
        logger.debug(f"[DateExtractor] Error reading mvhd: {e}")
        return None


def _extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Try to extract a recording date from the filename using known patterns.

    Common patterns:
      - Apple Voice Memos: "20260126 165443" → 2026-01-26 16:54:43
      - Generic: "2026-01-26_16-54-43" → 2026-01-26 16:54:43

    Note: The time in the filename is typically in LOCAL time (Israel = UTC+2/+3).
    We convert to UTC by subtracting 2 hours (standard Israel offset).

    Args:
        filename: The filename without extension

    Returns:
        datetime (UTC, naive) or None if no pattern matches
    """
    for pattern in _FILENAME_PATTERNS:
        match = pattern.search(filename)
        if match:
            try:
                groups = match.groups()
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                hour, minute, second = int(groups[3]), int(groups[4]), int(groups[5])

                local_dt = datetime(year, month, day, hour, minute, second)

                # Sanity check
                if local_dt.year < 2000 or local_dt.year > 2100:
                    continue

                # Convert from Israel local time (UTC+2) to UTC
                # Note: This is approximate — doesn't account for DST (UTC+3 in summer).
                # But the mvhd atom (Strategy 1) is already UTC, so this fallback
                # is only used when mvhd is not available.
                utc_dt = local_dt - timedelta(hours=2)
                return utc_dt

            except (ValueError, IndexError):
                continue

    return None
