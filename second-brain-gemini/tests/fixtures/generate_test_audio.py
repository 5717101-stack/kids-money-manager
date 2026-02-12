"""
Generate synthetic test audio fixtures.

Creates audio files with multiple "speakers" using different tones
for testing the audio pipeline without real recordings.

Run once: python -m tests.fixtures.generate_test_audio
"""
import os
import struct
import wave
import math
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "audio"


def generate_tone(frequency: float, duration_sec: float, sample_rate: int = 16000,
                  amplitude: float = 0.5) -> bytes:
    """Generate a sine wave tone as raw PCM bytes."""
    n_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        samples.append(int(value * 32767))
    return struct.pack(f"<{len(samples)}h", *samples)


def generate_silence(duration_sec: float, sample_rate: int = 16000) -> bytes:
    """Generate silence as raw PCM bytes."""
    n_samples = int(sample_rate * duration_sec)
    return b'\x00\x00' * n_samples


def create_two_speaker_audio():
    """
    Create a ~30s audio file simulating two speakers:
    - Speaker A: 300Hz tone (deeper voice)
    - Speaker B: 500Hz tone (higher voice)

    Pattern: A speaks, silence, B speaks, silence, A speaks, B speaks
    """
    sample_rate = 16000
    segments = [
        ("A", generate_tone(300, 5.0, sample_rate)),     # 0-5s: Speaker A
        ("silence", generate_silence(1.0, sample_rate)),  # 5-6s: gap
        ("B", generate_tone(500, 4.0, sample_rate)),     # 6-10s: Speaker B
        ("silence", generate_silence(0.5, sample_rate)),  # 10-10.5s: gap
        ("A", generate_tone(300, 6.0, sample_rate)),     # 10.5-16.5s: Speaker A
        ("silence", generate_silence(1.0, sample_rate)),  # 16.5-17.5s: gap
        ("B", generate_tone(500, 5.0, sample_rate)),     # 17.5-22.5s: Speaker B
        ("silence", generate_silence(0.5, sample_rate)),  # 22.5-23s: gap
        ("A", generate_tone(300, 4.0, sample_rate)),     # 23-27s: Speaker A
        ("silence", generate_silence(0.5, sample_rate)),  # 27-27.5s: gap
        ("B", generate_tone(500, 3.0, sample_rate)),     # 27.5-30.5s: Speaker B
    ]

    audio_data = b"".join(data for _, data in segments)

    filepath = FIXTURES_DIR / "two_speakers_synthetic.wav"
    with wave.open(str(filepath), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

    # Save reference annotation
    annotation = {
        "audio_file": "two_speakers_synthetic.wav",
        "duration_sec": 30.5,
        "speakers": {
            "SPEAKER_A": {"frequency_hz": 300, "description": "Deep voice"},
            "SPEAKER_B": {"frequency_hz": 500, "description": "Higher voice"},
        },
        "segments": [
            {"speaker": "SPEAKER_A", "start": 0.0, "end": 5.0},
            {"speaker": "SPEAKER_B", "start": 6.0, "end": 10.0},
            {"speaker": "SPEAKER_A", "start": 10.5, "end": 16.5},
            {"speaker": "SPEAKER_B", "start": 17.5, "end": 22.5},
            {"speaker": "SPEAKER_A", "start": 23.0, "end": 27.0},
            {"speaker": "SPEAKER_B", "start": 27.5, "end": 30.5},
        ],
    }

    import json
    annotation_path = FIXTURES_DIR / "two_speakers_synthetic.json"
    annotation_path.write_text(json.dumps(annotation, indent=2))

    print(f"✅ Created: {filepath} ({os.path.getsize(filepath)} bytes)")
    print(f"✅ Created: {annotation_path}")
    return filepath


def create_short_voice_note():
    """Create a short (~8s) single-speaker audio for voice note testing."""
    sample_rate = 16000
    audio_data = generate_tone(400, 8.0, sample_rate, amplitude=0.6)

    filepath = FIXTURES_DIR / "short_voice_note.wav"
    with wave.open(str(filepath), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

    print(f"✅ Created: {filepath} ({os.path.getsize(filepath)} bytes)")
    return filepath


if __name__ == "__main__":
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating test audio fixtures...")
    create_two_speaker_audio()
    create_short_voice_note()
    print("\nDone! Audio fixtures ready in tests/fixtures/audio/")
