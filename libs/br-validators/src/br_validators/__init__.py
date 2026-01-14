"""
BR Validators - Multi-level validation pipeline for B+R documentation.

Provides:
- StructureValidator: Document structure validation
- LegalValidator: Legal compliance validation (art. 18d CIT)
- FinancialValidator: Financial calculations validation
- LLMReviewValidator: LLM-based content review
- ValidationPipeline: Orchestration of all validators
"""

from .base import (
    BaseValidator,
    ValidationContext,
    ValidationStage,
)
from .structure import StructureValidator
from .legal import LegalValidator
from .financial import FinancialValidator
from .pipeline import ValidationPipeline, create_default_pipeline

__version__ = "0.1.0"

__all__ = [
    "BaseValidator",
    "ValidationContext",
    "ValidationStage",
    "StructureValidator",
    "LegalValidator",
    "FinancialValidator",
    "ValidationPipeline",
    "create_default_pipeline",
]
