"""
BR Documentation Generator - Financial Validator

Validates cost calculations and financial data consistency.
"""

from __future__ import annotations

import re
from decimal import Decimal

import structlog

from ..models import IssueSeverity, ValidationResult, ValidationStatus
from .base import BaseValidator, ValidationContext

logger = structlog.get_logger(__name__)


# B+R deduction rates according to Polish tax law
DEDUCTION_RATES = {
    "personnel_employment": Decimal("2.0"),    # 200% for employees
    "personnel_civil": Decimal("2.0"),         # 200% for civil contracts
    "materials": Decimal("1.0"),               # 100% for materials
    "equipment": Decimal("1.0"),               # 100% for equipment
    "expertise": Decimal("1.0"),               # 100% for expertise
    "external_research": Decimal("1.0"),       # 100% for research services
    "depreciation": Decimal("1.0"),            # 100% for depreciation
}


class FinancialValidator(BaseValidator):
    """
    Validates financial calculations and cost data.
    
    Checks:
    - Cost totals match item sums
    - Deduction calculations are correct
    - Financial data in document matches input
    - Currency consistency
    - Reasonable cost ranges
    """
    
    @property
    def stage_name(self) -> str:
        return "financial_validation"
    
    @property
    def validation_criteria(self) -> list[str]:
        return [
            "Cost totals are mathematically correct",
            "Deduction amounts use correct rates",
            "Personnel costs include proper percentages",
            "Financial data matches project input",
            "All amounts use consistent currency",
            "Cost breakdown is complete",
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate financial calculations."""
        logger.info("Starting financial validation", iteration=context.current_iteration)
        
        issues = []
        project = context.project_input
        content = context.markdown_content
        
        # Validate cost totals from input
        total_issues = self._validate_cost_totals(project.costs)
        issues.extend(total_issues)
        
        # Validate deduction calculations
        deduction_issues = self._validate_deductions(project.costs)
        issues.extend(deduction_issues)
        
        # Check financial data in document
        doc_issues = self._check_document_amounts(content, project.costs)
        issues.extend(doc_issues)
        
        # Check personnel percentage allocations
        personnel_issues = self._check_personnel_allocations(project.costs)
        issues.extend(personnel_issues)
        
        # Calculate score
        score = self.calculate_score_from_issues(issues)
        status = self.determine_status(score, issues)
        
        logger.info(
            "Financial validation complete",
            score=score,
            status=status.value,
            issue_count=len(issues)
        )
        
        return self.create_result(
            status=status,
            score=score,
            issues=issues,
            metadata={
                "total_costs": float(project.costs.total_costs),
                "total_deduction": float(project.costs.total_deduction),
                "personnel_employment_count": len(project.costs.personnel_employment),
                "personnel_civil_count": len(project.costs.personnel_civil),
            }
        )
    
    def _validate_cost_totals(self, costs) -> list:
        """Validate that cost totals are correct."""
        issues = []
        
        # Verify total costs calculation
        calculated_total = (
            costs.total_personnel_employment +
            costs.total_personnel_civil +
            costs.total_materials +
            costs.total_external_services
        )
        
        if calculated_total != costs.total_costs:
            issues.append(self.create_issue(
                issue_type="cost_total_mismatch",
                severity=IssueSeverity.CRITICAL,
                location="costs:total",
                message=f"Suma kosztów ({costs.total_costs}) nie zgadza się z kalkulacją ({calculated_total})",
                suggestion="Sprawdź sumowanie poszczególnych kategorii kosztów"
            ))
        
        # Check for zero or negative costs
        if costs.total_costs <= 0:
            issues.append(self.create_issue(
                issue_type="invalid_total_costs",
                severity=IssueSeverity.CRITICAL,
                location="costs:total",
                message="Suma kosztów musi być większa od zera",
                suggestion="Dodaj koszty kwalifikowane do projektu"
            ))
        
        return issues
    
    def _validate_deductions(self, costs) -> list:
        """Validate deduction calculations."""
        issues = []
        
        # Check personnel employment deductions (200%)
        for employee in costs.personnel_employment:
            expected_deduction = employee.total_cost * DEDUCTION_RATES["personnel_employment"]
            if employee.deduction_amount != expected_deduction:
                issues.append(self.create_issue(
                    issue_type="deduction_calculation",
                    severity=IssueSeverity.ERROR,
                    location=f"costs:personnel:{employee.name}",
                    message=f"Niepoprawna kalkulacja odliczenia dla {employee.name}",
                    suggestion=f"Oczekiwana kwota: {expected_deduction} (200% od kosztu kwalifikowanego)"
                ))
        
        # Check personnel civil deductions (200%)
        for contractor in costs.personnel_civil:
            expected_deduction = contractor.amount * DEDUCTION_RATES["personnel_civil"]
            if contractor.deduction_amount != expected_deduction:
                issues.append(self.create_issue(
                    issue_type="deduction_calculation",
                    severity=IssueSeverity.ERROR,
                    location=f"costs:civil:{contractor.name}",
                    message=f"Niepoprawna kalkulacja odliczenia dla {contractor.name}",
                    suggestion=f"Oczekiwana kwota: {expected_deduction} (200%)"
                ))
        
        return issues
    
    def _check_document_amounts(self, content: str, costs) -> list:
        """Check if amounts in document match project costs."""
        issues = []
        
        # Extract amounts from document
        amount_pattern = r'(\d{1,3}(?:[ \s.,]\d{3})*(?:[.,]\d{2})?)\s*(?:PLN|zł|złotych)?'
        found_amounts = re.findall(amount_pattern, content)
        
        # Normalize found amounts
        normalized_amounts = set()
        for amount_str in found_amounts:
            try:
                # Remove spaces and normalize decimal separator
                cleaned = amount_str.replace(" ", "").replace("\xa0", "")
                if "," in cleaned and "." not in cleaned:
                    cleaned = cleaned.replace(",", ".")
                elif "," in cleaned and "." in cleaned:
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                normalized_amounts.add(round(float(cleaned), 2))
            except (ValueError, AttributeError):
                continue
        
        # Check if total costs appear in document
        total_costs_value = round(float(costs.total_costs), 2)
        if total_costs_value > 0 and not self._amount_in_document(total_costs_value, normalized_amounts):
            issues.append(self.create_issue(
                issue_type="missing_total_costs",
                severity=IssueSeverity.WARNING,
                location="document:costs",
                message="Całkowita suma kosztów nie występuje w dokumencie",
                suggestion=f"Dodaj sumę kosztów: {total_costs_value:,.2f} PLN"
            ))
        
        # Check if deduction amount appears in document
        total_deduction = round(float(costs.total_deduction), 2)
        if total_deduction > 0 and not self._amount_in_document(total_deduction, normalized_amounts):
            issues.append(self.create_issue(
                issue_type="missing_deduction_amount",
                severity=IssueSeverity.WARNING,
                location="document:deduction",
                message="Kwota odliczenia B+R nie występuje w dokumencie",
                suggestion=f"Dodaj kwotę odliczenia: {total_deduction:,.2f} PLN"
            ))
        
        return issues
    
    def _amount_in_document(self, target: float, found_amounts: set, tolerance: float = 1.0) -> bool:
        """Check if amount appears in document (with tolerance)."""
        for amount in found_amounts:
            if abs(amount - target) <= tolerance:
                return True
        return False
    
    def _check_personnel_allocations(self, costs) -> list:
        """Check personnel time allocation percentages."""
        issues = []
        
        for employee in costs.personnel_employment:
            # Check for unrealistic allocations
            if employee.percentage > 100:
                issues.append(self.create_issue(
                    issue_type="invalid_percentage",
                    severity=IssueSeverity.CRITICAL,
                    location=f"costs:personnel:{employee.name}",
                    message=f"Alokacja czasu dla {employee.name} przekracza 100%",
                    suggestion="Alokacja czasu musi być w zakresie 0-100%"
                ))
            elif employee.percentage < 10:
                issues.append(self.create_issue(
                    issue_type="low_percentage",
                    severity=IssueSeverity.INFO,
                    location=f"costs:personnel:{employee.name}",
                    message=f"Niska alokacja czasu ({employee.percentage}%) dla {employee.name}",
                    suggestion="Rozważ czy alokacja jest wystarczająca do uzasadnienia kosztu"
                ))
            
            # Check for reasonable salary ranges (Polish market 2025)
            monthly_equivalent = employee.gross_salary
            if monthly_equivalent > Decimal("100000"):
                issues.append(self.create_issue(
                    issue_type="high_salary",
                    severity=IssueSeverity.WARNING,
                    location=f"costs:personnel:{employee.name}",
                    message=f"Wysokie wynagrodzenie ({monthly_equivalent} PLN) - może wymagać dodatkowego uzasadnienia",
                    suggestion="Przygotuj dokumentację uzasadniającą stawkę wynagrodzenia"
                ))
        
        return issues
    
    def _get_correction_instructions(self) -> str:
        return """Fix financial calculation issues:
1. Ensure all cost totals are mathematically correct
2. Verify deduction rates (200% for personnel, 100% for others)
3. Include total costs and deduction amounts in document
4. Fix any percentage allocation errors
5. Add financial summary section if missing
Maintain accuracy in all numerical calculations."""
