#!/usr/bin/env python3
"""
Documentation Validation Tests for B+R System.

Tests compliance with brgenerator requirements:
- Structure validation (required sections)
- Content validation (completeness, consistency)
- Legal compliance (art. 18d CIT requirements)
- Financial validation (calculations, categories)

Based on: brgenerator/docs/02-br-doc-generator-component.md
"""
import pytest
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    type: str
    severity: Severity
    location: str
    message: str
    suggestion: str = ""


@dataclass
class ValidationReport:
    stage: str
    timestamp: str
    status: str  # passed, failed, warning
    score: float
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "validation_stage": self.stage,
            "timestamp": self.timestamp,
            "status": self.status,
            "score": self.score,
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity.value,
                    "location": i.location,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ]
        }


class BRDocumentationValidator:
    """
    Multi-level documentation validator following brgenerator pipeline.
    
    Stages:
    1. Structure Validation - markdown structure and required sections
    2. Content Validation - completeness and consistency
    3. Legal Compliance - art. 18d CIT requirements
    4. Financial Validation - calculations and categories
    """
    
    # Required sections per brgenerator spec
    REQUIRED_SECTIONS = [
        "Streszczenie Wykonawcze",
        "Opis projektu",
        "Metodologia badawcza",
        "Podsumowanie kosztów",
        "Podstawa prawna",
        "Szczegółowa dokumentacja wydatków",
        "Oświadczenie"
    ]
    
    # Required subsections
    REQUIRED_SUBSECTIONS = {
        "Opis projektu": ["Cel projektu", "Innowacyjność", "Zakres prac"],
        "Metodologia badawcza": ["Systematyczność", "Twórczość"],
        "Podsumowanie kosztów": ["Zestawienie ogólne"],
        "Podstawa prawna": ["Stawki odliczenia"]
    }
    
    # Legal requirements per CIT art. 18d
    LEGAL_REQUIREMENTS = {
        "company_nip": r"NIP[:\s*\*]*\d{10}|\*\*NIP[:\s*\*]*\d{10}",
        "fiscal_year": r"[Rr]ok\s*podatkowy[:\s\*]*\d{4}",
        "article_reference": r"[Aa]rt\.\s*18d|[Aa]rt\.\s*26e",
        "deduction_rates": r"200%|100%"
    }
    
    # B+R cost categories per CIT
    BR_CATEGORIES = [
        "personnel_employment",  # Wynagrodzenia pracowników
        "personnel_civil",       # Umowy cywilnoprawne
        "materials",            # Materiały i surowce
        "equipment",            # Sprzęt specjalistyczny
        "depreciation",         # Amortyzacja
        "expertise",            # Ekspertyzy i opinie
        "external_services"     # Usługi zewnętrzne
    ]
    
    def __init__(self, content: str):
        self.content = content
        self.issues: List[ValidationIssue] = []
        self.reports: List[ValidationReport] = []
    
    def validate_all(self) -> Dict[str, ValidationReport]:
        """Run all validation stages."""
        results = {}
        results['structure'] = self.validate_structure()
        results['content'] = self.validate_content()
        results['legal'] = self.validate_legal_compliance()
        results['financial'] = self.validate_financial()
        return results
    
    def validate_structure(self) -> ValidationReport:
        """Stage 2: Structure Validation - check markdown structure and sections."""
        issues = []
        score = 1.0
        
        # Check for required sections
        for section in self.REQUIRED_SECTIONS:
            pattern = rf"#{{1,3}}\s*\d*\.?\s*{re.escape(section)}"
            if not re.search(pattern, self.content, re.IGNORECASE):
                # Try simpler match
                if section.lower() not in self.content.lower():
                    issues.append(ValidationIssue(
                        type="missing_section",
                        severity=Severity.CRITICAL,
                        location=f"section:{section}",
                        message=f"Brak wymaganej sekcji: {section}",
                        suggestion=f"Dodaj sekcję '## {section}' do dokumentacji"
                    ))
                    score -= 0.1
        
        # Check for proper markdown structure
        if not re.search(r'^#\s+', self.content, re.MULTILINE):
            issues.append(ValidationIssue(
                type="invalid_structure",
                severity=Severity.CRITICAL,
                location="document:header",
                message="Brak nagłówka głównego (H1)",
                suggestion="Dodaj nagłówek '# Dokumentacja Projektu B+R: [Nazwa]'"
            ))
            score -= 0.15
        
        # Check for tables
        if '|' not in self.content:
            issues.append(ValidationIssue(
                type="missing_tables",
                severity=Severity.WARNING,
                location="document:tables",
                message="Brak tabel z danymi finansowymi",
                suggestion="Dodaj tabele podsumowujące koszty i odliczenia"
            ))
            score -= 0.05
        
        # Check section numbering
        section_numbers = re.findall(r'^##\s+(\d+)\.', self.content, re.MULTILINE)
        if section_numbers:
            expected = list(range(1, len(section_numbers) + 1))
            actual = [int(n) for n in section_numbers]
            if actual != expected[:len(actual)]:
                issues.append(ValidationIssue(
                    type="inconsistent_numbering",
                    severity=Severity.INFO,
                    location="document:sections",
                    message="Niekonsekwentna numeracja sekcji",
                    suggestion="Popraw numerację sekcji (1, 2, 3...)"
                ))
        
        status = "passed" if not issues else ("warning" if score > 0.7 else "failed")
        
        report = ValidationReport(
            stage="structure_validation",
            timestamp=datetime.now().isoformat(),
            status=status,
            score=max(0, score),
            issues=issues
        )
        self.reports.append(report)
        return report
    
    def validate_content(self) -> ValidationReport:
        """Stage 3: Content Validation - check completeness and consistency."""
        issues = []
        score = 1.0
        
        # Check for project name
        if not re.search(r'Projekt[:\s]+\w+', self.content):
            issues.append(ValidationIssue(
                type="missing_project_name",
                severity=Severity.CRITICAL,
                location="document:header",
                message="Brak nazwy projektu",
                suggestion="Dodaj nazwę projektu w nagłówku"
            ))
            score -= 0.1
        
        # Check for expense details
        expense_count = len(re.findall(r'###\s*Iteracja\s*#\d+', self.content))
        if expense_count == 0:
            issues.append(ValidationIssue(
                type="missing_expenses",
                severity=Severity.WARNING,
                location="section:expenses",
                message="Brak szczegółowych danych o wydatkach",
                suggestion="Dodaj szczegółowe opisy każdego wydatku"
            ))
            score -= 0.1
        
        # Check for "None" values (incomplete data)
        none_count = self.content.count('| None |') + self.content.count('None')
        if none_count > 5:
            issues.append(ValidationIssue(
                type="incomplete_data",
                severity=Severity.WARNING,
                location="document:data",
                message=f"Znaleziono {none_count} niekompletnych danych (None)",
                suggestion="Uzupełnij brakujące dane dostawców i NIP"
            ))
            score -= 0.05 * min(none_count // 5, 3)
        
        # Check for B+R justification
        if "Uzasadnienie kwalifikacji B+R" not in self.content:
            issues.append(ValidationIssue(
                type="missing_justification",
                severity=Severity.CRITICAL,
                location="section:expenses",
                message="Brak uzasadnienia kwalifikacji B+R dla wydatków",
                suggestion="Dodaj uzasadnienie powiązania wydatku z działalnością B+R"
            ))
            score -= 0.15
        
        # Check innovation description
        if not re.search(r'[Ii]nnowacyj', self.content):
            issues.append(ValidationIssue(
                type="missing_innovation",
                severity=Severity.WARNING,
                location="section:innovation",
                message="Brak opisu innowacyjności projektu",
                suggestion="Dodaj sekcję opisującą elementy innowacyjne"
            ))
            score -= 0.1
        
        status = "passed" if not issues else ("warning" if score > 0.7 else "failed")
        
        report = ValidationReport(
            stage="content_validation",
            timestamp=datetime.now().isoformat(),
            status=status,
            score=max(0, score),
            issues=issues
        )
        self.reports.append(report)
        return report
    
    def validate_legal_compliance(self) -> ValidationReport:
        """Stage 4: Legal Compliance - verify CIT art. 18d requirements."""
        issues = []
        score = 1.0
        
        # Check NIP
        if not re.search(self.LEGAL_REQUIREMENTS['company_nip'], self.content):
            issues.append(ValidationIssue(
                type="missing_nip",
                severity=Severity.CRITICAL,
                location="document:header",
                message="Brak NIP firmy",
                suggestion="Dodaj NIP firmy w formacie: NIP: 1234567890"
            ))
            score -= 0.2
        
        # Check fiscal year
        if not re.search(self.LEGAL_REQUIREMENTS['fiscal_year'], self.content):
            issues.append(ValidationIssue(
                type="missing_fiscal_year",
                severity=Severity.CRITICAL,
                location="document:header",
                message="Brak roku podatkowego",
                suggestion="Dodaj rok podatkowy w formacie: Rok podatkowy: 2025"
            ))
            score -= 0.15
        
        # Check legal article references
        if not re.search(self.LEGAL_REQUIREMENTS['article_reference'], self.content):
            issues.append(ValidationIssue(
                type="missing_legal_reference",
                severity=Severity.WARNING,
                location="section:legal",
                message="Brak odniesienia do art. 18d CIT lub art. 26e PIT",
                suggestion="Dodaj podstawę prawną z powołaniem na odpowiedni artykuł"
            ))
            score -= 0.1
        
        # Check deduction rates
        if not re.search(self.LEGAL_REQUIREMENTS['deduction_rates'], self.content):
            issues.append(ValidationIssue(
                type="missing_deduction_rates",
                severity=Severity.WARNING,
                location="section:costs",
                message="Brak stawek odliczenia (100%, 200%)",
                suggestion="Dodaj tabele ze stawkami odliczenia dla kategorii kosztów"
            ))
            score -= 0.1
        
        # Check for oświadczenie (declaration)
        if "Oświadczam" not in self.content and "oświadczenie" not in self.content.lower():
            issues.append(ValidationIssue(
                type="missing_declaration",
                severity=Severity.CRITICAL,
                location="section:declaration",
                message="Brak oświadczenia o zgodności danych",
                suggestion="Dodaj sekcję Oświadczenie z deklaracją o zgodności"
            ))
            score -= 0.15
        
        status = "passed" if not issues else ("warning" if score > 0.7 else "failed")
        
        report = ValidationReport(
            stage="legal_compliance",
            timestamp=datetime.now().isoformat(),
            status=status,
            score=max(0, score),
            issues=issues
        )
        self.reports.append(report)
        return report
    
    def validate_financial(self) -> ValidationReport:
        """Stage 5: Financial Validation - verify calculations and categories."""
        issues = []
        score = 1.0
        
        # Extract amounts from content
        amounts = re.findall(r'(\d+[.,]\d{2})\s*PLN', self.content)
        
        if not amounts:
            issues.append(ValidationIssue(
                type="missing_amounts",
                severity=Severity.CRITICAL,
                location="document:financial",
                message="Brak kwot finansowych w dokumentacji",
                suggestion="Dodaj kwoty wydatków w formacie: 1234.56 PLN"
            ))
            score -= 0.3
        
        # Check for cost summary table
        if "Suma wszystkich wydatków" not in self.content:
            issues.append(ValidationIssue(
                type="missing_cost_summary",
                severity=Severity.WARNING,
                location="section:costs",
                message="Brak podsumowania kosztów",
                suggestion="Dodaj tabelę z sumą wszystkich wydatków"
            ))
            score -= 0.1
        
        # Check for qualified vs total split
        if "kwalifikowanych" not in self.content.lower():
            issues.append(ValidationIssue(
                type="missing_qualified_split",
                severity=Severity.WARNING,
                location="section:costs",
                message="Brak podziału na koszty kwalifikowane i niekwalifikowane",
                suggestion="Dodaj podział wydatków na kwalifikowane i pozostałe"
            ))
            score -= 0.1
        
        # Check for category breakdown
        categories_found = 0
        for cat in ['Wynagrodzenia', 'Materiały', 'Ekspertyzy', 'Amortyzacja', 'Usługi']:
            if cat.lower() in self.content.lower():
                categories_found += 1
        
        if categories_found < 2:
            issues.append(ValidationIssue(
                type="missing_category_breakdown",
                severity=Severity.INFO,
                location="section:costs",
                message="Brak pełnego podziału kosztów według kategorii B+R",
                suggestion="Dodaj tabelę z podziałem kosztów na kategorie"
            ))
            score -= 0.05
        
        # Verify calculations (if possible)
        gross_amounts = re.findall(r'Kwota brutto\s*\|\s*(\d+[.,]\d{2})', self.content)
        if gross_amounts:
            try:
                total_calculated = sum(float(a.replace(',', '.')) for a in gross_amounts)
                # Look for stated total
                total_match = re.search(r'Suma wszystkich wydatków\s*\|\s*(\d+[.,]\d{2})', self.content)
                if total_match:
                    stated_total = float(total_match.group(1).replace(',', '.'))
                    if abs(total_calculated - stated_total) > 0.01:
                        issues.append(ValidationIssue(
                            type="calculation_mismatch",
                            severity=Severity.CRITICAL,
                            location="section:costs",
                            message=f"Niezgodność sum: obliczona={total_calculated:.2f}, podana={stated_total:.2f}",
                            suggestion="Skoryguj sumę wydatków"
                        ))
                        score -= 0.2
            except ValueError:
                pass
        
        status = "passed" if not issues else ("warning" if score > 0.7 else "failed")
        
        report = ValidationReport(
            stage="financial_validation",
            timestamp=datetime.now().isoformat(),
            status=status,
            score=max(0, score),
            issues=issues
        )
        self.reports.append(report)
        return report
    
    def get_overall_score(self) -> float:
        """Calculate overall quality score."""
        if not self.reports:
            return 0.0
        return sum(r.score for r in self.reports) / len(self.reports)
    
    def get_full_report(self) -> dict:
        """Generate full validation report in YAML-compatible format."""
        return {
            "validation_summary": {
                "timestamp": datetime.now().isoformat(),
                "overall_score": self.get_overall_score(),
                "overall_status": "passed" if self.get_overall_score() >= 0.8 else 
                                 ("warning" if self.get_overall_score() >= 0.6 else "failed"),
                "stages_completed": len(self.reports)
            },
            "stage_reports": [r.to_dict() for r in self.reports],
            "total_issues": sum(len(r.issues) for r in self.reports),
            "critical_issues": sum(
                1 for r in self.reports 
                for i in r.issues 
                if i.severity == Severity.CRITICAL
            )
        }


# ========== TESTS ==========

class TestDocumentationStructure:
    """Test Stage 2: Structure Validation"""
    
    SAMPLE_DOC = """# Dokumentacja Projektu B+R: Test

**Kod projektu:** BR-2025-001
**Rok podatkowy:** 2025
**Firma:** Test (NIP: 1234567890)

## Streszczenie Wykonawcze

Test summary.

## 1. Opis projektu

### 1.1 Cel projektu

Test cel.

### 1.2 Innowacyjność rozwiązania

Test innowacyjność.

### 1.3 Zakres prac B+R

Test zakres.

## 2. Metodologia badawcza

### 2.1 Systematyczność

Test.

### 2.2 Twórczość

Test.

## 3. Podsumowanie kosztów

### 3.1 Zestawienie ogólne

| Parametr | Wartość |
|----------|---------|
| Suma wszystkich wydatków | 1000.00 PLN |

## 4. Podstawa prawna

Art. 18d ustawy o CIT.

### Stawki odliczenia kosztów kwalifikowanych:

| Kategoria | Stawka |
|-----------|--------|
| Wynagrodzenia | 200% |

## 5. Szczegółowa dokumentacja wydatków

### Iteracja #1 - Wydatek 1

| Parametr | Wartość |
|----------|---------|
| Kwota brutto | 1000.00 PLN |

**Uzasadnienie kwalifikacji B+R:**

Test uzasadnienie.

## 10. Oświadczenie

Oświadczam, że dane są prawidłowe.
"""
    
    def test_structure_valid(self):
        """Valid document should pass structure validation."""
        validator = BRDocumentationValidator(self.SAMPLE_DOC)
        report = validator.validate_structure()
        assert report.status in ["passed", "warning"]
        assert report.score >= 0.7
    
    def test_structure_missing_header(self):
        """Document without H1 should fail."""
        doc = "## Only H2\n\nNo main header."
        validator = BRDocumentationValidator(doc)
        report = validator.validate_structure()
        assert any(i.type == "invalid_structure" for i in report.issues)
    
    def test_structure_missing_sections(self):
        """Document without required sections should have issues."""
        doc = "# Test\n\nNo sections."
        validator = BRDocumentationValidator(doc)
        report = validator.validate_structure()
        missing = [i for i in report.issues if i.type == "missing_section"]
        assert len(missing) > 0


class TestDocumentationContent:
    """Test Stage 3: Content Validation"""
    
    def test_content_with_expenses(self):
        """Document with expense details should pass."""
        doc = """# Test
### Iteracja #1 - Wydatek 1
**Uzasadnienie kwalifikacji B+R:**
Test.
Projekt innowacyjny.
"""
        validator = BRDocumentationValidator(doc)
        report = validator.validate_content()
        assert report.score >= 0.7
    
    def test_content_missing_justification(self):
        """Document without B+R justification should warn."""
        doc = "# Test\n\nNo justification here."
        validator = BRDocumentationValidator(doc)
        report = validator.validate_content()
        assert any(i.type == "missing_justification" for i in report.issues)


class TestLegalCompliance:
    """Test Stage 4: Legal Compliance"""
    
    def test_legal_with_all_requirements(self):
        """Document with all legal requirements should pass."""
        doc = """# Test
NIP: 1234567890
Rok podatkowy: 2025
Art. 18d ustawy o CIT
Stawka 200% i 100%
Oświadczam, że dane są prawdziwe.
"""
        validator = BRDocumentationValidator(doc)
        report = validator.validate_legal_compliance()
        assert report.status == "passed"
    
    def test_legal_missing_nip(self):
        """Document without NIP should fail."""
        doc = "# Test\n\nNo NIP here."
        validator = BRDocumentationValidator(doc)
        report = validator.validate_legal_compliance()
        assert any(i.type == "missing_nip" for i in report.issues)


class TestFinancialValidation:
    """Test Stage 5: Financial Validation"""
    
    def test_financial_with_amounts(self):
        """Document with amounts should pass."""
        doc = """# Test
| Suma wszystkich wydatków | 1000.00 PLN |
Koszty kwalifikowanych: 500.00 PLN
| Kwota brutto | 1000.00 PLN |
Wynagrodzenia pracowników
"""
        validator = BRDocumentationValidator(doc)
        report = validator.validate_financial()
        assert report.score >= 0.7
    
    def test_financial_missing_amounts(self):
        """Document without amounts should fail."""
        doc = "# Test\n\nNo amounts."
        validator = BRDocumentationValidator(doc)
        report = validator.validate_financial()
        assert any(i.type == "missing_amounts" for i in report.issues)


class TestFullValidation:
    """Test complete validation pipeline."""
    
    def test_full_validation_pipeline(self):
        """Run all validation stages on sample document."""
        doc = TestDocumentationStructure.SAMPLE_DOC
        validator = BRDocumentationValidator(doc)
        results = validator.validate_all()
        
        assert 'structure' in results
        assert 'content' in results
        assert 'legal' in results
        assert 'financial' in results
        
        overall = validator.get_overall_score()
        assert 0 <= overall <= 1
    
    def test_full_report_format(self):
        """Verify report format matches brgenerator spec."""
        doc = TestDocumentationStructure.SAMPLE_DOC
        validator = BRDocumentationValidator(doc)
        validator.validate_all()
        
        report = validator.get_full_report()
        
        assert 'validation_summary' in report
        assert 'stage_reports' in report
        assert 'overall_score' in report['validation_summary']
        assert 'overall_status' in report['validation_summary']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
