"""
BR Documentation Generator - Base Validator

Abstract base class for all validators in the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

from ..models import (
    CorrectionApplied,
    IssueSeverity,
    ProjectInput,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)

logger = structlog.get_logger(__name__)


@dataclass
class ValidationContext:
    """Context passed through validation pipeline."""
    
    project_input: ProjectInput
    markdown_content: str
    current_iteration: int = 0
    max_iterations: int = 3
    previous_results: list[ValidationResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: ValidationResult) -> None:
        """Add validation result to context."""
        self.previous_results.append(result)
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if any previous result has critical issues."""
        return any(r.has_critical_issues for r in self.previous_results)
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score."""
        if not self.previous_results:
            return 0.0
        return sum(r.score for r in self.previous_results) / len(self.previous_results)


class BaseValidator(ABC):
    """
    Abstract base class for validators.
    
    Each validator performs a specific type of validation on the documentation
    and can optionally trigger auto-corrections via LLM.
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize validator.
        
        Args:
            use_llm: Whether to use LLM for validation and corrections
        """
        self.use_llm = use_llm
        self._llm_client = None
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of this validation stage."""
        pass
    
    @property
    @abstractmethod
    def validation_criteria(self) -> list[str]:
        """List of criteria this validator checks."""
        pass
    
    async def get_llm_client(self):
        """Get LLM client for validation."""
        if self._llm_client is None:
            from ..llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client
    
    @abstractmethod
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Perform validation on the content.
        
        Args:
            context: Validation context with project and content
            
        Returns:
            Validation result with score and issues
        """
        pass
    
    async def auto_correct(
        self,
        context: ValidationContext,
        issues: list[ValidationIssue]
    ) -> tuple[str, list[CorrectionApplied]]:
        """
        Attempt to auto-correct identified issues.
        
        Args:
            context: Validation context
            issues: Issues to correct
            
        Returns:
            Tuple of (corrected content, list of corrections applied)
        """
        if not self.use_llm or not issues:
            return context.markdown_content, []
        
        correctable_issues = [
            i for i in issues 
            if i.severity in [IssueSeverity.WARNING, IssueSeverity.ERROR]
        ]
        
        if not correctable_issues:
            return context.markdown_content, []
        
        logger.info(
            "Attempting auto-correction",
            stage=self.stage_name,
            issue_count=len(correctable_issues)
        )
        
        try:
            llm = await self.get_llm_client()
            corrected_content = await llm.improve_content(
                content=context.markdown_content,
                issues=[i.model_dump() for i in correctable_issues],
                instructions=self._get_correction_instructions()
            )
            
            corrections = [
                CorrectionApplied(
                    location=issue.location,
                    original="[content before correction]",
                    corrected="[content after correction]",
                    reason=issue.message
                )
                for issue in correctable_issues
            ]
            
            return corrected_content, corrections
            
        except Exception as e:
            logger.error("Auto-correction failed", error=str(e))
            return context.markdown_content, []
    
    def _get_correction_instructions(self) -> str:
        """Get stage-specific correction instructions."""
        return f"Focus on {self.stage_name} improvements."
    
    def create_result(
        self,
        status: ValidationStatus,
        score: float,
        issues: list[ValidationIssue],
        corrections: Optional[list[CorrectionApplied]] = None,
        metadata: Optional[dict] = None
    ) -> ValidationResult:
        """Create validation result."""
        return ValidationResult(
            stage=self.stage_name,
            timestamp=datetime.utcnow(),
            status=status,
            score=score,
            issues=issues,
            corrections_applied=corrections or [],
            metadata=metadata or {}
        )
    
    def create_issue(
        self,
        issue_type: str,
        severity: IssueSeverity,
        location: str,
        message: str,
        suggestion: Optional[str] = None
    ) -> ValidationIssue:
        """Helper to create validation issue."""
        return ValidationIssue(
            type=issue_type,
            severity=severity,
            location=location,
            message=message,
            suggestion=suggestion
        )
    
    @staticmethod
    def calculate_score_from_issues(issues: list[ValidationIssue]) -> float:
        """Calculate quality score based on issues."""
        if not issues:
            return 1.0
        
        # Weight by severity
        weights = {
            IssueSeverity.CRITICAL: 0.4,
            IssueSeverity.ERROR: 0.2,
            IssueSeverity.WARNING: 0.1,
            IssueSeverity.INFO: 0.02,
        }
        
        penalty = sum(weights.get(i.severity, 0) for i in issues)
        return max(0.0, 1.0 - penalty)
    
    @staticmethod
    def determine_status(score: float, issues: list[ValidationIssue]) -> ValidationStatus:
        """Determine validation status from score and issues."""
        has_critical = any(i.severity == IssueSeverity.CRITICAL for i in issues)
        
        if has_critical or score < 0.5:
            return ValidationStatus.FAILED
        elif score < 0.8:
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.PASSED
