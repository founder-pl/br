"""
Base classes for validation pipeline.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from br_core.types import ValidationIssue, ValidationResult, ValidationSeverity


class ValidationStage(str, Enum):
    """Stages of validation pipeline"""
    STRUCTURE = "structure"
    LEGAL = "legal"
    FINANCIAL = "financial"
    LLM_REVIEW = "llm_review"
    FINAL = "final"


@dataclass
class ValidationContext:
    """Context passed through validation pipeline"""
    document_type: str
    content: str
    project_id: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Validation state
    current_stage: ValidationStage = ValidationStage.STRUCTURE
    all_issues: List[ValidationIssue] = field(default_factory=list)
    stage_results: Dict[str, ValidationResult] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue"""
        self.all_issues.append(issue)
    
    def add_issues(self, issues: List[ValidationIssue]):
        """Add multiple validation issues"""
        self.all_issues.extend(issues)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any blocking errors"""
        return any(i.severity == ValidationSeverity.ERROR for i in self.all_issues)
    
    @property
    def error_count(self) -> int:
        """Count of errors"""
        return sum(1 for i in self.all_issues if i.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warnings"""
        return sum(1 for i in self.all_issues if i.severity == ValidationSeverity.WARNING)
    
    def get_stage_result(self, stage: ValidationStage) -> Optional[ValidationResult]:
        """Get result for a specific stage"""
        return self.stage_results.get(stage.value)
    
    def set_stage_result(self, stage: ValidationStage, result: ValidationResult):
        """Set result for a stage"""
        self.stage_results[stage.value] = result


class BaseValidator(ABC):
    """Abstract base class for validators"""
    
    stage: ValidationStage = ValidationStage.STRUCTURE
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Validate the document content.
        
        Args:
            context: Validation context with document and metadata
            
        Returns:
            ValidationResult with issues found
        """
        pass
    
    def create_issue(
        self,
        severity: ValidationSeverity,
        message: str,
        code: str = "",
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> ValidationIssue:
        """Helper to create validation issue"""
        return ValidationIssue(
            severity=severity,
            message=message,
            code=code,
            location=location,
            suggestion=suggestion,
        )
    
    def error(self, message: str, code: str = "", **kwargs) -> ValidationIssue:
        """Create error issue"""
        return self.create_issue(ValidationSeverity.ERROR, message, code, **kwargs)
    
    def warning(self, message: str, code: str = "", **kwargs) -> ValidationIssue:
        """Create warning issue"""
        return self.create_issue(ValidationSeverity.WARNING, message, code, **kwargs)
    
    def info(self, message: str, code: str = "", **kwargs) -> ValidationIssue:
        """Create info issue"""
        return self.create_issue(ValidationSeverity.INFO, message, code, **kwargs)
