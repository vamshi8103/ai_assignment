"""
LLM Engine — abstract interface + HuggingFace Inference API implementation.
Supports swapping to local models without code changes.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class BaseLLMEngine(ABC):
    """Abstract base for LLM backends."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate a response from the LLM."""
        pass



class HuggingFaceEngine(BaseLLMEngine):
    """
    Uses HuggingFace Inference API via the official SDK.
    Handling URL routing and authentication automatically.
    """

    def __init__(self):
        from huggingface_hub import AsyncInferenceClient
        
        self.client = AsyncInferenceClient(
            model=settings.MODEL_NAME,
            token=settings.HF_API_TOKEN or None,
        )

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Call HuggingFace Inference API with retry logic."""
        max_tok = max_tokens or settings.MAX_NEW_TOKENS
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                # Use chat completion for Instruct models
                messages = [{"role": "user", "content": prompt}]
                response = await self.client.chat_completion(
                    messages,
                    max_tokens=max_tok,
                    temperature=settings.TEMPERATURE,
                    seed=42,
                )
                return response.choices[0].message.content

            except Exception as e:
                # Handle SDK specific errors or generic exceptions
                import huggingface_hub
                error_str = str(e)
                
                # Check for rate limits or loading errors in the exception message
                if "429" in error_str:
                    logger.warning(f"Rate limited, waiting {settings.RETRY_DELAY}s")
                    await asyncio.sleep(settings.RETRY_DELAY * (attempt + 1))
                    continue
                    
                if "503" in error_str or "loading" in error_str.lower():
                    logger.warning(f"Model loading, waiting 20s (attempt {attempt+1})")
                    await asyncio.sleep(20)
                    continue

                logger.error(f"HF API error: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    await asyncio.sleep(settings.RETRY_DELAY)
                    continue
                raise RuntimeError(f"HF API failed: {e}")

        raise RuntimeError(f"Failed after {settings.MAX_RETRIES} retries")



def get_engine() -> BaseLLMEngine:
    """Factory function to get the appropriate LLM engine."""
    # Enforce HuggingFace engine for production
    if not settings.HF_API_TOKEN:
        logger.warning("HF_API_TOKEN not set. API calls will fail.")
    
    return HuggingFaceEngine()
