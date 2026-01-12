"""
OCR Configuration - Engines, strategies and field extraction mapping
"""
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel

class OCREngine(str, Enum):
    PADDLEOCR = "paddleocr"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    DOCTR = "doctr"
    SURYA = "surya"
    TROCR = "trocr"

class ExtractionStrategy(str, Enum):
    SINGLE = "single"           # Use one engine
    FALLBACK = "fallback"       # Try engines in order until success
    ENSEMBLE = "ensemble"       # Use multiple engines and merge results
    FIELD_SPECIFIC = "field_specific"  # Use best engine per field type

class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    PROTOCOL = "protocol"
    REPORT = "report"
    BANK_STATEMENT = "bank_statement"
    ID_DOCUMENT = "id_document"
    MEDICAL = "medical"
    LEGAL = "legal"
    TECHNICAL = "technical"
    OTHER = "other"

# Engine capabilities and strengths
ENGINE_CAPABILITIES = {
    OCREngine.PADDLEOCR: {
        "name": "PaddleOCR",
        "description": "Szybki i dokładny, dobry dla dokumentów polskich",
        "languages": ["pl", "en", "de", "fr", "zh"],
        "strengths": ["tables", "handwriting", "multilingual", "speed"],
        "weaknesses": ["very_small_text"],
        "gpu_required": False,
        "accuracy_score": 0.92,
        "speed_score": 0.95,
        "best_for": ["invoice", "receipt", "bank_statement"]
    },
    OCREngine.TESSERACT: {
        "name": "Tesseract",
        "description": "Klasyczny OCR, stabilny i dobrze przetestowany",
        "languages": ["pl", "en", "de", "fr", "es", "it"],
        "strengths": ["printed_text", "stability", "no_gpu"],
        "weaknesses": ["handwriting", "complex_layouts"],
        "gpu_required": False,
        "accuracy_score": 0.85,
        "speed_score": 0.80,
        "best_for": ["contract", "legal", "report"]
    },
    OCREngine.EASYOCR: {
        "name": "EasyOCR",
        "description": "Prosty w użyciu, dobry dla wielu języków",
        "languages": ["pl", "en", "de", "fr", "ru", "uk"],
        "strengths": ["multilingual", "scene_text", "ease_of_use"],
        "weaknesses": ["speed", "large_documents"],
        "gpu_required": True,
        "accuracy_score": 0.88,
        "speed_score": 0.70,
        "best_for": ["receipt", "id_document"]
    },
    OCREngine.DOCTR: {
        "name": "DocTR",
        "description": "Nowoczesny OCR oparty na transformerach",
        "languages": ["pl", "en", "de", "fr"],
        "strengths": ["accuracy", "layout_analysis", "modern"],
        "weaknesses": ["speed", "memory_usage"],
        "gpu_required": True,
        "accuracy_score": 0.94,
        "speed_score": 0.65,
        "best_for": ["invoice", "contract", "technical"]
    },
    OCREngine.SURYA: {
        "name": "Surya",
        "description": "Wielojęzyczny OCR z detekcją layoutu",
        "languages": ["pl", "en", "de", "fr", "es", "zh", "ja"],
        "strengths": ["layout_detection", "multilingual", "accuracy"],
        "weaknesses": ["speed", "setup_complexity"],
        "gpu_required": True,
        "accuracy_score": 0.93,
        "speed_score": 0.60,
        "best_for": ["technical", "report", "medical"]
    },
    OCREngine.TROCR: {
        "name": "TrOCR",
        "description": "Transformer OCR od Microsoft, świetny do rękopisu",
        "languages": ["en", "pl"],
        "strengths": ["handwriting", "accuracy", "transformer_based"],
        "weaknesses": ["speed", "limited_languages"],
        "gpu_required": True,
        "accuracy_score": 0.91,
        "speed_score": 0.55,
        "best_for": ["handwriting", "medical", "protocol"]
    }
}

# Field types and best engines for extraction
FIELD_ENGINE_MAPPING = {
    # Financial fields
    "nip": [OCREngine.PADDLEOCR, OCREngine.DOCTR],
    "invoice_number": [OCREngine.PADDLEOCR, OCREngine.TESSERACT],
    "total_gross": [OCREngine.PADDLEOCR, OCREngine.DOCTR],
    "total_net": [OCREngine.PADDLEOCR, OCREngine.DOCTR],
    "vat_amount": [OCREngine.PADDLEOCR, OCREngine.DOCTR],
    "bank_account": [OCREngine.PADDLEOCR, OCREngine.TESSERACT],
    
    # Date fields
    "issue_date": [OCREngine.PADDLEOCR, OCREngine.TESSERACT],
    "due_date": [OCREngine.PADDLEOCR, OCREngine.TESSERACT],
    "contract_date": [OCREngine.TESSERACT, OCREngine.PADDLEOCR],
    
    # Text fields
    "company_name": [OCREngine.DOCTR, OCREngine.PADDLEOCR],
    "address": [OCREngine.DOCTR, OCREngine.PADDLEOCR],
    "description": [OCREngine.DOCTR, OCREngine.SURYA],
    
    # Handwritten fields
    "signature": [OCREngine.TROCR, OCREngine.EASYOCR],
    "handwritten_notes": [OCREngine.TROCR, OCREngine.EASYOCR],
    
    # Table data
    "line_items": [OCREngine.PADDLEOCR, OCREngine.DOCTR],
    "table_data": [OCREngine.PADDLEOCR, OCREngine.SURYA]
}

