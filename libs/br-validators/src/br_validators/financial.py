"""
Financial validator for B+R documents.

Validates financial calculations, amounts, and Nexus indicator.
"""
import re
from decimal import Decimal
from typing import List, Tuple

from br_core.types import ValidationResult, ValidationSeverity

from .base import BaseValidator, ValidationContext, ValidationStage


class FinancialValidator(BaseValidator):
    """Validates financial calculations in B+R documents"""
    
    stage = ValidationStage.FINANCIAL
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate financial data"""
        issues = []
        content = context.content
        
        # Extract and validate amounts
        amounts = self._extract_amounts(content)
        
        # Check for negative amounts
        for amount, location in amounts:
            if amount < 0:
                issues.append(self.error(
                    f"Wykryto ujemną kwotę: {amount}",
                    code="NEGATIVE_AMOUNT",
                    location=location
                ))
        
        # Check for suspiciously large amounts
        for amount, location in amounts:
            if amount > 10_000_000:  # 10M PLN
                issues.append(self.warning(
                    f"Podejrzanie wysoka kwota: {amount:,.2f} PLN",
                    code="SUSPICIOUS_AMOUNT",
                    location=location
                ))
        
        # Validate Nexus indicator
        nexus_issues = self._validate_nexus(content, context)
        issues.extend(nexus_issues)
        
        # Validate totals if present
        total_issues = self._validate_totals(content, amounts)
        issues.extend(total_issues)
        
        # Check for currency consistency
        currencies = re.findall(r'(PLN|EUR|USD|zł|€|\$)', content)
        unique_currencies = set(c.upper().replace('ZŁ', 'PLN').replace('€', 'EUR').replace('$', 'USD') for c in currencies)
        
        if len(unique_currencies) > 1 and 'PLN' not in unique_currencies:
            issues.append(self.warning(
                f"Dokument zawiera różne waluty: {unique_currencies}",
                code="MIXED_CURRENCIES",
                suggestion="Upewnij się, że kwoty są przeliczone na PLN według kursu NBP"
            ))
        
        # Check for VAT mentions
        if context.document_type in ["expense_registry"]:
            if not re.search(r'(VAT|netto|brutto)', content, re.IGNORECASE):
                issues.append(self.warning(
                    "Brak informacji o VAT (netto/brutto)",
                    code="MISSING_VAT_INFO"
                ))
        
        # Check percentage values
        percentages = re.findall(r'(\d+[.,]?\d*)\s*%', content)
        for pct_str in percentages:
            try:
                pct = float(pct_str.replace(',', '.'))
                if pct > 100:
                    issues.append(self.error(
                        f"Wartość procentowa przekracza 100%: {pct}%",
                        code="INVALID_PERCENTAGE"
                    ))
            except ValueError:
                pass
        
        # Calculate score
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        
        score = max(0, 1 - (error_count * 0.3 + warning_count * 0.1))
        
        result = ValidationResult(
            valid=error_count == 0,
            issues=issues,
            score=score,
            stage=self.stage.value,
        )
        
        context.set_stage_result(self.stage, result)
        context.add_issues(issues)
        
        return result
    
    def _extract_amounts(self, content: str) -> List[Tuple[float, str]]:
        """Extract monetary amounts from content"""
        amounts = []
        
        # Pattern for Polish currency format: 1 234,56 zł or 1234.56 PLN
        amount_pattern = r'(\d{1,3}(?:[\s\xa0]?\d{3})*(?:[,\.]\d{2})?)\s*(?:zł|PLN)'
        
        for match in re.finditer(amount_pattern, content, re.IGNORECASE):
            amount_str = match.group(1)
            # Normalize: remove spaces, replace comma with dot
            normalized = amount_str.replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                amount = float(normalized)
                amounts.append((amount, f"pozycja {match.start()}"))
            except ValueError:
                pass
        
        return amounts
    
    def _validate_nexus(self, content: str, context: ValidationContext) -> List:
        """Validate Nexus indicator"""
        issues = []
        
        # Find Nexus value
        nexus_match = re.search(r'[Nn]exus[:\s]*(\d+[.,]\d+)', content)
        
        if nexus_match:
            nexus_str = nexus_match.group(1).replace(',', '.')
            try:
                nexus = float(nexus_str)
                
                if nexus < 0:
                    issues.append(self.error(
                        f"Wskaźnik Nexus nie może być ujemny: {nexus}",
                        code="NEXUS_NEGATIVE"
                    ))
                elif nexus > 1:
                    issues.append(self.error(
                        f"Wskaźnik Nexus nie może przekraczać 1.0: {nexus}",
                        code="NEXUS_EXCEEDS_ONE",
                        suggestion="Sprawdź obliczenia - Nexus = min(1, ((a+b)×1.3) / (a+b+c+d))"
                    ))
                elif nexus < 0.5:
                    issues.append(self.warning(
                        f"Niski wskaźnik Nexus: {nexus:.4f}",
                        code="NEXUS_LOW",
                        suggestion="Niski Nexus oznacza znaczące koszty od podmiotów powiązanych lub zakupu IP"
                    ))
                
                # Validate Nexus components if present
                components = {}
                for comp in ['a', 'b', 'c', 'd']:
                    comp_match = re.search(rf'\b{comp}[:\s]*(\d+(?:[.,]\d+)?)', content, re.IGNORECASE)
                    if comp_match:
                        components[comp] = float(comp_match.group(1).replace(',', '.'))
                
                if len(components) >= 2:
                    a = components.get('a', 0)
                    b = components.get('b', 0)
                    c = components.get('c', 0)
                    d = components.get('d', 0)
                    
                    total = a + b + c + d
                    if total > 0:
                        calculated_nexus = min(1, ((a + b) * 1.3) / total)
                        
                        if abs(calculated_nexus - nexus) > 0.01:
                            issues.append(self.error(
                                f"Niezgodność Nexus: podano {nexus:.4f}, obliczono {calculated_nexus:.4f}",
                                code="NEXUS_MISMATCH",
                                suggestion="Przelicz wskaźnik Nexus"
                            ))
            except ValueError:
                issues.append(self.error(
                    f"Nieprawidłowy format wskaźnika Nexus: {nexus_str}",
                    code="NEXUS_INVALID_FORMAT"
                ))
        
        elif context.document_type == "nexus_calculation":
            issues.append(self.error(
                "Brak wartości wskaźnika Nexus w dokumencie",
                code="NEXUS_MISSING"
            ))
        
        return issues
    
    def _validate_totals(self, content: str, amounts: List[Tuple[float, str]]) -> List:
        """Validate that totals match sum of items"""
        issues = []
        
        # Look for total/suma patterns
        total_pattern = r'(suma|total|razem|ogółem)[:\s]*(\d{1,3}(?:[\s\xa0]?\d{3})*(?:[,\.]\d{2})?)\s*(?:zł|PLN)?'
        
        for match in re.finditer(total_pattern, content, re.IGNORECASE):
            total_str = match.group(2)
            normalized = total_str.replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                stated_total = float(normalized)
                
                # If we have line items, check sum
                if len(amounts) > 2:
                    # Exclude the total itself
                    line_items = [(a, l) for a, l in amounts if abs(a - stated_total) > 0.01]
                    
                    if line_items:
                        calculated_sum = sum(a for a, _ in line_items)
                        
                        if abs(calculated_sum - stated_total) > 0.01:
                            diff = stated_total - calculated_sum
                            issues.append(self.warning(
                                f"Możliwa niezgodność sumy: podano {stated_total:,.2f}, obliczono {calculated_sum:,.2f} (różnica: {diff:,.2f})",
                                code="TOTAL_MISMATCH",
                                suggestion="Sprawdź sumowanie pozycji"
                            ))
            except ValueError:
                pass
        
        return issues
