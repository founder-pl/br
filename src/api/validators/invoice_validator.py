"""
Invoice Validator - Validates invoice numbers according to Polish standards.

Detects generic/placeholder invoice numbers and normalizes valid ones.
"""

import re
from typing import Optional, List
from pydantic import BaseModel


class InvoiceValidationResult(BaseModel):
    """Result of invoice number validation."""
    is_valid: bool
    errors: List[str] = []
    normalized_number: Optional[str] = None
    warnings: List[str] = []


class InvoiceValidator:
    """Walidator numerów faktur zgodny z polskimi standardami."""
    
    GENERIC_PATTERNS = [
        r"^faktury?$",
        r"^faktura$",
        r"^sprzedaz[y]?$",
        r"^brak$",
        r"^none$",
        r"^n/?a$",
        r"^-$",
        r"^\d{1,3}$",  # Zbyt krótkie numery (1-3 cyfry)
        r"^0+$",  # Same zera
    ]
    
    VALID_PATTERNS = [
        r"^FV[/-]?\d{1,4}[/-]\d{2,4}[/-]?\d{4}$",  # FV/123/01/2025
        r"^F[/-]?\d{1,4}[/-]\d{2,4}[/-]?\d{4}$",   # F/123/01/2025
        r"^[A-Z]{2,10}[-_]?\d{4,}$",               # SVFOB8UM-0001
        r"^\d{1,4}/\d{1,2}/\d{4}$",                # 269/11/2025
        r"^\d{4,}[/-]\d{2,4}[/-]\d{4}$",           # 1234/01/2025
        r"^[A-Z0-9]{6,}[-_]?\d{4,}$",              # ABC123-0001
        r"^\d{8,}$",                                # Long numeric IDs
    ]
    
    def validate(self, invoice_number: Optional[str]) -> InvoiceValidationResult:
        """
        Validate invoice number against Polish standards.
        
        Args:
            invoice_number: The invoice number to validate
            
        Returns:
            InvoiceValidationResult with validation status and details
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check for missing/empty
        if not invoice_number or invoice_number.lower() in ("none", "null", ""):
            errors.append("Brak numeru faktury")
            return InvoiceValidationResult(
                is_valid=False,
                errors=errors,
                normalized_number=None,
                warnings=warnings
            )
        
        # Normalize
        normalized = invoice_number.strip()
        
        # Check for generic/placeholder patterns
        for pattern in self.GENERIC_PATTERNS:
            if re.match(pattern, normalized.lower()):
                errors.append(
                    f"Generyczny numer faktury: '{invoice_number}' - "
                    "wymaga uzupełnienia prawidłowym numerem"
                )
                return InvoiceValidationResult(
                    is_valid=False,
                    errors=errors,
                    normalized_number=None,
                    warnings=warnings
                )
        
        # Check if matches known valid format
        normalized_upper = normalized.upper()
        is_valid_format = any(
            re.match(p, normalized_upper, re.IGNORECASE)
            for p in self.VALID_PATTERNS
        )
        
        if not is_valid_format:
            # Not an error, but a warning for non-standard formats
            warnings.append(
                f"Niestandardowy format numeru faktury: '{invoice_number}'"
            )
        
        return InvoiceValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            normalized_number=normalized_upper if not errors else None,
            warnings=warnings
        )
    
    def is_generic(self, invoice_number: Optional[str]) -> bool:
        """Quick check if invoice number is generic/placeholder."""
        if not invoice_number:
            return True
        
        normalized = invoice_number.strip().lower()
        return any(
            re.match(pattern, normalized)
            for pattern in self.GENERIC_PATTERNS
        )
