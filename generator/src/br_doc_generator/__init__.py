"""
BR Documentation Generator

A Python library for generating Polish B+R (R&D) tax relief documentation
using LLM with multi-level validation pipeline.

Features:
- Automatic documentation generation via LiteLLM
- Multi-level validation (structure, content, legal, financial)
- YAML form generation for easy input
- Markdown to PDF rendering
- Integration with OpenRouter and local LLM via Ollama

Usage:
    from br_doc_generator import BRDocumentationPipeline, FormGenerator
    
    # Generate input form
    form_gen = FormGenerator()
    form_gen.generate_empty_form("project_form.yaml")
    
    # Generate documentation
    pipeline = BRDocumentationPipeline.from_env()
    result = await pipeline.generate("project_form.yaml")
"""

from .config import (
    AppConfig,
    LLMConfig,
    ValidationConfig,
    PDFConfig,
    load_config,
)

from .models import (
    ProjectInput,
    CompanyInfo,
    Timeline,
    Milestone,
    Innovation,
    Methodology,
    ProjectCosts,
    PersonnelEmploymentCost,
    PersonnelCivilCost,
    MaterialCost,
    ExternalServiceCost,
    ValidationResult,
    ValidationIssue,
    PipelineResult,
    InnovationType,
    InnovationScale,
    CostCategory,
    ValidationStatus,
)

from .llm_client import LLMClient

from .validators import (
    BaseValidator,
    ValidationContext,
    StructureValidator,
    ContentValidator,
    LegalComplianceValidator,
    FinancialValidator,
    ValidationPipeline,
)

from .generators import (
    DocumentGenerator,
    FormGenerator,
    PDFRenderer,
    render_documentation_to_pdf,
)


