"""
BR Documentation Generator - LLM Client

LiteLLM-based client for interacting with various LLM providers.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import structlog
from litellm import acompletion, completion
from pydantic import BaseModel

from .config import LLMConfig, LLMProvider, get_config

logger = structlog.get_logger(__name__)


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMClient:
    """
    LiteLLM-based client for multiple LLM providers.
    
    Supports OpenRouter, Ollama (local), and other providers through LiteLLM.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client with configuration."""
        self.config = config or get_config().llm
        self._initialized = False
        
    async def _ensure_connection(self) -> None:
        """Verify connection to LLM provider."""
        if self._initialized:
            return
            
        provider = self.config.default_provider
        logger.info(
            "Initializing LLM connection",
            provider=provider.value,
            model=self._get_model_name()
        )
        
        # Test connection with simple prompt
        try:
            response = await self._call_llm(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            self._initialized = True
            logger.info("LLM connection established", provider=provider.value)
        except Exception as e:
            logger.error("Failed to connect to LLM", error=str(e))
            raise ConnectionError(f"Cannot connect to LLM provider: {e}")
    
    def _get_model_name(self) -> str:
        """Get model name based on provider."""
        provider = self.config.default_provider
        
        if provider == LLMProvider.OPENROUTER:
            return f"openrouter/{self.config.openrouter_model}"
        elif provider == LLMProvider.OLLAMA:
            return f"ollama/{self.config.ollama_model}"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _get_api_params(self) -> dict[str, Any]:
        """Get API parameters for LiteLLM."""
        provider = self.config.default_provider
        
        params = {
            "model": self._get_model_name(),
            "temperature": self.config.temperature,
            "timeout": self.config.timeout,
        }
        
        if provider == LLMProvider.OPENROUTER:
            params["api_key"] = self.config.openrouter_api_key
            params["api_base"] = self.config.openrouter_base_url
        elif provider == LLMProvider.OLLAMA:
            params["api_base"] = self.config.ollama_base_url
            
        return params
    
    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """Make async call to LLM."""
        params = self._get_api_params()
        params["messages"] = messages
        params["max_tokens"] = max_tokens or self.config.max_tokens
        
        if temperature is not None:
            params["temperature"] = temperature
            
        params.update(kwargs)
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await acompletion(**params)
                
                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    finish_reason=response.choices[0].finish_reason,
                    raw_response=response.model_dump() if hasattr(response, "model_dump") else None
                )
                
            except Exception as e:
                logger.warning(
                    "LLM call failed",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    error=str(e)
                )
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Generation temperature
            
        Returns:
            Generated text content
        """
        await self._ensure_connection()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self._call_llm(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.content
    
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_schema: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            output_schema: Expected JSON schema (for prompt guidance)
            
        Returns:
            Parsed JSON response
        """
        schema_instruction = ""
        if output_schema:
            schema_instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(output_schema, indent=2)}"
        
        full_prompt = f"{prompt}{schema_instruction}\n\nRespond ONLY with valid JSON, no other text."
        
        response = await self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.1  # Lower temperature for structured output
        )
        
        # Extract JSON from response
        content = response.strip()
        
        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response", error=str(e), content=content[:500])
            raise ValueError(f"LLM did not return valid JSON: {e}")
    
    async def validate_content(
        self,
        content: str,
        validation_criteria: list[str],
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Validate content against criteria using LLM.
        
        Args:
            content: Content to validate
            validation_criteria: List of validation criteria
            context: Additional context for validation
            
        Returns:
            Validation result with score and issues
        """
        criteria_text = "\n".join(f"- {c}" for c in validation_criteria)
        context_text = f"\n\nContext: {context}" if context else ""
        
        system_prompt = """You are a documentation quality validator. 
Analyze the provided content against validation criteria and return a structured assessment.
Be thorough but fair in your evaluation."""
        
        prompt = f"""Validate the following content against these criteria:

{criteria_text}
{context_text}

CONTENT TO VALIDATE:
---
{content}
---

Return a JSON object with:
{{
  "score": 0.0-1.0 (overall quality score),
  "passed": true/false,
  "issues": [
    {{
      "criterion": "which criterion failed",
      "severity": "critical|error|warning|info",
      "location": "where in document",
      "message": "description of issue",
      "suggestion": "how to fix"
    }}
  ],
  "strengths": ["list of positive aspects"],
  "summary": "brief assessment"
}}"""

        return await self.generate_structured(prompt, system_prompt)
    
    async def improve_content(
        self,
        content: str,
        issues: list[dict[str, str]],
        instructions: Optional[str] = None,
    ) -> str:
        """
        Improve content based on identified issues.
        
        Args:
            content: Original content
            issues: List of issues to address
            instructions: Additional improvement instructions
            
        Returns:
            Improved content
        """
        issues_text = "\n".join(
            f"- [{i.get('severity', 'info')}] {i.get('message', '')} "
            f"(Location: {i.get('location', 'unknown')}, Suggestion: {i.get('suggestion', 'N/A')})"
            for i in issues
        )
        
        extra_instructions = f"\n\nAdditional instructions: {instructions}" if instructions else ""
        
        system_prompt = """You are a professional documentation editor.
Improve the provided content by addressing the identified issues while maintaining the original structure and intent.
Return ONLY the improved content, no explanations."""

        prompt = f"""Improve the following content by addressing these issues:

ISSUES TO ADDRESS:
{issues_text}
{extra_instructions}

ORIGINAL CONTENT:
---
{content}
---

Return the improved content:"""

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )


# Singleton client instance
_client: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """Get or create LLM client instance."""
    global _client
    if _client is None or config is not None:
        _client = LLMClient(config)
    return _client
