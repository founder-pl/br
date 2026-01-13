"""
End-to-End Tests for BR Documentation Generator.

These tests verify complete workflows without actual LLM calls.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import date
from decimal import Decimal

from br_doc_generator import (
    BRDocumentationPipeline,
    FormGenerator,
    ValidationPipeline,
    DocumentGenerator,
    PDFRenderer,
    LLMClient,
)
from br_doc_generator.config import AppConfig, load_config
from br_doc_generator.models import (
    ProjectInput,
    ProjectBasicInfo,
    CompanyInfo,
    ProjectTimeline,
    Milestone,
    InnovationInfo,
    MethodologyInfo,
    RiskFactor,
    ResearchMethod,
    ProjectCosts,
    PersonnelEmploymentCost,
    MaterialCost,
    InnovationType,
    InnovationScale,
    CostCategory,
    ValidationStatus,
    DocumentationConfig,
)
from br_doc_generator.validators.base import ValidationContext


class TestFormGeneratorE2E:
    """E2E tests for form generation workflow."""
    
    def test_generate_and_load_form(self):
        """Test generating a form, saving it, and loading it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "test_form.yaml"
            
            # Generate form
            generator = FormGenerator()
            content = generator.generate_empty_form(
                project_name="Test E2E Project",
                fiscal_year=2025,
                output_path=form_path
            )
            
            # Verify file was created
            assert form_path.exists()
            assert len(content) > 500  # Should have substantial content
            
            # Load form back
            loaded_data = FormGenerator.load_form(form_path)
            
            # Verify structure
            assert "project" in loaded_data
            assert "timeline" in loaded_data
            assert "innovation" in loaded_data
            assert "methodology" in loaded_data
            assert "costs" in loaded_data
            
            # Verify project name
            assert loaded_data["project"]["name"] == "Test E2E Project"
    
    def test_form_validation(self):
        """Test form validation catches errors."""
        # Empty form should have errors
        empty_data = {}
        errors = FormGenerator.validate_form(empty_data)
        assert len(errors) > 0
        
        # Minimal valid form
        valid_data = {
            "project": {
                "name": "Test Project",
                "fiscal_year": 2025,
                "company": {
                    "name": "Test Company",
                    "nip": "1234567854"
                }
            },
            "timeline": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31"
            },
            "innovation": {
                "type": "product",
                "scale": "company",
                "description": "Test innovation"
            },
            "methodology": {
                "systematic": True,
                "creative": True,
                "innovative": True
            },
            "costs": {
                "personnel_employment": [
                    {
                        "name": "Jan Kowalski",
                        "role": "Developer",
                        "percentage": 100,
                        "gross_salary": 10000,
                        "months": 12
                    }
                ]
            }
        }
        errors = FormGenerator.validate_form(valid_data)
        assert len(errors) == 0


class TestValidationPipelineE2E:
    """E2E tests for validation pipeline."""
    
    @pytest.fixture
    def sample_project(self):
        """Create sample project for testing."""
        return ProjectInput(
            project=ProjectBasicInfo(
                name="E2E Test Project",
                code="E2E-001",
                fiscal_year=2025,
                company=CompanyInfo(
                    name="Test Company Sp. z o.o.",
                    nip="1234567854",
                ),
            ),
            timeline=ProjectTimeline(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                milestones=[
                    Milestone(
                        milestone_date=date(2025, 6, 30),
                        name="Phase 1",
                        description="First phase"
                    ),
                ],
            ),
            innovation=InnovationInfo(
                type=InnovationType.PRODUCT,
                scale=InnovationScale.COMPANY,
                description="Innovative E2E test project with machine learning and automation capabilities",
                novelty_aspects=["Novel aspect 1", "Novel aspect 2"],
            ),
            methodology=MethodologyInfo(
                systematic=True,
                creative=True,
                innovative=True,
                risk_factors=[
                    RiskFactor(
                        description="Technical risk",
                        probability="medium"
                    )
                ],
                research_methods=[
                    ResearchMethod(
                        name="Experimental method",
                        description="Testing various approaches"
                    )
                ],
            ),
            costs=ProjectCosts(
                personnel_employment=[
                    PersonnelEmploymentCost(
                        name="Jan Kowalski",
                        role="Developer",
                        percentage=100.0,
                        gross_salary=Decimal("12000"),
                        months=12,
                    )
                ],
            ),
            documentation=DocumentationConfig(),
        )
    
    @pytest.fixture
    def sample_document(self):
        """Sample markdown document for testing."""
        return """# Dokumentacja B+R: E2E Test Project

## Streszczenie wykonawcze

Projekt realizowany przez Test Company Sp. z o.o. (NIP: 1234567854).
Systematyczne i planowe podejście do realizacji projektu badawczo-rozwojowego.

## Opis projektu

Innowacyjny projekt wykorzystujący uczenie maszynowe. Twórczy charakter działalności
z nowatorskim podejściem do problemów. Projekt wprowadza przełomowe rozwiązania.

## Metodologia

Systematyczne podejście z wykorzystaniem metodologii Agile. Planowe działania
w harmonogramie. Kreatywne rozwiązywanie problemów.

## Innowacyjność

Projekt ma nowatorski charakter w skali firmy. Pionierskie rozwiązania techniczne.
Innowacja w zakresie automatyzacji procesów.

## Koszty B+R

### Wynagrodzenia

Jan Kowalski (Developer): 12 000 PLN × 12 miesięcy × 100% = 144 000 PLN
Stawka odliczenia: 200%
Kwota do odliczenia: 288 000 PLN

### Podsumowanie kosztów

Razem: 144 000 PLN
Koszty kwalifikowane do odliczenia: 288 000 PLN

Rok podatkowy: 2025

## Analiza ryzyka

Projekt wiąże się z ryzykiem i niepewnością badawczą. Wyzwania techniczne
obejmują niepewność co do skuteczności algorytmów.

## Wnioski

Projekt spełnia kryteria B+R zgodnie z art. 18d ustawy o CIT.
"""
    
    def test_validation_pipeline_runs(self, sample_project, sample_document):
        """Test that validation pipeline runs without errors."""
        pipeline = ValidationPipeline(config=None, use_llm=False)
        
        async def run_test():
            final_content, result = await pipeline.run(
                markdown_content=sample_document,
                project_input=sample_project,
                levels=["structure", "legal", "financial"],
                max_iterations=1
            )
            return final_content, result
        
        final_content, result = asyncio.run(run_test())
        
        # Should complete without errors
        assert result is not None
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
        assert len(result.validation_stages) > 0
        
        # Should return content
        assert final_content is not None
        assert len(final_content) > 0
    
    def test_validation_detects_issues(self, sample_project):
        """Test that validation detects issues in poor document."""
        poor_document = """# Document

This is a very short document with no B+R content.
"""
        pipeline = ValidationPipeline(config=None, use_llm=False)
        
        async def run_test():
            final_content, result = await pipeline.run(
                markdown_content=poor_document,
                project_input=sample_project,
                levels=["structure", "legal"],
                max_iterations=1
            )
            return final_content, result
        
        final_content, result = asyncio.run(run_test())
        
        # Should have issues
        total_issues = sum(len(stage.issues) for stage in result.validation_stages)
        assert total_issues > 0
        
        # Score should be lower
        assert result.quality_score < 1.0


