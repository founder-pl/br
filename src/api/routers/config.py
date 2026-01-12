"""
Configuration Router - Manage OCR engines, LLM settings and extraction strategies
"""
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..ocr_config import (
    OCREngine, ExtractionStrategy, DocumentType,
    ENGINE_CAPABILITIES, FIELD_ENGINE_MAPPING, DOCUMENT_ENGINE_PRIORITY,
    OCRConfig, LLMConfig, DEFAULT_OCR_CONFIG, DEFAULT_LLM_CONFIG,
    get_engines_for_document_type, get_required_fields
)

logger = structlog.get_logger()
router = APIRouter()

# In-memory config (would be stored in DB in production)
_current_ocr_config = DEFAULT_OCR_CONFIG.model_copy()
_current_llm_config = DEFAULT_LLM_CONFIG.model_copy()


class OCREngineInfo(BaseModel):
    id: str
    name: str
    description: str
    languages: List[str]
    strengths: List[str]
    weaknesses: List[str]
    gpu_required: bool
    accuracy_score: float
    speed_score: float
    best_for: List[str]


class DocumentTypeInfo(BaseModel):
    id: str
    name: str
    recommended_engines: List[str]
    required_fields: List[str]


@router.get("/ocr/engines")
async def list_ocr_engines():
    """List all available OCR engines with their capabilities"""
    engines = []
    for engine_id, caps in ENGINE_CAPABILITIES.items():
        engines.append(OCREngineInfo(
            id=engine_id.value,
            name=caps["name"],
            description=caps["description"],
            languages=caps["languages"],
            strengths=caps["strengths"],
            weaknesses=caps["weaknesses"],
            gpu_required=caps["gpu_required"],
            accuracy_score=caps["accuracy_score"],
            speed_score=caps["speed_score"],
            best_for=caps["best_for"]
        ))
    return {"engines": engines}


@router.get("/ocr/document-types")
async def list_document_types():
    """List all document types with their configurations"""
    types = []
    for doc_type in DocumentType:
        engines = get_engines_for_document_type(doc_type.value)
        required = get_required_fields(doc_type.value)
        
        names = {
            "invoice": "Faktura VAT",
            "receipt": "Paragon",
            "contract": "Umowa",
            "protocol": "Protokół",
            "report": "Raport",
            "bank_statement": "Wyciąg bankowy",
            "id_document": "Dokument tożsamości",
            "medical": "Dokument medyczny",
            "legal": "Dokument prawny",
            "technical": "Dokumentacja techniczna",
            "other": "Inny"
        }
        
        types.append(DocumentTypeInfo(
            id=doc_type.value,
            name=names.get(doc_type.value, doc_type.value),
            recommended_engines=[e.value for e in engines],
            required_fields=required
        ))
    return {"document_types": types}


@router.get("/ocr/field-mappings")
async def get_field_mappings():
    """Get field to engine mappings"""
    mappings = {}
    for field, engines in FIELD_ENGINE_MAPPING.items():
        mappings[field] = [e.value for e in engines]
    return {"field_mappings": mappings}


@router.get("/ocr/config")
async def get_ocr_config():
    """Get current OCR configuration"""
    return {
        "primary_engine": _current_ocr_config.primary_engine.value,
        "fallback_engines": [e.value for e in _current_ocr_config.fallback_engines],
        "strategy": _current_ocr_config.strategy.value,
        "min_confidence": _current_ocr_config.min_confidence,
        "use_field_specific": _current_ocr_config.use_field_specific,
        "max_retries": _current_ocr_config.max_retries,
        "timeout_seconds": _current_ocr_config.timeout_seconds,
        "language": _current_ocr_config.language,
        "use_gpu": _current_ocr_config.use_gpu
    }


@router.put("/ocr/config")
async def update_ocr_config(
    primary_engine: Optional[str] = None,
    fallback_engines: Optional[List[str]] = None,
    strategy: Optional[str] = None,
    min_confidence: Optional[float] = None,
    use_field_specific: Optional[bool] = None,
    max_retries: Optional[int] = None,
    language: Optional[str] = None,
    use_gpu: Optional[bool] = None
):
    """Update OCR configuration"""
    global _current_ocr_config
    
    if primary_engine:
        _current_ocr_config.primary_engine = OCREngine(primary_engine)
    if fallback_engines:
        _current_ocr_config.fallback_engines = [OCREngine(e) for e in fallback_engines]
    if strategy:
        _current_ocr_config.strategy = ExtractionStrategy(strategy)
    if min_confidence is not None:
        _current_ocr_config.min_confidence = min_confidence
    if use_field_specific is not None:
        _current_ocr_config.use_field_specific = use_field_specific
    if max_retries is not None:
        _current_ocr_config.max_retries = max_retries
    if language:
        _current_ocr_config.language = language
    if use_gpu is not None:
        _current_ocr_config.use_gpu = use_gpu
    
    logger.info("OCR config updated", config=_current_ocr_config.model_dump())
    return {"status": "updated", "config": await get_ocr_config()}


