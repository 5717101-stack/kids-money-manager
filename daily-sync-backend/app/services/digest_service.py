"""
Service for generating daily digests from agent analyses.
"""

import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
from app.core.database import get_mongo_db


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
        
        # Extract insights from each agent and truncate to avoid token limits
        # OpenAI has token limits per request, so we need to keep responses concise
        MAX_INSIGHT_LENGTH = 2000  # Characters per insight (roughly 500 tokens)
        
        leadership_full = agent_responses.get("leadership_coach", {}).get("response", "")
        strategy_full = agent_responses.get("strategy_consultant", {}).get("response", "")
        parenting_full = agent_responses.get("parenting_coach", {}).get("response", "")
        
        # Truncate if too long, keeping the most important parts (beginning and key sections)
        leadership_insights = self._truncate_insight(leadership_full, MAX_INSIGHT_LENGTH)
        strategy_insights = self._truncate_insight(strategy_full, MAX_INSIGHT_LENGTH)
        parenting_insights = self._truncate_insight(parenting_full, MAX_INSIGHT_LENGTH)
        
        # Create synthesis prompt (concise to save tokens)
        synthesis_prompt = """You are a synthesis expert. Combine insights from three specialized coaches into a concise, actionable daily digest.

## Input from Three Experts:

**Leadership Coach:**
{leadership_insights}

**Strategy Consultant:**
{strategy_insights}

**Parenting & Home Coach:**
{parenting_insights}

## Your Task:

Create a Daily Digest for {date} with:

1. **Executive Summary** (2-3 sentences)
2. **Key Insights** by category (Leadership, Strategy, Home & Parenting)
3. **Action Items** (3-5 prioritized, specific items)
4. **Reflection Questions** (2-3 questions)

Keep it concise, practical, and actionable. Write in a warm but professional tone."""

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
    
    def _truncate_insight(self, text: str, max_length: int) -> str:
        """
        Truncate insight text intelligently, keeping the most important parts.
        Tries to keep the beginning and any key sections.
        """
        if len(text) <= max_length:
            return text
        
        # If text is too long, take the first part and add a note
        # Try to cut at a sentence boundary
        truncated = text[:max_length - 100]  # Leave room for note
        
        # Find last sentence boundary
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        
        if cut_point > max_length * 0.7:  # If we found a good cut point
            truncated = truncated[:cut_point + 1]
        
        truncated += f"\n\n[Note: Response truncated from {len(text)} to {len(truncated)} characters to fit token limits. Full response available in agent_responses table.]"
        
        return truncated
    
    async def _save_digest(
        self,
        digest_data: Dict[str, Any],
        agent_responses: Dict[str, Any]
    ):
        """Save digest and agent responses to MongoDB."""
        db = await get_mongo_db()
        
        # Prepare digest document
        digest_doc = {
            "date": digest_data["date"],
            "summary": digest_data["summary"],
            "leadership_insights": digest_data["leadership_insights"],
            "strategy_insights": digest_data["strategy_insights"],
            "parenting_insights": digest_data["parenting_insights"],
            "action_items": digest_data["action_items"],
            "full_digest": digest_data["full_digest"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert or update digest (using date as unique identifier)
        result = await db.daily_digests.update_one(
            {"date": digest_data["date"]},
            {"$set": digest_doc},
            upsert=True
        )
        
        # Get the digest ID (either from update or insert)
        if result.upserted_id:
            digest_id = result.upserted_id
        else:
            digest = await db.daily_digests.find_one({"date": digest_data["date"]})
            digest_id = digest["_id"]
        
        # Delete old agent responses for this digest
        await db.agent_responses.delete_many({"digest_id": digest_id})
        
        # Insert agent responses
        agent_docs = []
        for agent_type, response_data in agent_responses.items():
            agent_docs.append({
                "digest_id": digest_id,
                "agent_type": agent_type,
                "input_content": response_data.get("content_analyzed", ""),
                "response": response_data.get("response", ""),
                "created_at": datetime.utcnow().isoformat()
            })
        
        if agent_docs:
            await db.agent_responses.insert_many(agent_docs)
    
    async def get_digest_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Retrieve a digest by date from MongoDB."""
        db = await get_mongo_db()
        digest = await db.daily_digests.find_one({"date": date_str})
        
        if digest:
            # Convert ObjectId to string and remove _id
            digest["id"] = str(digest.pop("_id"))
            return digest
        return None
