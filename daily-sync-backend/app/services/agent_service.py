"""
Service for running AI agents with different personas.
"""

from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
from app.agents.prompts import (
    get_leadership_coach_prompt,
    get_strategy_consultant_prompt,
    get_parenting_coach_prompt
)


class AgentService:
    """Service for running specialized AI agents."""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.llm = get_llm(provider=provider, model=model)
        self.output_parser = StrOutputParser()
    
    async def analyze_with_leadership_coach(
        self,
        content: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze content using the Leadership Coach persona.
        
        Args:
            content: The content to analyze
            context: Optional context from previous days (RAG)
        
        Returns:
            Dict with analysis results
        """
        system_prompt = get_leadership_coach_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(
                "Please analyze the following daily input:\n\n{content}\n\n"
                "{context}\n\n"
                "Provide your analysis following the format specified in your instructions."
            )
        ])
        
        chain = prompt | self.llm | self.output_parser
        response = await chain.ainvoke({
            "content": content,
            "context": context or "No previous context available."
        })
        
        return {
            "agent_type": "leadership_coach",
            "response": response,
            "content_analyzed": content[:200] + "..." if len(content) > 200 else content
        }
    
    async def analyze_with_strategy_consultant(
        self,
        content: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze content using the Strategy Consultant persona.
        
        Args:
            content: The content to analyze
            context: Optional context from previous days (RAG)
        
        Returns:
            Dict with analysis results
        """
        system_prompt = get_strategy_consultant_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(
                "Please analyze the following daily input:\n\n{content}\n\n"
                "{context}\n\n"
                "Provide your strategic analysis following the format specified in your instructions."
            )
        ])
        
        chain = prompt | self.llm | self.output_parser
        response = await chain.ainvoke({
            "content": content,
            "context": context or "No previous context available."
        })
        
        return {
            "agent_type": "strategy_consultant",
            "response": response,
            "content_analyzed": content[:200] + "..." if len(content) > 200 else content
        }
    
    async def analyze_with_parenting_coach(
        self,
        content: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze content using the Parenting Coach persona.
        
        Args:
            content: The content to analyze
            context: Optional context from previous days (RAG)
        
        Returns:
            Dict with analysis results
        """
        system_prompt = get_parenting_coach_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(
                "Please analyze the following daily input:\n\n{content}\n\n"
                "{context}\n\n"
                "Provide your parenting and home life analysis following the format specified in your instructions."
            )
        ])
        
        chain = prompt | self.llm | self.output_parser
        response = await chain.ainvoke({
            "content": content,
            "context": context or "No previous context available."
        })
        
        return {
            "agent_type": "parenting_coach",
            "response": response,
            "content_analyzed": content[:200] + "..." if len(content) > 200 else content
        }
    
    async def analyze_with_all_agents(
        self,
        content: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Run all three agents in parallel on the same content.
        
        Args:
            content: The content to analyze
            context: Optional context from previous days (RAG)
        
        Returns:
            Dict with all agent responses
        """
        import asyncio
        
        results = await asyncio.gather(
            self.analyze_with_leadership_coach(content, context),
            self.analyze_with_strategy_consultant(content, context),
            self.analyze_with_parenting_coach(content, context)
        )
        
        return {
            "leadership_coach": results[0],
            "strategy_consultant": results[1],
            "parenting_coach": results[2]
        }
