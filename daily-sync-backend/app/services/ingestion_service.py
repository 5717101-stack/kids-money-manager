"""
Service for ingesting and processing different data types (audio, text, images).
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
from PIL import Image
import base64
import io
import tempfile

from app.core.database import get_mongo_db
from app.core.config import settings

# OpenAI for Whisper API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class IngestionService:
    """Service for handling data ingestion."""
    
    def __init__(self):
        self.whisper_model = None
        self.openai_client = None
    
    def _load_whisper_model(self):
        """Lazy load Whisper model (for local Whisper)."""
        if self.whisper_model is None:
            self.whisper_model = whisper.load_model(settings.whisper_model)
    
    def _get_openai_client(self):
        """Get OpenAI client for Whisper API."""
        # Always check if API key changed and recreate client if needed
        current_key = settings.openai_api_key
        if not current_key:
            raise ValueError("OpenAI API key not set. Please set OPENAI_API_KEY in .env file.")
        
        # If client exists but key changed, recreate it
        if self.openai_client is None or (hasattr(self, '_last_api_key') and self._last_api_key != current_key):
            self.openai_client = OpenAI(api_key=current_key)
            self._last_api_key = current_key
            print(f"[INGESTION] OpenAI client created/recreated with key: {current_key[:30]}...")
        
        return self.openai_client
        return self.whisper_model
    
    async def ingest_audio(
        self,
        audio_file: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process audio file and transcribe using Whisper API or local Whisper.
        
        If use_whisper_api is True (default), uses OpenAI Whisper API which:
        - Supports MP3, M4A, WAV, and many other formats directly
        - No ffmpeg required
        - No format conversion needed
        
        Args:
            audio_file: Audio file bytes
            filename: Original filename
            metadata: Additional metadata
        
        Returns:
            Dict with transcription and metadata
        """
        # Use OpenAI Whisper API if enabled (recommended - supports MP3 directly)
        if settings.use_whisper_api and OPENAI_AVAILABLE and settings.openai_api_key:
            return await self._transcribe_with_whisper_api(audio_file, filename, metadata)
        
        # Fallback to local Whisper (requires WAV format)
        return await self._transcribe_with_local_whisper(audio_file, filename, metadata)
    
    async def _transcribe_with_whisper_api(
        self,
        audio_file: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI Whisper API.
        Supports MP3, M4A, WAV, and many other formats directly - no conversion needed!
        Automatically compresses large files to fit within API limits (25MB).
        """
        try:
            client = self._get_openai_client()
            
            # Determine file format from filename
            file_format = None
            if filename:
                _, ext = os.path.splitext(filename.lower())
                if ext:
                    file_format = ext[1:]  # Remove the dot
            
            # Check file size (OpenAI limit is 25MB)
            MAX_SIZE = 25 * 1024 * 1024  # 25MB in bytes
            file_size = len(audio_file)
            
            # If file is too large, compress it
            if file_size > MAX_SIZE:
                audio_file = await self._compress_audio_for_api(audio_file, file_format)
                file_size = len(audio_file)
                
                # If still too large after compression, try more aggressive compression
                if file_size > MAX_SIZE:
                    audio_file = await self._compress_audio_aggressively(audio_file, file_format)
                    file_size = len(audio_file)
                    
                    # If still too large, raise error with helpful message
                    if file_size > MAX_SIZE:
                        raise ValueError(
                            f"Audio file is too large ({file_size / (1024*1024):.1f}MB) even after compression. "
                            f"OpenAI Whisper API limit is 25MB. "
                            f"Please split the audio into smaller files or use a shorter recording."
                        )
            
            # Save to temp file for API (OpenAI API needs a file)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format or "mp3"}') as tmp_file:
                tmp_file.write(audio_file)
                tmp_path = tmp_file.name
            
            try:
                # Call OpenAI Whisper API
                with open(tmp_path, 'rb') as audio_file_obj:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file_obj,
                        language="he"  # Hebrew - can be auto-detected if None
                    )
                
                transcription = transcript.text
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            # Process as text
            return await self.ingest_text(
                text=transcription,
                metadata={
                    **(metadata or {}),
                    "source": "audio",
                    "filename": filename,
                    "whisper_model": "whisper-1-api",
                    "transcription_method": "openai_api"
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error message for size limit
            if "413" in error_msg or "Maximum content size" in error_msg:
                raise ValueError(
                    f"Audio file is too large for Whisper API (limit: 25MB). "
                    f"Please split the audio into smaller files or record a shorter audio. "
                    f"Original error: {error_msg}"
                )
            raise ValueError(f"Error transcribing audio with Whisper API: {error_msg}")
    
    async def _compress_audio_for_api(
        self,
        audio_file: bytes,
        file_format: Optional[str] = None
    ) -> bytes:
        """
        Compress audio file to reduce size while maintaining reasonable quality.
        Converts to MP3 with lower bitrate if needed.
        """
        try:
            from pydub import AudioSegment
            
            # Load audio
            audio_input = io.BytesIO(audio_file)
            if file_format and file_format.lower() == 'wav':
                audio = AudioSegment.from_wav(audio_input)
            else:
                audio_input.seek(0)
                audio = AudioSegment.from_file(audio_input, format=file_format)
            
            # Convert to mono and reduce sample rate to save space
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(16000)  # 16kHz (good for speech)
            
            # Export as MP3 with lower bitrate (64kbps is good for speech)
            output = io.BytesIO()
            audio.export(output, format="mp3", bitrate="64k")
            return output.getvalue()
            
        except Exception as e:
            # If compression fails, return original (will fail with clear error)
            return audio_file
    
    async def _compress_audio_aggressively(
        self,
        audio_file: bytes,
        file_format: Optional[str] = None
    ) -> bytes:
        """
        More aggressive compression - lower bitrate and sample rate.
        Use only if regular compression isn't enough.
        """
        try:
            from pydub import AudioSegment
            
            # Load audio
            audio_input = io.BytesIO(audio_file)
            if file_format and file_format.lower() == 'wav':
                audio = AudioSegment.from_wav(audio_input)
            else:
                audio_input.seek(0)
                audio = AudioSegment.from_file(audio_input, format=file_format)
            
            # More aggressive: mono, lower sample rate, lower bitrate
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(12000)  # 12kHz (still good for speech)
            
            # Export as MP3 with very low bitrate (32kbps - minimum for speech)
            output = io.BytesIO()
            audio.export(output, format="mp3", bitrate="32k")
            return output.getvalue()
            
        except Exception as e:
            # If compression fails, return original
            return audio_file
    
    async def _transcribe_with_local_whisper(
        self,
        audio_file: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using local Whisper (requires WAV format).
        This is the fallback method if Whisper API is not available.
        """
        # Check if file is already WAV format
        import wave
        is_wav = False
        try:
            wav_io = io.BytesIO(audio_file)
            wave.open(wav_io)
            is_wav = True
        except:
            pass
        
        # If not WAV, try to convert (but this may require ffmpeg)
        if not is_wav:
            # Try using ffmpeg directly first (works for MP3, M4A, etc.)
            import subprocess
            import tempfile
            
            # Determine format from filename
            file_format = None
            if filename:
                _, ext = os.path.splitext(filename.lower())
                if ext:
                    file_format = ext[1:]  # Remove the dot
            
            # Check if ffmpeg is available (try multiple paths)
            ffmpeg_available = False
            ffmpeg_path = None
            
            # Try common ffmpeg paths
            possible_paths = [
                'ffmpeg',  # In PATH
                '/usr/local/bin/ffmpeg',
                '/opt/homebrew/bin/ffmpeg',
                '/usr/bin/ffmpeg'
            ]
            
            for path in possible_paths:
                try:
                    result = subprocess.run(
                        [path, '-version'],
                        capture_output=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        ffmpeg_available = True
                        ffmpeg_path = path
                        break
                except:
                    continue
            
            if ffmpeg_available:
                # Use ffmpeg to convert to WAV (16kHz mono)
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format or "mp3"}') as input_file:
                        input_file.write(audio_file)
                        input_path = input_file.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as output_file:
                        output_path = output_file.name
                    
                    # Convert to WAV 16kHz mono using ffmpeg
                    subprocess.run(
                        [
                            ffmpeg_path,
                            '-i', input_path,
                            '-ar', '16000',  # Sample rate 16kHz
                            '-ac', '1',      # Mono
                            '-y',            # Overwrite output
                            output_path
                        ],
                        capture_output=True,
                        check=True,
                        timeout=30
                    )
                    
                    # Read the converted WAV file
                    with open(output_path, 'rb') as f:
                        audio_file = f.read()
                    
                    # Clean up temp files
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                    
                except subprocess.CalledProcessError as e:
                    # Clean up temp files on error
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                    raise ValueError(
                        f"Could not convert audio file using ffmpeg. "
                        f"Error: {e.stderr.decode() if e.stderr else str(e)}. "
                        f"Please ensure your audio file is valid, or convert to WAV format first."
                    )
                except Exception as e:
                    # Clean up temp files on error
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                    raise ValueError(
                        f"Error processing audio with ffmpeg: {str(e)}. "
                        f"Please try converting to WAV format first."
                    )
            else:
                # Fallback: Try using ffmpeg via subprocess with direct path, or pydub
                # First, try to find and use ffmpeg directly even if not in PATH
                ffmpeg_found = False
                for test_path in ['/usr/local/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg', '/usr/bin/ffmpeg']:
                    if os.path.exists(test_path) and os.access(test_path, os.X_OK):
                        try:
                            # Test if it's actually executable
                            test_result = subprocess.run(
                                [test_path, '-version'],
                                capture_output=True,
                                timeout=2
                            )
                            if test_result.returncode == 0:
                                ffmpeg_path = test_path
                                ffmpeg_found = True
                                break
                        except:
                            continue
                
                if ffmpeg_found:
                    # Use the found ffmpeg
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format or "mp3"}') as input_file:
                            input_file.write(audio_file)
                            input_path = input_file.name
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as output_file:
                            output_path = output_file.name
                        
                        subprocess.run(
                            [
                                ffmpeg_path,
                                '-i', input_path,
                                '-ar', '16000',
                                '-ac', '1',
                                '-y',
                                output_path
                            ],
                            capture_output=True,
                            check=True,
                            timeout=30
                        )
                        
                        with open(output_path, 'rb') as f:
                            audio_file = f.read()
                        
                        try:
                            os.unlink(input_path)
                            os.unlink(output_path)
                        except:
                            pass
                    except Exception as e:
                        try:
                            os.unlink(input_path)
                            os.unlink(output_path)
                        except:
                            pass
                        # Fall through to pydub
                        ffmpeg_found = False
                
                if not ffmpeg_found:
                    # Fallback to pydub (may need ffprobe for some formats)
                    try:
                        from pydub import AudioSegment
                        
                        audio_input = io.BytesIO(audio_file)
                        
                        # For WAV, use from_wav (doesn't need ffprobe)
                        if file_format and file_format.lower() == 'wav':
                            audio = AudioSegment.from_wav(audio_input)
                        else:
                            # For other formats, try with pydub
                            audio_input.seek(0)
                            audio = AudioSegment.from_file(audio_input, format=file_format)
                        
                        # Convert to WAV format (16kHz mono, which Whisper prefers)
                        audio = audio.set_frame_rate(16000).set_channels(1)
                        wav_io = io.BytesIO()
                        audio.export(wav_io, format="wav")
                        audio_file = wav_io.getvalue()
                        
                    except Exception as e:
                        raise ValueError(
                            f"Could not process audio file format '{file_format}'. "
                            f"Error: {str(e)}. "
                            f"ffmpeg is not available or not working. Please install ffmpeg for MP3/M4A support, "
                            f"or convert your audio to WAV format first. "
                            f"WAV format works without any additional dependencies. "
                            f"To install ffmpeg: brew install ffmpeg (if Homebrew is installed)"
                        )
        
            # Try simple conversion with pydub (may not work for MP3 without ffmpeg)
            try:
                from pydub import AudioSegment
                audio_input = io.BytesIO(audio_file)
                
                # Determine format from filename
                file_format = None
                if filename:
                    _, ext = os.path.splitext(filename.lower())
                    if ext:
                        file_format = ext[1:]  # Remove the dot
                
                # Try to load with pydub
                if file_format and file_format.lower() == 'wav':
                    audio = AudioSegment.from_wav(audio_input)
                else:
                    # For other formats, pydub may need ffmpeg/ffprobe
                    audio_input.seek(0)
                    audio = AudioSegment.from_file(audio_input, format=file_format)
                
                # Convert to WAV format (16kHz mono, which Whisper prefers)
                audio = audio.set_frame_rate(16000).set_channels(1)
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                audio_file = wav_io.getvalue()
                is_wav = True
                
            except Exception as e:
                raise ValueError(
                    f"Could not convert audio file to WAV format. "
                    f"Error: {str(e)}. "
                    f"Please use OpenAI Whisper API (set use_whisper_api=True in config) "
                    f"or convert your audio to WAV format first. "
                    f"Whisper API supports MP3 directly without any conversion."
                )
        
        # If it's WAV, optimize it for Whisper (16kHz mono) using pydub if available
        if is_wav:
            try:
                from pydub import AudioSegment
                audio_input = io.BytesIO(audio_file)
                audio = AudioSegment.from_wav(audio_input)
                audio = audio.set_frame_rate(16000).set_channels(1)
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                audio_file = wav_io.getvalue()
            except:
                # If pydub fails, use WAV as-is (Whisper can handle it)
                pass
        
        # Transcribe audio with local Whisper
        model = self._load_whisper_model()
        
        # Save to temp file for Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_file)
            tmp_path = tmp_file.name
        
        try:
            result = model.transcribe(tmp_path)
            transcription = result["text"]
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise ValueError(f"Error transcribing audio: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        # Process as text
        return await self.ingest_text(
            text=transcription,
            metadata={
                **(metadata or {}),
                "source": "audio",
                "filename": filename,
                "whisper_model": settings.whisper_model,
                "transcription_method": "local_whisper"
            }
        )
    
    async def ingest_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process text input.
        
        Args:
            text: Text content
            metadata: Additional metadata
        
        Returns:
            Dict with processed content and metadata
        """
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        timestamp = datetime.utcnow().isoformat()
        
        # Store in MongoDB
        db = await get_mongo_db()
        await db.ingestion_logs.insert_one({
            "timestamp": timestamp,
            "data_type": "text",
            "content_hash": content_hash,
            "raw_content": text,
            "processed_content": text,  # For text, processed = raw
            "metadata": metadata or {},
            "created_at": timestamp
        })
        
        return {
            "content_hash": content_hash,
            "timestamp": timestamp,
            "data_type": "text",
            "processed_content": text,
            "metadata": metadata or {}
        }
    
    async def ingest_image(
        self,
        image_file: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process image file (placeholder for vision analysis).
        
        Args:
            image_file: Image file bytes
            filename: Original filename
            metadata: Additional metadata
        
        Returns:
            Dict with image metadata (vision analysis to be added)
        """
        # For now, just store metadata
        # TODO: Add vision analysis using GPT-4 Vision or Claude Vision
        content_hash = hashlib.sha256(image_file).hexdigest()
        timestamp = datetime.utcnow().isoformat()
        
        # Get image dimensions
        image = Image.open(io.BytesIO(image_file))
        width, height = image.size
        
        image_metadata = {
            **(metadata or {}),
            "source": "image",
            "filename": filename,
            "width": width,
            "height": height,
            "format": image.format
        }
        
        # Store in MongoDB
        db = await get_mongo_db()
        await db.ingestion_logs.insert_one({
            "timestamp": timestamp,
            "data_type": "image",
            "content_hash": content_hash,
            "raw_content": base64.b64encode(image_file).decode(),  # Store as base64
            "processed_content": "",  # Vision analysis result will go here
            "metadata": image_metadata,
            "created_at": timestamp
        })
        
        return {
            "content_hash": content_hash,
            "timestamp": timestamp,
            "data_type": "image",
            "metadata": image_metadata,
            "note": "Vision analysis not yet implemented"
        }


# Singleton instance
ingestion_service = IngestionService()
