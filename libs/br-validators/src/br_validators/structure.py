"""
Structure validator for B+R documents.

Validates document structure, required sections, and formatting.
"""
import re
from typing import Any, Dict, List, Optional

from br_core.types import ValidationResult, ValidationSeverity

from .base import BaseValidator, ValidationContext, ValidationStage


# Required sections by document type
REQUIRED_SECTIONS = {
    "project_card": [
        ("Identyfikacja", r"##\s*(Identyfikacja|Dane\s+projektu)", True),
        ("Opis projektu", r"##\s*(Opis|Cel|Zakres)", True),
        ("Zespół", r"##\s*(Zespół|Pracownicy|Kadra)", False),
        ("Koszty", r"##\s*(Koszty|Wydatki|Budżet)", True),
    ],
    "expense_registry": [
        ("Nagłówek", r"#\s*(Ewidencja|Rejestr)\s+(Wydatków|Kosztów)", True),
        ("Podsumowanie", r"##\s*(Podsumowanie|Suma)", True),
        ("Tabela wydatków", r"\|.*\|.*\|", True),
    ],
    "nexus_calculation": [
        ("Nagłówek", r"#\s*(Obliczenie\s+)?Nexus", True),
        ("Składniki", r"##\s*(Składniki|Komponenty)", True),
        ("Obliczenie", r"##\s*(Obliczenie|Wynik|Kalkulacja)", True),
        ("Wzór", r"nexus\s*=|formula", False),
    ],
    "timesheet_monthly": [
        ("Nagłówek", r"#\s*(Ewidencja|Rejestr)\s+Czasu", True),
        ("Pracownik", r"(Pracownik|Imię|Nazwisko)", True),
        ("Godziny", r"(godzin|hours|czas)", True),
    ],
}

# Required fields by document type
REQUIRED_FIELDS = {
    "project_card": [
        ("NIP", r"\bNIP[:\s]*\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b", True),
        ("Rok", r"\b(Rok|Year)[:\s]*\d{4}\b", True),
        ("Nazwa projektu", r"(Nazwa|Tytuł)\s*(projektu)?[:\s]*.{3,}", True),
    ],
    "expense_registry": [
        ("Kwota", r"\d+[,.\s]\d{2}\s*(zł|PLN)", True),
        ("Data", r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[./]\d{2}[./]\d{4}", True),
    ],
    "nexus_calculation": [
        ("Wartość Nexus", r"[Nn]exus[:\s]*\d+[.,]\d+", True),
        ("Składnik a", r"\ba[:\s]*\d+", True),
        ("Składnik b", r"\bb[:\s]*\d+", False),
    ],
}


class StructureValidator(BaseValidator):
    """Validates document structure and formatting"""
    
    stage = ValidationStage.STRUCTURE
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate document structure"""
        issues = []
        content = context.content
        doc_type = context.document_type
        
        # Check minimum length
        if len(content) < 100:
            issues.append(self.error(
                "Dokument jest zbyt krótki (minimum 100 znaków)",
                code="DOC_TOO_SHORT"
            ))
        
        # Check for title
        if not re.search(r'^#\s+.+', content, re.MULTILINE):
            issues.append(self.error(
                "Brak nagłówka głównego (# Tytuł)",
                code="MISSING_TITLE"
            ))
        
        # Check required sections
        required_sections = REQUIRED_SECTIONS.get(doc_type, [])
        for section_name, pattern, required in required_sections:
            if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                if required:
                    issues.append(self.error(
                        f"Brak wymaganej sekcji: {section_name}",
                        code="MISSING_SECTION",
                        suggestion=f"Dodaj sekcję ## {section_name}"
                    ))
                else:
                    issues.append(self.warning(
                        f"Brak opcjonalnej sekcji: {section_name}",
                        code="MISSING_OPTIONAL_SECTION"
                    ))
        
        # Check required fields
        required_fields = REQUIRED_FIELDS.get(doc_type, [])
        for field_name, pattern, required in required_fields:
            if not re.search(pattern, content, re.IGNORECASE):
                if required:
                    issues.append(self.error(
                        f"Brak wymaganego pola: {field_name}",
                        code="MISSING_FIELD"
                    ))
                else:
                    issues.append(self.warning(
                        f"Brak opcjonalnego pola: {field_name}",
                        code="MISSING_OPTIONAL_FIELD"
                    ))
        
        # Check table formatting
        tables = re.findall(r'\|[^\n]+\|', content)
        if tables:
            for i, table_row in enumerate(tables):
                if table_row.count('|') < 3:
                    issues.append(self.warning(
                        f"Nieprawidłowy format tabeli w wierszu {i+1}",
                        code="INVALID_TABLE_FORMAT"
                    ))
        
        # Check for empty sections
        empty_sections = re.findall(r'##\s+[^\n]+\n\s*\n##', content)
        if empty_sections:
            issues.append(self.warning(
                f"Znaleziono {len(empty_sections)} pustych sekcji",
                code="EMPTY_SECTIONS"
            ))
        
        # Calculate score
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        
        max_score = len(required_sections) + len(required_fields) + 3  # +3 for basic checks
        deductions = error_count * 0.2 + warning_count * 0.05
        score = max(0, 1 - deductions)
        
        result = ValidationResult(
            valid=error_count == 0,
            issues=issues,
            score=score,
            stage=self.stage.value,
        )
        
        context.set_stage_result(self.stage, result)
        context.add_issues(issues)
        
        return result
