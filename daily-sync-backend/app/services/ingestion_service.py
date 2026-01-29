"""
Service for ingesting and processing different data types (audio, text, images).
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
from PIL import Image
import base64
import io

import aiosqlite
from app.core.database import get_db_path
from app.core.config import settings


class IngestionService:
    """Service for handling data ingestion."""
    
    def __init__(self):
        self.whisper_model = None
    
    def _load_whisper_model(self):
        """Lazy load Whisper model."""
        if self.whisper_model is None:
            self.whisper_model = whisper.load_model(settings.whisper_model)
        return self.whisper_model
    
    async def ingest_audio(
        self,
        audio_file: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process audio file and transcribe using Whisper.
        
        Args:
            audio_file: Audio file bytes
            filename: Original filename
            metadata: Additional metadata
        
        Returns:
            Dict with transcription and metadata
        """
        # Transcribe audio
        model = self._load_whisper_model()
        
        # Save to temp file for Whisper
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_file)
            tmp_path = tmp_file.name
        
        try:
            result = model.transcribe(tmp_path)
            transcription = result["text"]
        finally:
            Path(tmp_path).unlink()
        
        # Process as text
        return await self.ingest_text(
            text=transcription,
            metadata={
                **(metadata or {}),
                "source": "audio",
                "filename": filename,
                "whisper_model": settings.whisper_model
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
        
        # Store in database
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                INSERT INTO ingestion_logs 
                (timestamp, data_type, content_hash, raw_content, processed_content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                "text",
                content_hash,
                text,
                text,  # For text, processed = raw
                json.dumps(metadata or {})
            ))
            await db.commit()
        
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
        
        # Store in database
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                INSERT INTO ingestion_logs 
                (timestamp, data_type, content_hash, raw_content, processed_content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                "image",
                content_hash,
                base64.b64encode(image_file).decode(),  # Store as base64
                "",  # Vision analysis result will go here
                json.dumps(image_metadata)
            ))
            await db.commit()
        
        return {
            "content_hash": content_hash,
            "timestamp": timestamp,
            "data_type": "image",
            "metadata": image_metadata,
            "note": "Vision analysis not yet implemented"
        }


# Singleton instance
ingestion_service = IngestionService()
