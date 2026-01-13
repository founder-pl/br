"""
Tests for BR Documentation Generator validators.
"""
import pytest
from datetime import date
from decimal import Decimal

from br_doc_generator.models import (
    ProjectInput,
    CompanyInfo,
    ProjectTimeline,
    InnovationDetails,
    ProjectCosts,
    PersonnelEmploymentCost,
    MaterialCost,
    InnovationType,
    InnovationScale,
    ValidationStatus,
)
from br_doc_generator.validators.structure import StructureValidator
from br_doc_generator.validators.legal import LegalComplianceValidator
from br_doc_generator.validators.financial import FinancialValidator
from br_doc_generator.validators.base import ValidationContext
from br_doc_generator.config import ValidationConfig


@pytest.fixture
def validation_config():
    """Default validation config."""
    return ValidationConfig()


@pytest.fixture
def sample_project_input():
    """Sample project input for testing."""
    return ProjectInput(
        project_name="System AI do analizy dokumentów",
        project_description="Innowacyjny system wykorzystujący uczenie maszynowe do automatycznej analizy dokumentów B+R",
        company=CompanyInfo(
            name="Softreck Sp. z o.o.",
            nip="5252448481",
            address="ul. Testowa 1, 00-001 Warszawa",
        ),
        timeline=ProjectTimeline(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            milestones=[
                {"name": "Etap 1", "date": "2024-03-31", "description": "Analiza"},
                {"name": "Etap 2", "date": "2024-06-30", "description": "Implementacja"},
            ],
        ),
        innovation=InnovationDetails(
            type=InnovationType.PRODUCT,
            scale=InnovationScale.COMPANY,
            description="System nowatorski w skali firmy",
            novelty_justification="Pierwsza implementacja AI w procesach firmy",
        ),
        methodology="Metodologia Agile z elementami Design Thinking. Systematyczne podejście z etapami: analiza, projektowanie, implementacja, testowanie.",
        research_goals=["Stworzenie modelu ML", "Integracja z systemami"],
        expected_results=["Automatyzacja procesów", "Redukcja czasu o 50%"],
        costs=ProjectCosts(
            personnel_employment=[
                PersonnelEmploymentCost(
                    name="Jan Kowalski",
                    role="Lead Developer",
                    monthly_gross_salary=Decimal("15000"),
                    br_time_percent=80,
                    months_worked=12,
                )
            ],
            materials=[
                MaterialCost(
                    description="Serwer GPU",
                    amount=Decimal("50000"),
                    justification="Do trenowania modeli ML",
                )
            ],
        ),
        br_criteria={
            "systematycznosc": True,
            "tworczosc": True,
            "nowatorstwo": True,
            "niepewnosc": True,
        },
    )


@pytest.fixture
def valid_document():
    """Sample valid markdown document."""
    return """# Dokumentacja B+R: System AI do analizy dokumentów

## Streszczenie wykonawcze

Niniejszy dokument opisuje systematyczny i planowy projekt badawczo-rozwojowy 
realizowany przez Softreck Sp. z o.o. (NIP: 5252448481). Projekt ma charakter 
twórczy i innowacyjny, wprowadzając nowatorskie rozwiązania w dziedzinie AI.

## Opis projektu

Projekt obejmuje stworzenie innowacyjnego systemu wykorzystującego uczenie maszynowe.
Podejście jest systematyczne i metodyczne, z jasno określonymi etapami i harmonogramem.

## Metodologia

Stosujemy metodologię Agile z elementami Design Thinking. Systematyczne podejście
zapewnia planowy przebieg prac. Każda faza projektu jest starannie zaplanowana.

### Etapy realizacji

1. Analiza wymagań - systematyczne zbieranie informacji
2. Projektowanie - twórcze opracowanie architektury
3. Implementacja - nowatorskie rozwiązania techniczne
4. Testowanie - weryfikacja hipotez badawczych

## Innowacyjność

Projekt ma charakter nowatorski i przełomowy w skali firmy. Wprowadza pionierskie
rozwiązania oparte na najnowszej wiedzy z dziedziny AI. Stan techniki został
szczegółowo przeanalizowany.

## Koszty B+R

### Wynagrodzenia pracowników

- Jan Kowalski (Lead Developer): 15 000 PLN × 12 miesięcy × 80% = 144 000 PLN
- Stawka odliczenia: 200%
- Kwota do odliczenia: 288 000 PLN

### Materiały i surowce

- Serwer GPU: 50 000 PLN
- Stawka odliczenia: 100%
- Kwota do odliczenia: 50 000 PLN

### Podsumowanie kosztów

| Kategoria | Kwota brutto | Stawka | Do odliczenia |
|-----------|-------------|--------|---------------|
| Wynagrodzenia | 144 000 PLN | 200% | 288 000 PLN |
| Materiały | 50 000 PLN | 100% | 50 000 PLN |
| **Razem** | **194 000 PLN** | - | **338 000 PLN** |

## Harmonogram

Rok podatkowy: 2024

| Etap | Data | Opis |
|------|------|------|
| Start | 2024-01-01 | Rozpoczęcie projektu |
| Etap 1 | 2024-03-31 | Analiza |
| Etap 2 | 2024-06-30 | Implementacja |
| Zakończenie | 2024-12-31 | Finalizacja |

## Analiza ryzyka

Projekt wiąże się z ryzykiem i niepewnością badawczą. Główne wyzwania:
- Niepewność co do skuteczności modeli ML
- Ryzyko techniczne związane z integracją
- Problem badawczy wymaga weryfikacji hipotez

## Wnioski

Projekt spełnia wszystkie kryteria działalności badawczo-rozwojowej zgodnie 
z art. 18d ustawy o CIT:
- Systematyczność - planowe i metodyczne podejście
- Twórczość - oryginalne rozwiązania
- Nowatorstwo - innowacja w skali firmy
- Niepewność - ryzyko badawcze
"""


