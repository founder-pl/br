"""Tests for validation pipeline"""
import pytest
from br_validators import (
    create_default_pipeline,
    StructureValidator,
    LegalValidator,
    FinancialValidator,
    ValidationContext,
)


SAMPLE_PROJECT_CARD = """
# Karta Projektu B+R

## Identyfikacja

**Nazwa projektu:** System zarządzania dokumentacją B+R
**NIP:** 588-191-86-62
**Rok podatkowy:** 2025

## Opis projektu

Projekt obejmuje rozwój systemu automatyzacji dokumentacji 
działalności badawczo-rozwojowej zgodnie z art. 18d CIT.

## Zespół

- Jan Kowalski - Programista
- Anna Nowak - Analityk

## Koszty

| Kategoria | Kwota |
|-----------|-------|
| Wynagrodzenia (UoP) | 50 000,00 zł |
| Materiały | 10 000,00 zł |
| **Suma** | 60 000,00 zł |
"""

SAMPLE_NEXUS = """
# Obliczenie Nexus

## Składniki

- a (koszty bezpośrednie): 50000
- b (usługi zewnętrzne): 10000
- c (podmioty powiązane): 0
- d (zakup IP): 0

## Obliczenie

nexus = ((a + b) × 1.3) / (a + b + c + d)
nexus = ((50000 + 10000) × 1.3) / 60000
Nexus: 1.0000
"""


@pytest.mark.asyncio
class TestStructureValidator:
    """Tests for StructureValidator"""
    
    async def test_valid_project_card(self):
        validator = StructureValidator()
        context = ValidationContext(
            document_type="project_card",
            content=SAMPLE_PROJECT_CARD,
        )
        
        result = await validator.validate(context)
        
        assert result.valid is True
        assert result.score > 0.8
    
    async def test_missing_title(self):
        validator = StructureValidator()
        context = ValidationContext(
            document_type="project_card",
            content="Some content without title\n" * 10,
        )
        
        result = await validator.validate(context)
        
        assert result.valid is False
        assert any(i.code == "MISSING_TITLE" for i in result.issues)
    
    async def test_too_short(self):
        validator = StructureValidator()
        context = ValidationContext(
            document_type="project_card",
            content="# Title\nShort",
        )
        
        result = await validator.validate(context)
        
        assert any(i.code == "DOC_TOO_SHORT" for i in result.issues)


@pytest.mark.asyncio
class TestLegalValidator:
    """Tests for LegalValidator"""
    
    async def test_valid_nip(self):
        validator = LegalValidator()
        context = ValidationContext(
            document_type="project_card",
            content="NIP: 588-191-86-62",
        )
        
        result = await validator.validate(context)
        
        # Should not have NIP error
        assert not any(i.code == "INVALID_NIP" for i in result.issues)
    
    async def test_invalid_nip(self):
        validator = LegalValidator()
        context = ValidationContext(
            document_type="project_card",
            content="NIP: 123-456-78-90",  # Invalid checksum
        )
        
        result = await validator.validate(context)
        
        assert any(i.code == "INVALID_NIP" for i in result.issues)


@pytest.mark.asyncio
class TestFinancialValidator:
    """Tests for FinancialValidator"""
    
    async def test_valid_nexus(self):
        validator = FinancialValidator()
        context = ValidationContext(
            document_type="nexus_calculation",
            content=SAMPLE_NEXUS,
        )
        
        result = await validator.validate(context)
        
        # Should not have Nexus errors
        assert not any("NEXUS" in i.code and i.code != "NEXUS_LOW" for i in result.issues)
    
    async def test_nexus_exceeds_one(self):
        validator = FinancialValidator()
        context = ValidationContext(
            document_type="nexus_calculation",
            content="Nexus: 1.5000",
        )
        
        result = await validator.validate(context)
        
        assert any(i.code == "NEXUS_EXCEEDS_ONE" for i in result.issues)
    
    async def test_negative_amount(self):
        validator = FinancialValidator()
        context = ValidationContext(
            document_type="expense_registry",
            content="Kwota: -500,00 zł",
        )
        
        result = await validator.validate(context)
        
        # Negative amounts should be detected
        assert any(i.code == "NEGATIVE_AMOUNT" for i in result.issues)


@pytest.mark.asyncio
class TestValidationPipeline:
    """Tests for ValidationPipeline"""
    
    async def test_full_pipeline(self):
        pipeline = create_default_pipeline()
        
        result = await pipeline.validate(
            content=SAMPLE_PROJECT_CARD,
            document_type="project_card",
            year=2025,
        )
        
        assert "valid" in result
        assert "overall_score" in result
        assert "stages" in result
        assert len(result["stages"]) == 3  # structure, legal, financial
    
    async def test_quick_validate(self):
        pipeline = create_default_pipeline()
        
        is_valid = await pipeline.validate_quick(
            SAMPLE_PROJECT_CARD,
            "project_card"
        )
        
        assert isinstance(is_valid, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
