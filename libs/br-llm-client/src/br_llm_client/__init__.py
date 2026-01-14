"""
BR LLM Client - LLM client with fallback support for B+R documentation.

Provides:
- LLMClient: Unified interface for multiple LLM providers
- FallbackChain: Automatic fallback between models
- PromptBuilder: B+R-specific prompt templates
"""

from .client import LLMClient, LLMResponse
from .fallback import FallbackChain, ModelConfig
from .prompts import PromptBuilder, BR_PROMPTS

__version__ = "0.1.0"

__all__ = [
    "LLMClient",
    "LLMResponse",
    "FallbackChain",
    "ModelConfig",
    "PromptBuilder",
    "BR_PROMPTS",
]
