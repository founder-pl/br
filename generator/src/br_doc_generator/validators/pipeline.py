"""
BR Documentation Generator - Validation Pipeline

Orchestrates multi-level validation with iterative refinement.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import structlog

from ..config import ValidationConfig, ValidationLevel, get_config
from ..models import (
    PipelineResult,
    ProjectInput,
    ValidationResult,
    ValidationStatus,
)
from .base import BaseValidator, ValidationContext
from .content import ContentValidator
from .financial import FinancialValidator
from .legal import LegalComplianceValidator
from .structure import StructureValidator

logger = structlog.get_logger(__name__)


class ValidationPipeline:
    """
    Multi-level validation pipeline with iterative refinement.
    
    Orchestrates validators in sequence:
    1. Structure validation (markdown, sections)
    2. Content validation (quality, consistency)
    3. Legal compliance validation (B+R requirements)
    4. Financial validation (cost calculations)
    
    Each stage can trigger auto-corrections and re-validation.
    """
    
    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        use_llm: bool = True
    ):
        """
        Initialize validation pipeline.
        
        Args:
            config: Validation configuration
            use_llm: Whether to use LLM for validation and corrections
        """
        self.config = config or get_config().validation
        self.use_llm = use_llm
        
        # Initialize validators
        self.validators: dict[ValidationLevel, BaseValidator] = {
            ValidationLevel.STRUCTURE: StructureValidator(use_llm=use_llm),
            ValidationLevel.CONTENT: ContentValidator(use_llm=use_llm),
            ValidationLevel.LEGAL: LegalComplianceValidator(use_llm=use_llm),
            ValidationLevel.FINANCIAL: FinancialValidator(use_llm=use_llm),
        }
    
    async def validate(
        self,
        project_input: ProjectInput,
        markdown_content: str,
        levels: Optional[list[ValidationLevel]] = None,
        max_iterations: Optional[int] = None,
    ) -> PipelineResult:
        """
        Run validation pipeline on documentation.
        
        Args:
            project_input: Project data
            markdown_content: Generated markdown documentation
            levels: Specific validation levels to run (default: all configured)
            max_iterations: Maximum correction iterations per stage
            
        Returns:
            Pipeline result with validation details
        """
        start_time = datetime.utcnow()
        
        levels = levels or self.config.levels
        max_iterations = max_iterations or self.config.max_iterations
        
        logger.info(
            "Starting validation pipeline",
            levels=[l.value for l in levels],
            max_iterations=max_iterations
        )
        
        # Create validation context
        context = ValidationContext(
            project_input=project_input,
            markdown_content=markdown_content,
            max_iterations=max_iterations
        )
        
        all_results: list[ValidationResult] = []
        total_iterations = 0
        errors: list[str] = []
        
        # Run each validation level
        for level in levels:
            validator = self.validators.get(level)
            if not validator:
                logger.warning(f"No validator for level: {level.value}")
                continue
            
            logger.info(f"Starting validation level: {level.value}")
            
            # Run validation with potential iterations
            level_results, iterations, level_errors = await self._run_validation_level(
                validator=validator,
                context=context,
                max_iterations=max_iterations
            )
            
            all_results.extend(level_results)
            total_iterations += iterations
            errors.extend(level_errors)
            
            # Update context with results
            for result in level_results:
                context.add_result(result)
            
            # Check for critical failures
            if any(r.has_critical_issues for r in level_results):
                logger.warning(
                    "Critical issues found, continuing with next level",
                    level=level.value
                )
        
        # Calculate final results
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_results)
        overall_score = self._calculate_overall_score(all_results)
        
        logger.info(
            "Validation pipeline complete",
            status=overall_status.value,
            score=overall_score,
            total_iterations=total_iterations,
            duration_seconds=duration
        )
        
        return PipelineResult(
            status=overall_status,
            quality_score=overall_score,
            validation_stages=all_results,
            markdown_content=context.markdown_content,
            generation_time_seconds=duration,
            iterations_used=total_iterations,
            errors=errors
        )
    
    async def _run_validation_level(
        self,
        validator: BaseValidator,
        context: ValidationContext,
        max_iterations: int
    ) -> tuple[list[ValidationResult], int, list[str]]:
        """
        Run single validation level with potential iterations.
        
        Returns:
            Tuple of (results, iterations_used, errors)
        """
        results: list[ValidationResult] = []
        errors: list[str] = []
        iterations = 0
        
        for iteration in range(max_iterations):
            context.current_iteration = iteration
            iterations += 1
            
            try:
                # Run validation
                result = await validator.validate(context)
                results.append(result)
                
                # Check if passed or no correctable issues
                if result.status == ValidationStatus.PASSED:
                    logger.info(
                        f"Validation passed on iteration {iteration + 1}",
                        stage=validator.stage_name
                    )
                    break
                
                # Check if we should attempt correction
                if iteration < max_iterations - 1 and not result.has_critical_issues:
                    # Attempt auto-correction
                    correctable_issues = [
                        i for i in result.issues
                        if i.severity.value in ["warning", "error"]
                    ]
                    
                    if correctable_issues:
                        logger.info(
                            "Attempting auto-correction",
                            stage=validator.stage_name,
                            iteration=iteration + 1,
                            issue_count=len(correctable_issues)
                        )
                        
                        corrected_content, corrections = await validator.auto_correct(
                            context=context,
                            issues=correctable_issues
                        )
                        
                        if corrections:
                            context.markdown_content = corrected_content
                            result.corrections_applied.extend(corrections)
                            logger.info(
                                "Corrections applied",
                                count=len(corrections)
                            )
                        else:
                            # No corrections made, stop iteration
                            logger.info("No corrections could be made")
                            break
                    else:
                        # No correctable issues
                        break
                else:
                    # Max iterations reached or critical issues
                    break
                    
            except Exception as e:
                error_msg = f"Validation error in {validator.stage_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                break
        
        return results, iterations, errors
    
    def _determine_overall_status(self, results: list[ValidationResult]) -> ValidationStatus:
        """Determine overall pipeline status from all results."""
        if not results:
            return ValidationStatus.FAILED
        
        # Get final result from each stage
        stage_final_results = {}
        for result in results:
            stage_final_results[result.stage] = result
        
        final_results = list(stage_final_results.values())
        
        # Check for any critical failures
        if any(r.has_critical_issues for r in final_results):
            return ValidationStatus.FAILED
        
        # Check for any failed stages
        if any(r.status == ValidationStatus.FAILED for r in final_results):
            return ValidationStatus.FAILED
        
        # Check for warnings
        if any(r.status == ValidationStatus.WARNING for r in final_results):
            return ValidationStatus.WARNING
        
        return ValidationStatus.PASSED
    
    def _calculate_overall_score(self, results: list[ValidationResult]) -> float:
        """Calculate weighted overall score."""
        if not results:
            return 0.0
        
        # Get final result from each stage
        stage_final_results = {}
        for result in results:
            stage_final_results[result.stage] = result
        
        final_results = list(stage_final_results.values())
        
        # Weight by validation level importance
        weights = {
            "structure_validation": 0.2,
            "content_validation": 0.3,
            "legal_compliance_validation": 0.3,
            "financial_validation": 0.2,
        }
        
        total_weight = 0
        weighted_score = 0
        
        for result in final_results:
            weight = weights.get(result.stage, 0.25)
            weighted_score += result.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return sum(r.score for r in final_results) / len(final_results)
        
        return weighted_score / total_weight
    
    async def validate_single_level(
        self,
        project_input: ProjectInput,
        markdown_content: str,
        level: ValidationLevel
    ) -> ValidationResult:
        """
        Run single validation level without iteration.
        
        Useful for quick checks or debugging.
        """
        validator = self.validators.get(level)
        if not validator:
            raise ValueError(f"Unknown validation level: {level}")
        
        context = ValidationContext(
            project_input=project_input,
            markdown_content=markdown_content,
            max_iterations=1
        )
        
        return await validator.validate(context)
