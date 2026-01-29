"""
Router for daily digest endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, datetime, timedelta
import asyncio

from app.services.agent_service import AgentService
from app.services.digest_service import DigestService
from app.core.database import get_mongo_db

router = APIRouter(prefix="/digest", tags=["digest"])


@router.post("/generate")
async def generate_digest(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today."),
    provider: Optional[str] = Query("openai", description="LLM provider: 'openai' or 'anthropic'"),
    model: Optional[str] = Query(None, description="Model name. Uses default if not specified.")
):
    """
    Generate a daily digest by analyzing all ingested content for a given date.
    
    This endpoint:
    1. Retrieves all ingested content for the specified date
    2. Runs it through all three AI agents (Leadership, Strategy, Parenting)
    3. Synthesizes the results into a daily digest
    """
    try:
        if date_str:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = date.today()
        
        # Get all ingested content for the date from MongoDB
        db = await get_mongo_db()
        # Query for documents where timestamp starts with the date (YYYY-MM-DD)
        date_str = target_date.isoformat()
        cursor = db.ingestion_logs.find({
            "timestamp": {"$regex": f"^{date_str}"}
        }).sort("timestamp", 1)
        
        rows = await cursor.to_list(length=None)
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No content found for date {target_date.isoformat()}"
            )
        
        # Combine all content, but limit total size to avoid token limits
        # OpenAI has token limits (e.g., 30K tokens per minute for gpt-4o)
        # We'll limit to roughly 20K tokens (~80K characters) to be safe
        MAX_CONTENT_LENGTH = 80000  # Characters (roughly 20K tokens)
        
        content_parts = []
        total_length = 0
        for row in rows:
            content = row.get("processed_content", "")
            data_type = row.get("data_type", "unknown")
            if content:
                content_str = f"[{data_type.upper()}]: {content}"
                # If adding this would exceed limit, truncate it
                if total_length + len(content_str) > MAX_CONTENT_LENGTH:
                    remaining = MAX_CONTENT_LENGTH - total_length - 100  # Leave room for note
                    if remaining > 1000:  # Only add if we have meaningful space
                        content_str = content_str[:remaining] + "\n[Content truncated due to length...]"
                        content_parts.append(content_str)
                    break
                content_parts.append(content_str)
                total_length += len(content_str)
        
        combined_content = "\n\n".join(content_parts)
        
        if total_length >= MAX_CONTENT_LENGTH:
            combined_content += "\n\n[Note: Some content was truncated to fit token limits. Consider splitting into multiple days or using shorter recordings.]"
        
        # Initialize services
        agent_service = AgentService(provider=provider, model=model)
        digest_service = DigestService(provider=provider, model=model)
        
        # Run all agents
        agent_responses = await agent_service.analyze_with_all_agents(combined_content)
        
        # Generate digest
        digest = await digest_service.generate_daily_digest(
            agent_responses=agent_responses,
            date_str=target_date.isoformat()
        )
        
        return {
            "status": "success",
            "date": target_date.isoformat(),
            "digest": digest
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating digest: {str(e)}")


@router.get("/{date_str}")
async def get_digest(date_str: str):
    """
    Retrieve a daily digest by date.
    
    - **date_str**: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        digest_service = DigestService()
        
        digest = await digest_service.get_digest_by_date(target_date.isoformat())
        
        if not digest:
            raise HTTPException(
                status_code=404,
                detail=f"No digest found for date {date_str}"
            )
        
        return {
            "status": "success",
            "digest": digest
        }
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving digest: {str(e)}")


@router.get("/")
async def list_digests(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List recent daily digests.
    
    - **limit**: Maximum number of digests to return (1-100)
    - **offset**: Number of digests to skip
    """
    try:
        db = await get_mongo_db()
        cursor = db.daily_digests.find().sort("date", -1).skip(offset).limit(limit)
        rows = await cursor.to_list(length=limit)
        
        digests = [
            {
                "date": row["date"],
                "summary": row.get("summary", ""),
                "created_at": row.get("created_at", "")
            }
            for row in rows
        ]
        
        return {
            "status": "success",
            "count": len(digests),
            "digests": digests
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing digests: {str(e)}")
