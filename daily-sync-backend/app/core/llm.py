"""
LLM provider setup and utilities for OpenAI and Anthropic.
"""

from typing import Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from app.core.config import settings


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7
) -> BaseChatModel:
    """
    Get an LLM instance based on provider and model.
    
    Args:
        provider: "openai" or "anthropic". Defaults to settings.default_llm_provider
        model: Model name. Defaults to settings.default_model
        temperature: Sampling temperature (0.0 to 2.0)
    
    Returns:
        BaseChatModel instance
    """
    provider = provider or settings.default_llm_provider
    model = model or settings.default_model
    
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not set. Set OPENAI_API_KEY environment variable.")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.openai_api_key
        )
    
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not set. Set ANTHROPIC_API_KEY environment variable.")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=settings.anthropic_api_key
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'anthropic'.")


def get_embedding_model():
    """Get embedding model for vector store (currently OpenAI only)."""
    from langchain_openai import OpenAIEmbeddings
    
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key required for embeddings. Set OPENAI_API_KEY environment variable.")
    
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key
    )