class TestCLICommands:
    """Test CLI command execution (without actual LLM)."""
    
    def test_generate_form_command(self):
        """Test that generate-form command works."""
        import subprocess
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.yaml"
            
            result = subprocess.run(
                ["br-doc", "generate-form", "--name", "CLI Test", "--output", str(output_path)],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent.parent)
            )
            
            # Should succeed
            assert result.returncode == 0
            assert output_path.exists()
    
    def test_info_command(self):
        """Test that info command works."""
        import subprocess
        
        result = subprocess.run(
            ["br-doc", "info"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        # Should succeed
        assert result.returncode == 0
        assert "BR Documentation Generator" in result.stdout


class TestPDFRendering:
    """Test PDF rendering functionality."""
    
    def test_pdf_renderer_initialization(self):
        """Test that PDF renderer can be initialized."""
        renderer = PDFRenderer(
            template="professional",
            header="Test Header",
            footer="Test Footer"
        )
        
        assert renderer is not None
    
    def test_render_simple_markdown(self):
        """Test rendering simple markdown to PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            
            renderer = PDFRenderer(template="minimal")
            
            markdown_content = """# Test Document

## Section 1

This is a test paragraph.

## Section 2

- Item 1
- Item 2
- Item 3
"""
            
            result_path = renderer.render(
                markdown_content=markdown_content,
                output_path=str(output_path),
                metadata={"title": "Test"}
            )
            
            # Should create PDF
            assert Path(result_path).exists()
            assert Path(result_path).stat().st_size > 0


class TestCostCalculations:
    """Test cost calculation accuracy."""
    
    def test_personnel_employment_costs(self):
        """Test personnel employment cost calculations."""
        cost = PersonnelEmploymentCost(
            name="Test Employee",
            role="Developer",
            percentage=75.0,
            gross_salary=Decimal("20000"),
            months=10,
        )
        
        # Total: 20000 * 10 * 0.75 = 150000
        expected_total = Decimal("150000")
        assert abs(cost.total_cost - expected_total) < Decimal("0.01")
        
        # Deduction: 150000 * 2 = 300000
        expected_deduction = Decimal("300000")
        assert abs(cost.deduction_amount - expected_deduction) < Decimal("0.01")
    
    def test_project_costs_aggregation(self):
        """Test aggregation of all project costs."""
        costs = ProjectCosts(
            personnel_employment=[
                PersonnelEmploymentCost(
                    name="Employee 1",
                    role="Developer",
                    percentage=100.0,
                    gross_salary=Decimal("10000"),
                    months=12,
                ),
                PersonnelEmploymentCost(
                    name="Employee 2",
                    role="Designer",
                    percentage=50.0,
                    gross_salary=Decimal("8000"),
                    months=12,
                ),
            ],
            materials=[
                MaterialCost(
                    name="Equipment",
                    category=CostCategory.EQUIPMENT,
                    amount=Decimal("30000"),
                ),
            ],
        )
        
        # Personnel 1: 10000 * 12 * 1.0 = 120000
        # Personnel 2: 8000 * 12 * 0.5 = 48000
        # Materials: 30000
        # Total: 198000
        expected_total = Decimal("198000")
        assert abs(costs.total_costs - expected_total) < Decimal("0.01")
        
        # Deductions:
        # Personnel 1: 120000 * 2 = 240000
        # Personnel 2: 48000 * 2 = 96000
        # Materials: 30000 * 1 = 30000
        # Total: 366000
        expected_deduction = Decimal("366000")
        assert abs(costs.total_deduction - expected_deduction) < Decimal("0.01")


# Run with: pytest tests/test_e2e.py -v
