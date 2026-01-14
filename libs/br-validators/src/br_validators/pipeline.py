"""
Validation pipeline orchestration.
"""
from typing import Any, Dict, List, Optional
import structlog

from br_core.types import ValidationResult, ValidationSeverity, ValidationIssue

from .base import BaseValidator, ValidationContext, ValidationStage
from .structure import StructureValidator
from .legal import LegalValidator
from .financial import FinancialValidator

logger = structlog.get_logger()


class ValidationPipeline:
    """
    Orchestrates multi-stage validation of B+R documents.
    
    Pipeline stages:
    1. Structure validation (required sections, formatting)
    2. Legal compliance (NIP, B+R categories, legal references)
    3. Financial validation (amounts, Nexus, calculations)
    4. LLM review (optional, content quality)
    """
    
    def __init__(
        self,
        validators: Optional[List[BaseValidator]] = None,
        stop_on_error: bool = False,
    ):
        """
        Initialize validation pipeline.
        
        Args:
            validators: List of validators to run (in order)
            stop_on_error: Whether to stop pipeline on first error
        """
        self.validators = validators or []
        self.stop_on_error = stop_on_error
    
    def add_validator(self, validator: BaseValidator):
        """Add a validator to the pipeline"""
        self.validators.append(validator)
    
    async def validate(
        self,
        content: str,
        document_type: str,
        project_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run full validation pipeline.
        
        Args:
            content: Document content to validate
            document_type: Type of document (project_card, expense_registry, etc.)
            project_id: Optional project ID
            year: Optional fiscal year
            month: Optional month
            metadata: Optional metadata dict
            data: Optional data dict (source data for validation)
            
        Returns:
            Dict with validation results
        """
        context = ValidationContext(
            document_type=document_type,
            content=content,
            project_id=project_id,
            year=year,
            month=month,
            metadata=metadata or {},
            data=data or {},
        )
        
        logger.info(
            "validation_started",
            document_type=document_type,
            content_length=len(content),
            validator_count=len(self.validators),
        )
        
        results = {}
        
        for validator in self.validators:
            context.current_stage = validator.stage
            
            try:
                result = await validator.validate(context)
                results[validator.stage.value] = result.to_dict()
                
                logger.info(
                    "validation_stage_complete",
                    stage=validator.stage.value,
                    valid=result.valid,
                    issue_count=len(result.issues),
                    score=result.score,
                )
                
                if self.stop_on_error and not result.valid:
                    logger.warning(
                        "validation_stopped",
                        stage=validator.stage.value,
                        reason="errors_found",
                    )
                    break
                    
            except Exception as e:
                logger.error(
                    "validation_error",
                    stage=validator.stage.value,
                    error=str(e),
                )
                results[validator.stage.value] = {
                    "valid": False,
                    "error": str(e),
                    "issues": [],
                }
                
                if self.stop_on_error:
                    break
        
        # Calculate overall result
        all_valid = all(r.get("valid", False) for r in results.values())
        total_issues = context.all_issues
        
        error_count = sum(1 for i in total_issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in total_issues if i.severity == ValidationSeverity.WARNING)
        
        # Overall score
        overall_score = sum(r.get("score", 0) for r in results.values()) / max(len(results), 1)
        
        return {
            "valid": all_valid,
            "overall_score": round(overall_score, 4),
            "error_count": error_count,
            "warning_count": warning_count,
            "stages": results,
            "all_issues": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "code": i.code,
                    "location": i.location,
                    "suggestion": i.suggestion,
                }
                for i in total_issues
            ],
            "document_type": document_type,
            "content_length": len(content),
        }
    
    async def validate_quick(self, content: str, document_type: str) -> bool:
        """
        Quick validation - just check if document passes basic validation.
        
        Returns:
            True if document is valid, False otherwise
        """
        result = await self.validate(content, document_type)
        return result["valid"]


def create_default_pipeline(
    include_llm: bool = False,
    stop_on_error: bool = False,
) -> ValidationPipeline:
    """
    Create default validation pipeline.
    
    Args:
        include_llm: Whether to include LLM review stage
        stop_on_error: Whether to stop on first error
        
    Returns:
        Configured ValidationPipeline
    """
    validators = [
        StructureValidator(),
        LegalValidator(),
        FinancialValidator(),
    ]
    
    # LLM validator would be added here if include_llm=True
    # Currently not implemented - would require litellm dependency
    
    return ValidationPipeline(validators=validators, stop_on_error=stop_on_error)
