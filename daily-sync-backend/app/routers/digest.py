"""
Router for daily digest endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, datetime, timedelta
import asyncio

from app.services.agent_service import AgentService
from app.services.digest_service import DigestService
import aiosqlite
from app.core.database import get_db_path

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
        
        # Get all ingested content for the date
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("""
                SELECT processed_content, data_type, metadata
                FROM ingestion_logs
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp
            """, (target_date.isoformat(),)) as cursor:
                rows = await cursor.fetchall()
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No content found for date {target_date.isoformat()}"
            )
        
        # Combine all content
        content_parts = []
        for row in rows:
            content = row[0]
            data_type = row[1]
            if content:
                content_parts.append(f"[{data_type.upper()}]: {content}")
        
        combined_content = "\n\n".join(content_parts)
        
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
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("""
                SELECT date, summary, created_at
                FROM daily_digests
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
        
        digests = [
            {
                "date": row[0],
                "summary": row[1],
                "created_at": row[2]
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
