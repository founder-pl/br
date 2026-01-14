"""
LLM Client with unified interface.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    
    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Ollama (local models)
    - OpenRouter (multiple models)
    - LiteLLM proxy
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (openai, anthropic, ollama, openrouter, litellm)
            model: Model name
            api_key: API key (or from environment)
            base_url: Custom base URL for API
            timeout: Request timeout in seconds
        """
        self.provider = provider.lower()
        self.model = model
        self.timeout = timeout
        
        # Get API key from environment if not provided
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url or self._get_base_url()
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment"""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "litellm": "LITELLM_MASTER_KEY",
        }
        env_var = key_map.get(self.provider)
        return os.getenv(env_var) if env_var else None
    
    def _get_base_url(self) -> str:
        """Get base URL for provider"""
        url_map = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "ollama": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
            "openrouter": "https://openrouter.ai/api/v1",
            "litellm": os.getenv("LITELLM_API_BASE", "http://localhost:4000"),
        }
        return url_map.get(self.provider, "http://localhost:11434")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        start_time = datetime.now()
        
        try:
            if self.provider == "ollama":
                response = await self._generate_ollama(
                    prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            elif self.provider == "anthropic":
                response = await self._generate_anthropic(
                    prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            else:
                # OpenAI-compatible API (OpenAI, OpenRouter, LiteLLM)
                response = await self._generate_openai(
                    prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            response.latency_ms = latency
            
            logger.info(
                "llm_generation_complete",
                provider=self.provider,
                model=self.model,
                latency_ms=latency,
                tokens=response.tokens_used,
            )
            
            return response
            
        except Exception as e:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.error(
                "llm_generation_error",
                provider=self.provider,
                model=self.model,
                error=str(e),
            )
            
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider,
                latency_ms=latency,
                error=str(e),
            )
    
    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI-compatible API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # OpenRouter specific headers
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://br-system.local"
            headers["X-Title"] = "BR Documentation System"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            tokens_used=tokens,
            metadata=data.get("usage", {}),
        )
    
    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Generate using Anthropic API"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["content"][0]["text"]
        tokens = data.get("usage", {}).get("input_tokens", 0) + \
                 data.get("usage", {}).get("output_tokens", 0)
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            tokens_used=tokens,
            metadata=data.get("usage", {}),
        )
    
    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Generate using Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("response", ""),
            model=self.model,
            provider=self.provider,
            tokens_used=data.get("eval_count", 0),
            metadata={
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
            },
        )
