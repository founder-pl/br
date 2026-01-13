"""
BR Documentation Generator - Content Validator

Validates content quality and consistency using LLM.
"""

from __future__ import annotations

import structlog

from ..models import IssueSeverity, ValidationResult, ValidationStatus
from .base import BaseValidator, ValidationContext

logger = structlog.get_logger(__name__)


class ContentValidator(BaseValidator):
    """
    Validates documentation content quality.
    
    Uses LLM to check:
    - Content consistency and coherence
    - Technical accuracy
    - Language quality
    - Completeness of information
    - Data consistency between sections
    """
    
    @property
    def stage_name(self) -> str:
        return "content_validation"
    
    @property
    def validation_criteria(self) -> list[str]:
        return [
            "Content is coherent and well-structured",
            "Technical descriptions are accurate",
            "Data is consistent across sections",
            "Language is professional and clear",
            "All claims are supported with details",
            "Project goals align with described work",
            "Innovation aspects are clearly described",
            "Methodology is explained step-by-step",
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate content quality using LLM."""
        logger.info("Starting content validation", iteration=context.current_iteration)
        
        issues = []
        
        if self.use_llm:
            llm_issues = await self._llm_validate(context)
            issues.extend(llm_issues)
        
        # Basic consistency checks
        consistency_issues = self._check_data_consistency(context)
        issues.extend(consistency_issues)
        
        # Calculate score
        score = self.calculate_score_from_issues(issues)
        status = self.determine_status(score, issues)
        
        logger.info(
            "Content validation complete",
            score=score,
            status=status.value,
            issue_count=len(issues)
        )
        
        return self.create_result(
            status=status,
            score=score,
            issues=issues,
            metadata={
                "llm_validated": self.use_llm,
                "criteria_checked": len(self.validation_criteria),
            }
        )
    
    async def _llm_validate(self, context: ValidationContext) -> list:
        """Use LLM to validate content quality."""
        issues = []
        
        try:
            llm = await self.get_llm_client()
            
            # Build validation prompt with project context
            project_context = self._build_project_context(context.project_input)
            
            result = await llm.validate_content(
                content=context.markdown_content,
                validation_criteria=self.validation_criteria,
                context=project_context
            )
            
            # Parse LLM response into issues
            for llm_issue in result.get("issues", []):
                severity_map = {
                    "critical": IssueSeverity.CRITICAL,
                    "error": IssueSeverity.ERROR,
                    "warning": IssueSeverity.WARNING,
                    "info": IssueSeverity.INFO,
                }
                
                issues.append(self.create_issue(
                    issue_type=f"content_{llm_issue.get('criterion', 'quality')[:20]}",
                    severity=severity_map.get(
                        llm_issue.get("severity", "warning").lower(),
                        IssueSeverity.WARNING
                    ),
                    location=llm_issue.get("location", "document"),
                    message=llm_issue.get("message", "Issue detected"),
                    suggestion=llm_issue.get("suggestion")
                ))
                
        except Exception as e:
            logger.warning("LLM validation failed, using basic checks", error=str(e))
            issues.append(self.create_issue(
                issue_type="llm_validation_failed",
                severity=IssueSeverity.INFO,
                location="system",
                message=f"LLM validation unavailable: {str(e)[:100]}",
                suggestion="Proceeding with basic validation only"
            ))
        
        return issues
    
    def _build_project_context(self, project_input) -> str:
        """Build context string from project input."""
        return f"""
Project: {project_input.project.name}
Company: {project_input.project.company.name}
Fiscal Year: {project_input.project.fiscal_year}
Innovation Type: {project_input.innovation.type.value}
Innovation Scale: {project_input.innovation.scale.value}
Timeline: {project_input.timeline.start_date} to {project_input.timeline.end_date}
Total Costs: {project_input.costs.total_costs}
"""
    
    def _check_data_consistency(self, context: ValidationContext) -> list:
        """Check consistency between document and project input."""
        issues = []
        content = context.markdown_content.lower()
        project = context.project_input
        
        # Check company name appears
        company_name = project.project.company.name.lower()
        if company_name not in content:
            issues.append(self.create_issue(
                issue_type="missing_company_name",
                severity=IssueSeverity.ERROR,
                location="document",
                message="Nazwa firmy nie występuje w dokumencie",
                suggestion=f"Dodaj nazwę firmy '{project.project.company.name}' do dokumentu"
            ))
        
        # Check project name appears
        project_name = project.project.name.lower()
        if project_name not in content:
            issues.append(self.create_issue(
                issue_type="missing_project_name",
                severity=IssueSeverity.WARNING,
                location="document",
                message="Nazwa projektu nie występuje w dokumencie",
                suggestion=f"Dodaj nazwę projektu '{project.project.name}'"
            ))
        
        # Check fiscal year is mentioned
        fiscal_year = str(project.project.fiscal_year)
        if fiscal_year not in context.markdown_content:
            issues.append(self.create_issue(
                issue_type="missing_fiscal_year",
                severity=IssueSeverity.WARNING,
                location="document",
                message="Rok podatkowy nie występuje w dokumencie",
                suggestion=f"Dodaj rok podatkowy: {fiscal_year}"
            ))
        
        # Check innovation keywords based on type
        innovation_keywords = {
            "product": ["produkt", "rozwiązanie", "system"],
            "process": ["proces", "metoda", "procedura"],
            "mixed": ["produkt", "proces", "rozwiązanie"],
        }
        
        keywords = innovation_keywords.get(project.innovation.type.value, [])
        found_keywords = sum(1 for kw in keywords if kw in content)
        
        if found_keywords == 0:
            issues.append(self.create_issue(
                issue_type="innovation_type_mismatch",
                severity=IssueSeverity.WARNING,
                location="section:innovation",
                message=f"Brak słów kluczowych dla innowacji typu '{project.innovation.type.value}'",
                suggestion=f"Użyj terminologii związanej z innowacją: {', '.join(keywords)}"
            ))
        
        return issues
    
    def _get_correction_instructions(self) -> str:
        return """Improve content quality:
1. Ensure consistency with project data
2. Use professional, technical language
3. Provide specific details and examples
4. Ensure all sections are complete
5. Check data consistency between sections
Maintain the document structure while improving content quality."""
