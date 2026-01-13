"""
Expense Validation Pipeline - Comprehensive validation for B+R compliance.

P2 Task: Pipeline walidacji – nowe reguły
Based on: todo/05-br-priority-roadmap.md

Validates:
- Invoice data completeness
- Vendor information
- Amount consistency
- B+R qualification criteria
- Documentation requirements
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import date
import re
import structlog

from .invoice_validator import InvoiceValidator

logger = structlog.get_logger()


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must be fixed
    WARNING = "warning"  # Should be fixed
    INFO = "info"        # Recommendation


class ValidationCategory(str, Enum):
    """Categories of validation rules."""
    INVOICE = "invoice"
    VENDOR = "vendor"
    AMOUNT = "amount"
    BR_QUALIFICATION = "br_qualification"
    DOCUMENTATION = "documentation"
    COMPLIANCE = "compliance"


@dataclass
class ValidationIssue:
    """Single validation issue."""
    code: str
    message: str
    severity: ValidationSeverity
    category: ValidationCategory
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of expense validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 0.0  # 0-100 quality score
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity.value,
                    "category": i.category.value,
                    "field": i.field,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ]
        }


class ExpenseValidationPipeline:
    """
    Comprehensive expense validation pipeline.
    
    Runs multiple validation rules and aggregates results.
    """
    
    def __init__(self):
        self.invoice_validator = InvoiceValidator()
        
    def validate(self, expense: Dict[str, Any]) -> ValidationResult:
        """
        Run all validation rules on an expense.
        
        Args:
            expense: Expense data dictionary
            
        Returns:
            ValidationResult with all issues found
        """
        issues: List[ValidationIssue] = []
        
        # Run all validation categories
        issues.extend(self._validate_invoice(expense))
        issues.extend(self._validate_vendor(expense))
        issues.extend(self._validate_amounts(expense))
        issues.extend(self._validate_br_qualification(expense))
        issues.extend(self._validate_documentation(expense))
        issues.extend(self._validate_compliance(expense))
        
        # Calculate quality score
        score = self._calculate_score(issues)
        
        # Determine if valid (no errors)
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score
        )
    
    def _validate_invoice(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate invoice data."""
        issues = []
        
        # Invoice number
        invoice_number = expense.get("invoice_number")
        if not invoice_number:
            issues.append(ValidationIssue(
                code="INV_001",
                message="Brak numeru faktury",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.INVOICE,
                field="invoice_number",
                suggestion="Uzupełnij numer faktury z dokumentu źródłowego"
            ))
        elif self.invoice_validator.is_generic(invoice_number):
            issues.append(ValidationIssue(
                code="INV_002",
                message=f"Generyczny numer faktury: '{invoice_number}'",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.INVOICE,
                field="invoice_number",
                suggestion="Wprowadź właściwy numer faktury z dokumentu"
            ))
        elif not self.invoice_validator.validate(invoice_number):
            issues.append(ValidationIssue(
                code="INV_003",
                message=f"Nieprawidłowy format numeru faktury: '{invoice_number}'",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.INVOICE,
                field="invoice_number",
                suggestion="Sprawdź poprawność numeru faktury"
            ))
        
        # Invoice date
        invoice_date = expense.get("invoice_date")
        if not invoice_date:
            issues.append(ValidationIssue(
                code="INV_004",
                message="Brak daty faktury",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.INVOICE,
                field="invoice_date",
                suggestion="Uzupełnij datę wystawienia faktury"
            ))
        elif isinstance(invoice_date, str):
            try:
                parsed = date.fromisoformat(invoice_date.split('T')[0])
                if parsed > date.today():
                    issues.append(ValidationIssue(
                        code="INV_005",
                        message="Data faktury w przyszłości",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.INVOICE,
                        field="invoice_date",
                        suggestion="Sprawdź poprawność daty faktury"
                    ))
            except ValueError:
                issues.append(ValidationIssue(
                    code="INV_006",
                    message=f"Nieprawidłowy format daty: '{invoice_date}'",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVOICE,
                    field="invoice_date"
                ))
        
        return issues
    
    def _validate_vendor(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate vendor information."""
        issues = []
        
        vendor_name = expense.get("vendor_name")
        vendor_nip = expense.get("vendor_nip")
        
        if not vendor_name:
            issues.append(ValidationIssue(
                code="VND_001",
                message="Brak nazwy dostawcy",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.VENDOR,
                field="vendor_name",
                suggestion="Uzupełnij nazwę dostawcy z faktury"
            ))
        elif len(vendor_name) < 3:
            issues.append(ValidationIssue(
                code="VND_002",
                message=f"Nazwa dostawcy zbyt krótka: '{vendor_name}'",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.VENDOR,
                field="vendor_name",
                suggestion="Wprowadź pełną nazwę firmy"
            ))
        
        if not vendor_nip:
            issues.append(ValidationIssue(
                code="VND_003",
                message="Brak NIP dostawcy",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.VENDOR,
                field="vendor_nip",
                suggestion="Uzupełnij NIP dostawcy dla pełnej dokumentacji"
            ))
        elif vendor_nip and not self._validate_nip(vendor_nip):
            issues.append(ValidationIssue(
                code="VND_004",
                message=f"Nieprawidłowy NIP: '{vendor_nip}'",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.VENDOR,
                field="vendor_nip",
                suggestion="Sprawdź poprawność NIP dostawcy"
            ))
        
        return issues
    
    def _validate_amounts(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate amount fields."""
        issues = []
        
        gross = expense.get("gross_amount")
        net = expense.get("net_amount")
        vat = expense.get("vat_amount")
        currency = expense.get("currency", "PLN")
        
        if gross is None or gross <= 0:
            issues.append(ValidationIssue(
                code="AMT_001",
                message="Brak lub nieprawidłowa kwota brutto",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.AMOUNT,
                field="gross_amount",
                suggestion="Wprowadź kwotę brutto > 0"
            ))
        
        if currency != "PLN":
            issues.append(ValidationIssue(
                code="AMT_002",
                message=f"Waluta inna niż PLN: {currency}",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.AMOUNT,
                field="currency",
                suggestion="Przelicz kwotę na PLN według kursu NBP"
            ))
        
        # Check VAT calculation
        if gross and net and vat:
            expected_gross = float(net) + float(vat)
            actual_gross = float(gross)
            if abs(expected_gross - actual_gross) > 0.02:
                issues.append(ValidationIssue(
                    code="AMT_003",
                    message=f"Niespójność kwot: netto({net}) + VAT({vat}) ≠ brutto({gross})",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.AMOUNT,
                    suggestion="Sprawdź poprawność kwot na fakturze"
                ))
        
        return issues
    
    def _validate_br_qualification(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate B+R qualification criteria."""
        issues = []
        
        br_qualified = expense.get("br_qualified")
        br_category = expense.get("br_category")
        br_reason = expense.get("br_qualification_reason")
        br_rate = expense.get("br_deduction_rate")
        
        if br_qualified:
            if not br_category:
                issues.append(ValidationIssue(
                    code="BR_001",
                    message="Brak kategorii B+R dla wydatku kwalifikowanego",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BR_QUALIFICATION,
                    field="br_category",
                    suggestion="Przypisz kategorię B+R (wynagrodzenia, materiały, usługi, etc.)"
                ))
            
            if not br_reason:
                issues.append(ValidationIssue(
                    code="BR_002",
                    message="Brak uzasadnienia kwalifikacji B+R",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BR_QUALIFICATION,
                    field="br_qualification_reason",
                    suggestion="Dodaj indywidualne uzasadnienie związku z działalnością B+R"
                ))
            elif len(br_reason) < 50:
                issues.append(ValidationIssue(
                    code="BR_003",
                    message=f"Uzasadnienie zbyt krótkie ({len(br_reason)} znaków)",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BR_QUALIFICATION,
                    field="br_qualification_reason",
                    suggestion="Rozszerz uzasadnienie do min. 50 znaków"
                ))
            
            # Check for generic justifications
            generic_phrases = [
                "działalność badawczo-rozwojowa",
                "prace badawczo-rozwojowe",
                "koszt kwalifikowany",
                "wydatek b+r"
            ]
            if br_reason:
                reason_lower = br_reason.lower()
                for phrase in generic_phrases:
                    if phrase in reason_lower and len(br_reason) < 100:
                        issues.append(ValidationIssue(
                            code="BR_004",
                            message=f"Generyczne uzasadnienie zawiera '{phrase}'",
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.BR_QUALIFICATION,
                            field="br_qualification_reason",
                            suggestion="Skonkretyzuj uzasadnienie, opisz konkretne zastosowanie"
                        ))
                        break
            
            if br_rate is None or br_rate <= 0:
                issues.append(ValidationIssue(
                    code="BR_005",
                    message="Brak stawki odliczenia B+R",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BR_QUALIFICATION,
                    field="br_deduction_rate",
                    suggestion="Ustaw stawkę odliczenia (domyślnie 1.0 = 100%)"
                ))
        
        return issues
    
    def _validate_documentation(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate documentation completeness."""
        issues = []
        
        document_id = expense.get("document_id")
        
        if not document_id:
            issues.append(ValidationIssue(
                code="DOC_001",
                message="Brak powiązanego dokumentu źródłowego",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.DOCUMENTATION,
                field="document_id",
                suggestion="Powiąż wydatek z zeskanowanym dokumentem"
            ))
        
        return issues
    
    def _validate_compliance(self, expense: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate tax compliance requirements."""
        issues = []
        
        status = expense.get("status")
        needs_clarification = expense.get("needs_clarification")
        
        if status == "pending":
            issues.append(ValidationIssue(
                code="CMP_001",
                message="Wydatek wymaga zatwierdzenia",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.COMPLIANCE,
                field="status",
                suggestion="Przeklasyfikuj lub zatwierdź wydatek"
            ))
        
        if needs_clarification:
            issues.append(ValidationIssue(
                code="CMP_002",
                message="Wydatek wymaga wyjaśnień",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.COMPLIANCE,
                field="needs_clarification",
                suggestion="Odpowiedz na pytania wyjaśniające"
            ))
        
        return issues
    
    def _validate_nip(self, nip: str) -> bool:
        """Validate Polish NIP number."""
        nip = re.sub(r'[\s\-]', '', nip)
        if len(nip) != 10 or not nip.isdigit():
            return False
        
        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(nip[i]) * weights[i] for i in range(9)) % 11
        return checksum == int(nip[9])
    
    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate quality score based on issues found."""
        base_score = 100.0
        
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                base_score -= 15
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 5
            elif issue.severity == ValidationSeverity.INFO:
                base_score -= 1
        
        return max(0.0, min(100.0, base_score))


# Singleton
_pipeline: Optional[ExpenseValidationPipeline] = None


def get_validation_pipeline() -> ExpenseValidationPipeline:
    """Get or create validation pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ExpenseValidationPipeline()
    return _pipeline
