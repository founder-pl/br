"""
BR Documentation Generator - Configuration Module

Centralized configuration management with Pydantic settings.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class ValidationLevel(str, Enum):
    """Validation pipeline stages."""
    STRUCTURE = "structure"
    CONTENT = "content"
    LEGAL = "legal"
    FINANCIAL = "financial"


class PDFTemplate(str, Enum):
    """Available PDF templates."""
    PROFESSIONAL = "professional"
    MINIMAL = "minimal"
    DETAILED = "detailed"


class LogFormat(str, Enum):
    """Log output formats."""
    JSON = "json"
    CONSOLE = "console"


class LLMConfig(BaseSettings):
    """LLM provider configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore"
    )
    
    # OpenRouter settings
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="nvidia/nemotron-3-nano-30b-a3b:free",
        alias="OPENROUTER_MODEL"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL"
    )
    
    # Ollama settings (local)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="llama3.2:latest",
        alias="OLLAMA_MODEL"
    )
    
    # Default provider selection
    default_provider: LLMProvider = Field(
        default=LLMProvider.OPENROUTER,
        alias="LLM_DEFAULT_PROVIDER"
    )
    
    # Generation parameters
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4096, gt=0, alias="LLM_MAX_TOKENS")
    timeout: int = Field(default=120, gt=0, alias="LLM_TIMEOUT")
    max_retries: int = Field(default=3, ge=0, alias="LLM_MAX_RETRIES")
    retry_delay: int = Field(default=5, ge=0, alias="LLM_RETRY_DELAY")
    
    def get_litellm_params(self) -> dict:
        """Get parameters for LiteLLM call."""
        provider = self.default_provider
        
        if provider == LLMProvider.OPENROUTER:
            return {
                "model": f"openrouter/{self.openrouter_model}",
                "api_key": self.openrouter_api_key,
                "api_base": self.openrouter_base_url,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout": self.timeout,
            }
        elif provider == LLMProvider.OLLAMA:
            return {
                "model": f"ollama/{self.ollama_model}",
                "api_base": self.ollama_base_url,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout": self.timeout,
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")


class ValidationConfig(BaseSettings):
    """Validation pipeline configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        extra="ignore"
    )
    
    levels: list[ValidationLevel] = Field(
        default=[
            ValidationLevel.STRUCTURE,
            ValidationLevel.CONTENT,
            ValidationLevel.LEGAL,
            ValidationLevel.FINANCIAL,
        ]
    )
    max_iterations: int = Field(default=3, ge=1, le=10)
    min_quality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    verbose: bool = Field(default=True)
    
    @field_validator("levels", mode="before")
    @classmethod
    def parse_levels(cls, v):
        if isinstance(v, str):
            return [ValidationLevel(level.strip()) for level in v.split(",")]
        return v


class PDFConfig(BaseSettings):
    """PDF rendering configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="PDF_",
        extra="ignore"
    )
    
    template: PDFTemplate = Field(default=PDFTemplate.PROFESSIONAL)
    company_logo: Optional[Path] = Field(default=None)
    margin_top: int = Field(default=20, ge=0)
    margin_bottom: int = Field(default=20, ge=0)
    margin_left: int = Field(default=25, ge=0)
    margin_right: int = Field(default=25, ge=0)
    font_family: str = Field(default="DejaVu Sans")
    
    @field_validator("company_logo", mode="before")
    @classmethod
    def validate_logo_path(cls, v):
        if v and isinstance(v, str) and v.strip():
            path = Path(v)
            if path.exists():
                return path
        return None


class OutputConfig(BaseSettings):
    """Output configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore"
    )
    
    output_dir: Path = Field(default=Path("./output"), alias="OUTPUT_DIR")
    date_format: str = Field(default="%Y-%m-%d", alias="DATE_FORMAT")
    document_language: str = Field(default="pl", alias="DOCUMENT_LANGUAGE")
    
    @field_validator("output_dir", mode="before")
    @classmethod
    def ensure_output_dir(cls, v):
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path


class LogConfig(BaseSettings):
    """Logging configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore"
    )
    
    level: str = Field(default="INFO")
    format: LogFormat = Field(default=LogFormat.CONSOLE)
    dir: Path = Field(default=Path("./logs"))
    
    @field_validator("dir", mode="before")
    @classmethod
    def ensure_log_dir(cls, v):
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path


class CompanyDefaults(BaseSettings):
    """Default company information."""
    
    model_config = SettingsConfigDict(
        env_prefix="DEFAULT_",
        extra="ignore"
    )
    
    company_name: Optional[str] = Field(default=None)
    company_nip: Optional[str] = Field(default=None)
    company_regon: Optional[str] = Field(default=None)
    fiscal_year: int = Field(default=2025)


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    company: CompanyDefaults = Field(default_factory=CompanyDefaults)
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "AppConfig":
        """Load configuration from environment file."""
        if env_file and Path(env_file).exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
        
        return cls(
            llm=LLMConfig(),
            validation=ValidationConfig(),
            pdf=PDFConfig(),
            output=OutputConfig(),
            log=LogConfig(),
            company=CompanyDefaults(),
        )


def load_config(env_file: Optional[str] = None) -> AppConfig:
    """Load application configuration."""
    return AppConfig.from_env(env_file)


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