# Document type to recommended engines
DOCUMENT_ENGINE_PRIORITY = {
    DocumentType.INVOICE: [OCREngine.PADDLEOCR, OCREngine.DOCTR, OCREngine.TESSERACT],
    DocumentType.RECEIPT: [OCREngine.PADDLEOCR, OCREngine.EASYOCR],
    DocumentType.CONTRACT: [OCREngine.TESSERACT, OCREngine.DOCTR, OCREngine.PADDLEOCR],
    DocumentType.PROTOCOL: [OCREngine.TROCR, OCREngine.PADDLEOCR],
    DocumentType.REPORT: [OCREngine.SURYA, OCREngine.DOCTR, OCREngine.PADDLEOCR],
    DocumentType.BANK_STATEMENT: [OCREngine.PADDLEOCR, OCREngine.TESSERACT],
    DocumentType.ID_DOCUMENT: [OCREngine.EASYOCR, OCREngine.PADDLEOCR],
    DocumentType.MEDICAL: [OCREngine.TROCR, OCREngine.SURYA, OCREngine.DOCTR],
    DocumentType.LEGAL: [OCREngine.TESSERACT, OCREngine.DOCTR],
    DocumentType.TECHNICAL: [OCREngine.SURYA, OCREngine.DOCTR, OCREngine.PADDLEOCR],
    DocumentType.OTHER: [OCREngine.PADDLEOCR, OCREngine.TESSERACT]
}

# Minimum confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.90,
    "medium": 0.75,
    "low": 0.50,
    "accept_any": 0.0
}

# Required fields per document type
REQUIRED_FIELDS = {
    DocumentType.INVOICE: ["invoice_number", "total_gross", "nip_seller"],
    DocumentType.RECEIPT: ["total", "date"],
    DocumentType.CONTRACT: ["contract_date", "parties"],
    DocumentType.BANK_STATEMENT: ["account_number", "balance"],
    DocumentType.ID_DOCUMENT: ["name", "id_number"],
}


class OCRConfig(BaseModel):
    """Configuration for OCR processing"""
    primary_engine: OCREngine = OCREngine.PADDLEOCR
    fallback_engines: List[OCREngine] = [OCREngine.TESSERACT, OCREngine.DOCTR]
    strategy: ExtractionStrategy = ExtractionStrategy.FALLBACK
    min_confidence: float = 0.75
    use_field_specific: bool = True
    max_retries: int = 2
    timeout_seconds: int = 300
    language: str = "pol"
    use_gpu: bool = True


class LLMConfig(BaseModel):
    """Configuration for LLM processing"""
    provider: str = "ollama"
    model: str = "llama3.2"
    api_base: str = "http://host.docker.internal:11434"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    use_for_extraction: bool = True
    use_for_classification: bool = True
    use_for_validation: bool = True


# Default configuration
DEFAULT_OCR_CONFIG = OCRConfig()
DEFAULT_LLM_CONFIG = LLMConfig()


def get_best_engine_for_field(field_name: str) -> OCREngine:
    """Get the best OCR engine for a specific field type"""
    engines = FIELD_ENGINE_MAPPING.get(field_name, [OCREngine.PADDLEOCR])
    return engines[0] if engines else OCREngine.PADDLEOCR


def get_engines_for_document_type(doc_type: str) -> List[OCREngine]:
    """Get ordered list of recommended engines for a document type"""
    try:
        dtype = DocumentType(doc_type)
        return DOCUMENT_ENGINE_PRIORITY.get(dtype, [OCREngine.PADDLEOCR])
    except ValueError:
        return [OCREngine.PADDLEOCR, OCREngine.TESSERACT]


def get_required_fields(doc_type: str) -> List[str]:
    """Get list of required fields for a document type"""
    try:
        dtype = DocumentType(doc_type)
        return REQUIRED_FIELDS.get(dtype, [])
    except ValueError:
        return []


def evaluate_extraction_completeness(extracted_data: Dict, doc_type: str) -> float:
    """Calculate how complete the extraction is (0.0 to 1.0)"""
    required = get_required_fields(doc_type)
    if not required:
        return 1.0
    
    found = sum(1 for field in required if field in extracted_data and extracted_data[field])
    return found / len(required)
