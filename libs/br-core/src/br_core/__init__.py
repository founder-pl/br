"""
BR Core - Core utilities and base classes for B+R documentation system.

This library provides:
- Base classes for data sources, templates, validators
- Common types and enums
- Shared utilities (formatting, validation helpers)
- Result types for consistent error handling
"""

from .types import (
    Result,
    Success,
    Failure,
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
)
from .enums import (
    DocumentCategory,
    TimeScope,
    BRCategory,
    ExpenseType,
)
from .formatters import (
    format_currency,
    format_date,
    format_nip,
    format_percent,
)
from .validators import (
    validate_nip,
    validate_date_range,
    validate_fiscal_year,
)

__version__ = "0.1.0"

__all__ = [
    # Types
    "Result",
    "Success", 
    "Failure",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    # Enums
    "DocumentCategory",
    "TimeScope",
    "BRCategory",
    "ExpenseType",
    # Formatters
    "format_currency",
    "format_date",
    "format_nip",
    "format_percent",
    # Validators
    "validate_nip",
    "validate_date_range",
    "validate_fiscal_year",
]