class TestStructureValidator:
    """Tests for StructureValidator."""

    def test_valid_document_passes(self, validation_config, valid_document, sample_project_input):
        """Valid document should pass structure validation."""
        validator = StructureValidator(validation_config)
        context = ValidationContext(
            document=valid_document,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
        assert result.score >= 0.7

    def test_missing_sections_fails(self, validation_config, sample_project_input):
        """Document missing required sections should fail."""
        incomplete_doc = """# Dokumentacja B+R

## Streszczenie

Krótki opis projektu.
"""
        validator = StructureValidator(validation_config)
        context = ValidationContext(
            document=incomplete_doc,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status == ValidationStatus.FAILED
        assert len(result.issues) > 0

    def test_empty_document_fails(self, validation_config, sample_project_input):
        """Empty document should fail validation."""
        validator = StructureValidator(validation_config)
        context = ValidationContext(
            document="",
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status == ValidationStatus.FAILED


class TestLegalComplianceValidator:
    """Tests for LegalComplianceValidator."""

    def test_valid_document_passes(self, validation_config, valid_document, sample_project_input):
        """Document with all BR criteria should pass."""
        validator = LegalComplianceValidator(validation_config)
        context = ValidationContext(
            document=valid_document,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
        assert result.score >= 0.6

    def test_missing_keywords_fails(self, validation_config, sample_project_input):
        """Document missing BR keywords should fail."""
        doc_without_keywords = """# Dokumentacja projektu

## Opis

To jest projekt informatyczny firmy Softreck (NIP: 5252448481).

## Koszty

Koszty wyniosły 100000 PLN.
"""
        validator = LegalComplianceValidator(validation_config)
        context = ValidationContext(
            document=doc_without_keywords,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status == ValidationStatus.FAILED
        assert any("systematyczn" in issue.lower() or "twórcz" in issue.lower() 
                   for issue in result.issues)

    def test_nip_validation(self, validation_config, sample_project_input):
        """Valid NIP should be detected."""
        doc_with_nip = """# Dokumentacja B+R

Projekt firmy Softreck Sp. z o.o. (NIP: 5252448481).

Systematyczne i planowe podejście. Twórczy i innowacyjny projekt.
Nowatorskie i przełomowe rozwiązania. Pionierska innowacja.
Ryzyko i niepewność badawcza.
"""
        validator = LegalComplianceValidator(validation_config)
        context = ValidationContext(
            document=doc_with_nip,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        # NIP should be found
        assert not any("NIP" in issue and "brak" in issue.lower() 
                       for issue in result.issues)

    def test_invalid_nip_checksum(self, validation_config, sample_project_input):
        """Invalid NIP checksum should be detected."""
        # Change NIP in project input to invalid one
        sample_project_input.company.nip = "1234567890"  # Invalid checksum
        
        doc = """# Dokumentacja B+R

Projekt firmy Test (NIP: 1234567890).

Systematyczne i planowe podejście metodyczne.
Twórczy i innowacyjny oryginalny projekt.
Nowatorskie i przełomowe rozwiązania pionierskie. Nowa wiedza.
Ryzyko i niepewność badawcza.
"""
        validator = LegalComplianceValidator(validation_config)
        context = ValidationContext(
            document=doc,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        # Should have warning about NIP checksum
        assert any("NIP" in issue for issue in result.issues)


class TestFinancialValidator:
    """Tests for FinancialValidator."""

    def test_valid_costs_pass(self, validation_config, valid_document, sample_project_input):
        """Document with correct cost calculations should pass."""
        validator = FinancialValidator(validation_config)
        context = ValidationContext(
            document=valid_document,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]

    def test_missing_costs_fails(self, validation_config, sample_project_input):
        """Document without cost section should fail."""
        doc_no_costs = """# Dokumentacja B+R

## Opis projektu

Projekt badawczy bez sekcji kosztów.
"""
        validator = FinancialValidator(validation_config)
        context = ValidationContext(
            document=doc_no_costs,
            project_input=sample_project_input,
        )
        
        result = validator.validate(context)
        
        assert result.status == ValidationStatus.FAILED

    def test_deduction_rates_validation(self, validation_config):
        """Correct deduction rates should be validated."""
        validator = FinancialValidator(validation_config)
        
        # Personnel should be 200%
        assert validator._get_expected_rate("personnel_employment") == Decimal("2.0")
        assert validator._get_expected_rate("personnel_civil") == Decimal("2.0")
        
        # Materials should be 100%
        assert validator._get_expected_rate("materials") == Decimal("1.0")
        assert validator._get_expected_rate("equipment") == Decimal("1.0")


class TestNIPValidation:
    """Tests for NIP checksum validation."""

    def test_valid_nips(self):
        """Valid NIPs should pass checksum."""
        from br_doc_generator.validators.legal import LegalComplianceValidator
        
        validator = LegalComplianceValidator(ValidationConfig())
        
        # Known valid NIPs
        valid_nips = [
            "5252448481",
            "7811767426",
            "5213017228",
        ]
        
        for nip in valid_nips:
            assert validator._validate_nip_checksum(nip), f"NIP {nip} should be valid"

    def test_invalid_nips(self):
        """Invalid NIPs should fail checksum."""
        from br_doc_generator.validators.legal import LegalComplianceValidator
        
        validator = LegalComplianceValidator(ValidationConfig())
        
        invalid_nips = [
            "1234567890",
            "0000000000",
            "9999999999",
        ]
        
        for nip in invalid_nips:
            assert not validator._validate_nip_checksum(nip), f"NIP {nip} should be invalid"


class TestProjectCostsCalculation:
    """Tests for cost calculations."""

    def test_personnel_cost_calculation(self):
        """Personnel costs should calculate correctly."""
        cost = PersonnelEmploymentCost(
            name="Jan Kowalski",
            role="Developer",
            monthly_gross_salary=Decimal("10000"),
            br_time_percent=50,
            months_worked=12,
        )
        
        # Total: 10000 * 12 * 0.5 = 60000
        assert cost.total_cost == Decimal("60000")
        
        # Deduction at 200%: 60000 * 2 = 120000
        assert cost.deduction_amount == Decimal("120000")

    def test_material_cost_calculation(self):
        """Material costs should calculate correctly."""
        cost = MaterialCost(
            description="Serwer",
            amount=Decimal("50000"),
            justification="Do obliczeń",
        )
        
        # Deduction at 100%: 50000 * 1 = 50000
        assert cost.deduction_amount == Decimal("50000")

    def test_total_costs_aggregation(self, sample_project_input):
        """Total costs should aggregate correctly."""
        costs = sample_project_input.costs
        
        total_gross = costs.total_gross
        total_deduction = costs.total_deduction
        
        # Personnel: 15000 * 12 * 0.8 = 144000
        # Materials: 50000
        # Total gross: 194000
        assert total_gross == Decimal("194000")
        
        # Personnel deduction: 144000 * 2 = 288000
        # Materials deduction: 50000 * 1 = 50000
        # Total deduction: 338000
        assert total_deduction == Decimal("338000")


# Run with: pytest tests/test_validators.py -v
