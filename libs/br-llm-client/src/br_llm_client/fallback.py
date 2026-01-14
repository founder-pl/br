"""
Fallback chain for LLM models.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import structlog

from .client import LLMClient, LLMResponse

logger = structlog.get_logger()


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    provider: str
    model: str
    priority: int = 0
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 1
    
    def to_client(self) -> LLMClient:
        """Create LLMClient from config"""
        return LLMClient(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )


class FallbackChain:
    """
    Chain of LLM models with automatic fallback.
    
    Tries models in priority order, falling back to next model on failure.
    
    Example:
        chain = FallbackChain([
            ModelConfig(provider="openai", model="gpt-4o", priority=1),
            ModelConfig(provider="anthropic", model="claude-3-sonnet", priority=2),
            ModelConfig(provider="ollama", model="llama3.2", priority=3),
        ])
        
        response = await chain.generate("Describe B+R project")
    """
    
    def __init__(
        self,
        models: Optional[List[ModelConfig]] = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 2000,
    ):
        """
        Initialize fallback chain.
        
        Args:
            models: List of model configurations (sorted by priority)
            default_temperature: Default temperature for generation
            default_max_tokens: Default max tokens for generation
        """
        self.models = sorted(models or [], key=lambda m: m.priority)
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._clients: Dict[str, LLMClient] = {}
    
    def add_model(self, config: ModelConfig):
        """Add model to chain"""
        self.models.append(config)
        self.models.sort(key=lambda m: m.priority)
    
    def _get_client(self, config: ModelConfig) -> LLMClient:
        """Get or create client for model"""
        key = f"{config.provider}:{config.model}"
        if key not in self._clients:
            self._clients[key] = config.to_client()
        return self._clients[key]
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using fallback chain.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Temperature (uses default if not provided)
            max_tokens: Max tokens (uses default if not provided)
            
        Returns:
            LLMResponse from first successful model
        """
        if not self.models:
            return LLMResponse(
                content="",
                model="none",
                provider="none",
                error="No models configured in fallback chain",
            )
        
        temperature = temperature or self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        last_error = None
        
        for config in self.models:
            for attempt in range(config.max_retries):
                client = self._get_client(config)
                
                logger.info(
                    "llm_attempt",
                    provider=config.provider,
                    model=config.model,
                    attempt=attempt + 1,
                    max_retries=config.max_retries,
                )
                
                response = await client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                if response.success:
                    logger.info(
                        "llm_fallback_success",
                        provider=config.provider,
                        model=config.model,
                    )
                    return response
                
                last_error = response.error
                logger.warning(
                    "llm_attempt_failed",
                    provider=config.provider,
                    model=config.model,
                    error=response.error,
                    attempt=attempt + 1,
                )
        
        # All models failed
        logger.error(
            "llm_fallback_exhausted",
            models_tried=len(self.models),
            last_error=last_error,
        )
        
        return LLMResponse(
            content="",
            model="fallback_exhausted",
            provider="none",
            error=f"All {len(self.models)} models failed. Last error: {last_error}",
        )


def create_default_chain() -> FallbackChain:
    """
    Create default fallback chain for B+R system.
    
    Priority:
    1. GPT-4o-mini (fast, cheap)
    2. Claude 3 Haiku (fast, cheap)
    3. Llama 3.2 local (free, offline)
    """
    return FallbackChain([
        ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            priority=1,
            timeout=30.0,
        ),
        ModelConfig(
            provider="anthropic",
            model="claude-3-haiku-20240307",
            priority=2,
            timeout=30.0,
        ),
        ModelConfig(
            provider="ollama",
            model="llama3.2",
            priority=3,
            timeout=120.0,
            max_retries=2,
        ),
    ])
