"""
Service for generating daily digests from agent analyses.
"""

import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
import aiosqlite
from app.core.database import get_db_path


class DigestService:
    """Service for synthesizing daily digests."""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.llm = get_llm(provider=provider, model=model)
        self.output_parser = StrOutputParser()
    
    async def generate_daily_digest(
        self,
        agent_responses: Dict[str, Any],
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive daily digest from all agent responses.
        
        Args:
            agent_responses: Dict with responses from all three agents
            date_str: Date string (YYYY-MM-DD). Defaults to today.
        
        Returns:
            Dict with complete daily digest
        """
        if date_str is None:
            date_str = date.today().isoformat()
        
        # Extract insights from each agent
        leadership_insights = agent_responses.get("leadership_coach", {}).get("response", "")
        strategy_insights = agent_responses.get("strategy_consultant", {}).get("response", "")
        parenting_insights = agent_responses.get("parenting_coach", {}).get("response", "")
        
        # Create synthesis prompt
        synthesis_prompt = """You are a synthesis expert. Your role is to combine insights from three specialized coaches into a cohesive, actionable daily digest.

## Input from Three Experts:

**Leadership Coach (Simon Sinek persona):**
{leadership_insights}

**Strategy Consultant:**
{strategy_insights}

**Parenting & Home Coach (Adler Institute persona):**
{parenting_insights}

## Your Task:

Create a comprehensive Daily Digest for {date} that includes:

1. **Executive Summary** (2-3 sentences)
   - A high-level overview of the day's key themes

2. **Insights by Category**
   - **Leadership:** Key leadership insights and opportunities
   - **Strategy:** Strategic observations and recommendations
   - **Home & Parenting:** Family and home life insights

3. **Action Items for Tomorrow**
   - 3-5 concrete, actionable items prioritized by impact
   - Each item should be specific, measurable, and tied to one of the three domains

4. **Reflection Questions**
   - 2-3 thought-provoking questions to consider

Make the digest practical, inspiring, and actionable. Write in a warm but professional tone."""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(synthesis_prompt),
            HumanMessagePromptTemplate.from_template(
                "Please generate the daily digest for {date}."
            )
        ])
        
        chain = prompt | self.llm | self.output_parser
        full_digest = await chain.ainvoke({
            "date": date_str,
            "leadership_insights": leadership_insights,
            "strategy_insights": strategy_insights,
            "parenting_insights": parenting_insights
        })
        
        # Parse digest to extract structured components (simple extraction for now)
        # In production, you might want to use structured output parsing
        digest_data = {
            "date": date_str,
            "summary": self._extract_summary(full_digest),
            "leadership_insights": leadership_insights,
            "strategy_insights": strategy_insights,
            "parenting_insights": parenting_insights,
            "action_items": self._extract_action_items(full_digest),
            "full_digest": full_digest
        }
        
        # Store in database
        await self._save_digest(digest_data, agent_responses)
        
        return digest_data
    
    def _extract_summary(self, digest: str) -> str:
        """Extract executive summary from digest (simple implementation)."""
        # Simple extraction - in production, use structured output
        lines = digest.split("\n")
        summary_lines = []
        in_summary = False
        
        for line in lines:
            if "executive summary" in line.lower() or "summary" in line.lower():
                in_summary = True
                continue
            if in_summary and line.strip():
                if line.strip().startswith("#") or "insights" in line.lower():
                    break
                summary_lines.append(line.strip())
        
        return "\n".join(summary_lines) if summary_lines else digest[:500]
    
    def _extract_action_items(self, digest: str) -> str:
        """Extract action items from digest (simple implementation)."""
        # Simple extraction - in production, use structured output
        lines = digest.split("\n")
        action_lines = []
        in_actions = False
        
        for line in lines:
            if "action" in line.lower() and "item" in line.lower():
                in_actions = True
                continue
            if in_actions and line.strip():
                if line.strip().startswith("#") or "reflection" in line.lower():
                    break
                if line.strip().startswith("-") or line.strip().startswith("*") or line.strip()[0].isdigit():
                    action_lines.append(line.strip())
        
        return "\n".join(action_lines) if action_lines else "See full digest for action items."
    
    async def _save_digest(
        self,
        digest_data: Dict[str, Any],
        agent_responses: Dict[str, Any]
    ):
        """Save digest and agent responses to database."""
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            # Insert digest
            cursor = await db.execute("""
                INSERT OR REPLACE INTO daily_digests 
                (date, summary, leadership_insights, strategy_insights, parenting_insights, action_items, full_digest)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                digest_data["date"],
                digest_data["summary"],
                digest_data["leadership_insights"],
                digest_data["strategy_insights"],
                digest_data["parenting_insights"],
                digest_data["action_items"],
                digest_data["full_digest"]
            ))
            digest_id = cursor.lastrowid
            await db.commit()
            
            # Insert agent responses
            for agent_type, response_data in agent_responses.items():
                await db.execute("""
                    INSERT INTO agent_responses 
                    (digest_id, agent_type, input_content, response)
                    VALUES (?, ?, ?, ?)
                """, (
                    digest_id,
                    agent_type,
                    response_data.get("content_analyzed", ""),
                    response_data.get("response", "")
                ))
            await db.commit()
    
    async def get_digest_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Retrieve a digest by date."""
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("""
                SELECT * FROM daily_digests WHERE date = ?
            """, (date_str,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "date": row[1],
                        "summary": row[2],
                        "leadership_insights": row[3],
                        "strategy_insights": row[4],
                        "parenting_insights": row[5],
                        "action_items": row[6],
                        "full_digest": row[7],
                        "created_at": row[8]
                    }
                return None