@router.get("/llm/config")
async def get_llm_config():
    """Get current LLM configuration"""
    return {
        "provider": _current_llm_config.provider,
        "model": _current_llm_config.model,
        "api_base": _current_llm_config.api_base,
        "temperature": _current_llm_config.temperature,
        "max_tokens": _current_llm_config.max_tokens,
        "use_for_extraction": _current_llm_config.use_for_extraction,
        "use_for_classification": _current_llm_config.use_for_classification,
        "use_for_validation": _current_llm_config.use_for_validation
    }


@router.put("/llm/config")
async def update_llm_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_for_extraction: Optional[bool] = None,
    use_for_classification: Optional[bool] = None,
    use_for_validation: Optional[bool] = None
):
    """Update LLM configuration"""
    global _current_llm_config
    
    if provider:
        _current_llm_config.provider = provider
    if model:
        _current_llm_config.model = model
    if api_base:
        _current_llm_config.api_base = api_base
    if api_key:
        _current_llm_config.api_key = api_key
    if temperature is not None:
        _current_llm_config.temperature = temperature
    if max_tokens is not None:
        _current_llm_config.max_tokens = max_tokens
    if use_for_extraction is not None:
        _current_llm_config.use_for_extraction = use_for_extraction
    if use_for_classification is not None:
        _current_llm_config.use_for_classification = use_for_classification
    if use_for_validation is not None:
        _current_llm_config.use_for_validation = use_for_validation
    
    logger.info("LLM config updated", provider=_current_llm_config.provider, model=_current_llm_config.model)
    return {"status": "updated", "config": await get_llm_config()}


@router.get("/llm/models")
async def list_available_models():
    """List available LLM models"""
    models = [
        {"id": "llama3.2", "name": "Llama 3.2", "provider": "ollama", "size": "3B", "best_for": ["general", "extraction"]},
        {"id": "llama3.1:8b", "name": "Llama 3.1 8B", "provider": "ollama", "size": "8B", "best_for": ["complex", "reasoning"]},
        {"id": "mistral", "name": "Mistral 7B", "provider": "ollama", "size": "7B", "best_for": ["general", "fast"]},
        {"id": "gemma2:9b", "name": "Gemma 2 9B", "provider": "ollama", "size": "9B", "best_for": ["multilingual", "polish"]},
        {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "provider": "ollama", "size": "7B", "best_for": ["extraction", "structured"]},
        {"id": "phi3", "name": "Phi-3", "provider": "ollama", "size": "3.8B", "best_for": ["fast", "efficient"]},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "size": "API", "best_for": ["accuracy", "complex"]},
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "size": "API", "best_for": ["best_quality"]},
        {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "size": "API", "best_for": ["reasoning", "polish"]}
    ]
    return {"models": models}


@router.get("/strategies")
async def list_strategies():
    """List available extraction strategies"""
    strategies = [
        {
            "id": "single",
            "name": "Pojedynczy silnik",
            "description": "Używa jednego silnika OCR"
        },
        {
            "id": "fallback",
            "name": "Fallback",
            "description": "Próbuje kolejnych silników jeśli poprzedni nie osiągnie wymaganej pewności"
        },
        {
            "id": "ensemble",
            "name": "Ensemble",
            "description": "Używa wielu silników i łączy wyniki"
        },
        {
            "id": "field_specific",
            "name": "Specyficzny dla pola",
            "description": "Używa najlepszego silnika dla każdego typu pola"
        }
    ]
    return {"strategies": strategies}


@router.post("/test-ocr")
async def test_ocr_engine(engine: str, text_sample: str = "Faktura VAT nr 123/2025"):
    """Test OCR engine availability"""
    # This would actually test the engine
    available_engines = ["paddleocr", "tesseract"]  # Currently installed
    
    is_available = engine in available_engines
    
    return {
        "engine": engine,
        "available": is_available,
        "message": f"Silnik {engine} jest {'dostępny' if is_available else 'niedostępny'}"
    }


@router.post("/test-llm")
async def test_llm_connection():
    """Test LLM connection"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{_current_llm_config.api_base}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "status": "connected",
                    "provider": _current_llm_config.provider,
                    "available_models": [m.get("name") for m in models]
                }
    except Exception as e:
        pass
    
    return {
        "status": "disconnected",
        "provider": _current_llm_config.provider,
        "error": "Nie można połączyć się z LLM"
    }