class BRDocumentationPipeline:
    """
    High-level pipeline for generating B+R documentation.
    
    Combines form loading, document generation, validation,
    and PDF rendering into a single workflow.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize pipeline with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.llm_client = LLMClient(config.llm)
        self.document_generator = DocumentGenerator(self.llm_client, config)
        self.validation_pipeline = ValidationPipeline(self.llm_client, config.validation)
        self.pdf_renderer = PDFRenderer(
            template=config.pdf.template,
            company_logo=config.pdf.company_logo,
            header=config.pdf.header_text,
            footer=config.pdf.footer_text
        )
    
    @classmethod
    def from_env(cls, env_path: str = ".env") -> "BRDocumentationPipeline":
        """
        Create pipeline from environment configuration.
        
        Args:
            env_path: Path to .env file
        
        Returns:
            Configured pipeline instance
        """
        config = load_config(env_path)
        return cls(config)
    
    async def generate(
        self,
        form_path: str,
        output_dir: str = "./output",
        validation_levels: list = None,
        max_iterations: int = 3,
        output_format: str = "pdf"
    ) -> PipelineResult:
        """
        Generate B+R documentation from YAML form.
        
        Args:
            form_path: Path to YAML form file
            output_dir: Output directory
            validation_levels: List of validation levels to apply
            max_iterations: Maximum iterations per validation stage
            output_format: Output format (pdf, md, both)
        
        Returns:
            Pipeline result with status and output paths
        """
        import os
        from pathlib import Path
        
        # Load and validate form
        project_data = FormGenerator.load_form(form_path)
        form_errors = FormGenerator.validate_form(project_data)
        
        if form_errors:
            return PipelineResult(
                status=ValidationStatus.FAILED,
                quality_score=0.0,
                iterations=0,
                validation_results=[],
                errors=form_errors,
                output_path=None,
                markdown_content=None
            )
        
        # Create ProjectInput from form data
        project_input = self._form_to_project_input(project_data)
        
        # Generate documentation
        markdown_content = await self.document_generator.generate_full_documentation(
            project_input
        )
        
        # Run validation pipeline
        validation_levels = validation_levels or self.config.validation.levels
        
        final_content, pipeline_result = await self.validation_pipeline.run(
            markdown_content,
            project_input,
            validation_levels,
            max_iterations
        )
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save markdown
        md_path = output_path / "documentation.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        # Generate PDF if requested
        pdf_path = None
        if output_format in ("pdf", "both"):
            pdf_path = output_path / "documentation.pdf"
            await self.pdf_renderer.render_async(
                final_content,
                str(pdf_path),
                metadata={
                    "title": f"Dokumentacja B+R: {project_input.name}",
                    "company_name": project_input.company.name,
                    "fiscal_year": project_input.fiscal_year
                }
            )
        
        # Update result with output paths
        pipeline_result.output_path = str(pdf_path or md_path)
        pipeline_result.markdown_content = final_content
        
        return pipeline_result
    
    def _form_to_project_input(self, form_data: dict) -> ProjectInput:
        """Convert form data dictionary to ProjectInput model."""
        from datetime import date
        from decimal import Decimal
        
        project = form_data.get("project", {})
        timeline = form_data.get("timeline", {})
        innovation = form_data.get("innovation", {})
        methodology = form_data.get("methodology", {})
        costs = form_data.get("costs", {})
        
        # Parse company info
        company_data = project.get("company", {})
        company = CompanyInfo(
            name=company_data.get("name", ""),
            nip=company_data.get("nip", ""),
            regon=company_data.get("regon", ""),
            address=company_data.get("address", ""),
            krs=company_data.get("krs")
        )
        
        # Parse timeline
        milestones = []
        for m in timeline.get("milestones", []):
            milestones.append(Milestone(
                date=date.fromisoformat(m.get("date", "")),
                name=m.get("name", ""),
                deliverables=m.get("deliverables", [])
            ))
        
        timeline_obj = Timeline(
            start_date=date.fromisoformat(timeline.get("start_date", "")),
            end_date=date.fromisoformat(timeline.get("end_date", "")),
            milestones=milestones
        )
        
        # Parse innovation
        innovation_obj = Innovation(
            type=InnovationType(innovation.get("type", "product")),
            scale=InnovationScale(innovation.get("scale", "company")),
            description=innovation.get("description", ""),
            novelty_aspects=innovation.get("novelty_aspects", [])
        )
        
        # Parse methodology
        methodology_obj = Methodology(
            systematic=methodology.get("systematic", True),
            creative=methodology.get("creative", True),
            innovative=methodology.get("innovative", True),
            risk_factors=methodology.get("risk_factors", []),
            research_methods=methodology.get("research_methods", [])
        )
        
        # Parse costs
        personnel_employment = []
        for p in costs.get("personnel", {}).get("employment", []):
            personnel_employment.append(PersonnelEmploymentCost(
                name=p.get("name", ""),
                role=p.get("role", ""),
                percentage=p.get("percentage", 100),
                gross_salary=Decimal(str(p.get("gross_salary", 0))),
                months=p.get("months", 12)
            ))
        
        personnel_civil = []
        for p in costs.get("personnel", {}).get("civil_contracts", []):
            personnel_civil.append(PersonnelCivilCost(
                name=p.get("name", ""),
                role=p.get("role", ""),
                contract_type=p.get("contract_type", "UoD"),
                amount=Decimal(str(p.get("amount", 0)))
            ))
        
        materials = []
        for m in costs.get("materials", []):
            materials.append(MaterialCost(
                name=m.get("name", ""),
                category=m.get("category", "materials"),
                amount=Decimal(str(m.get("amount", 0))),
                description=m.get("description", "")
            ))
        
        external_services = []
        for s in costs.get("external_services", []):
            external_services.append(ExternalServiceCost(
                name=s.get("name", ""),
                provider=s.get("provider", ""),
                amount=Decimal(str(s.get("amount", 0))),
                description=s.get("description", "")
            ))
        
        costs_obj = ProjectCosts(
            personnel_employment=personnel_employment,
            personnel_civil=personnel_civil,
            materials=materials,
            external_services=external_services
        )
        
        return ProjectInput(
            name=project.get("name", ""),
            code=project.get("code", ""),
            fiscal_year=project.get("fiscal_year", date.today().year),
            company=company,
            timeline=timeline_obj,
            innovation=innovation_obj,
            methodology=methodology_obj,
            costs=costs_obj
        )
    
    def load_form(self, form_path: str) -> dict:
        """Load YAML form file."""
        return FormGenerator.load_form(form_path)
    
    def save_validation_report(self, result: PipelineResult, output_path: str):
        """Save validation report to YAML file."""
        import yaml
        from datetime import datetime
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "status": result.status.value,
            "quality_score": float(result.quality_score),
            "iterations": result.iterations,
            "errors": result.errors,
            "validation_results": []
        }
        
        for vr in result.validation_results:
            report["validation_results"].append({
                "stage": vr.stage,
                "status": vr.status.value,
                "score": float(vr.score),
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity,
                        "message": i.message,
                        "location": i.location,
                        "suggestion": i.suggestion
                    }
                    for i in vr.issues
                ],
                "corrections": vr.corrections
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(report, f, allow_unicode=True, default_flow_style=False)


__version__ = "0.1.0"
__author__ = "Softreck"
__all__ = [
    # Config
    "AppConfig",
    "LLMConfig", 
    "ValidationConfig",
    "PDFConfig",
    "load_config",
    
    # Models
    "ProjectInput",
    "CompanyInfo",
    "Timeline",
    "Milestone",
    "Innovation",
    "Methodology",
    "ProjectCosts",
    "PersonnelEmploymentCost",
    "PersonnelCivilCost",
    "MaterialCost",
    "ExternalServiceCost",
    "ValidationResult",
    "ValidationIssue",
    "PipelineResult",
    "InnovationType",
    "InnovationScale",
    "CostCategory",
    "ValidationStatus",
    
    # LLM Client
    "LLMClient",
    
    # Validators
    "BaseValidator",
    "ValidationContext",
    "StructureValidator",
    "ContentValidator",
    "LegalComplianceValidator",
    "FinancialValidator",
    "ValidationPipeline",
    
    # Generators
    "DocumentGenerator",
    "FormGenerator",
    "PDFRenderer",
    "render_documentation_to_pdf",
    
    # Pipeline
    "BRDocumentationPipeline",
]
