"""
Router for data ingestion endpoints.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import json

from app.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/audio")
async def ingest_audio(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """
    Ingest audio file and transcribe using Whisper.
    
    - **file**: Audio file (supports common formats: mp3, wav, m4a, etc.)
    - **metadata**: Optional JSON string with additional metadata
    """
    try:
        audio_bytes = await file.read()
        metadata_dict = json.loads(metadata) if metadata else None
        
        result = await ingestion_service.ingest_audio(
            audio_file=audio_bytes,
            filename=file.filename,
            metadata=metadata_dict
        )
        
        return {
            "status": "success",
            "message": "Audio ingested and transcribed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@router.post("/text")
async def ingest_text(
    text: str = Form(...),
    metadata: Optional[str] = Form(None)
):
    """
    Ingest text content.
    
    - **text**: Text content to ingest
    - **metadata**: Optional JSON string with additional metadata
    """
    try:
        metadata_dict = json.loads(metadata) if metadata else None
        
        result = await ingestion_service.ingest_text(
            text=text,
            metadata=metadata_dict
        )
        
        return {
            "status": "success",
            "message": "Text ingested successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text: {str(e)}")


@router.post("/image")
async def ingest_image(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """
    Ingest image file.
    
    - **file**: Image file (supports common formats: jpg, png, etc.)
    - **metadata**: Optional JSON string with additional metadata
    
    Note: Vision analysis is not yet implemented.
    """
    try:
        image_bytes = await file.read()
        metadata_dict = json.loads(metadata) if metadata else None
        
        result = await ingestion_service.ingest_image(
            image_file=image_bytes,
            filename=file.filename,
            metadata=metadata_dict
        )
        
        return {
            "status": "success",
            "message": "Image ingested successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
