"""
Legal compliance validator for B+R documents.

Validates compliance with Polish tax law (art. 18d CIT, IP Box).
"""
import re
from typing import List

from br_core.types import ValidationResult, ValidationSeverity
from br_core.validators import validate_nip

from .base import BaseValidator, ValidationContext, ValidationStage


# B+R categories according to art. 18d CIT
VALID_BR_CATEGORIES = {
    "personnel_employment": "Wynagrodzenia (UoP)",
    "personnel_civil": "Umowy cywilnoprawne",
    "materials": "Materiały i surowce",
    "equipment": "Sprzęt specjalistyczny",
    "external_services": "Usługi zewnętrzne (niepowiązane)",
    "related_services": "Usługi od podmiotów powiązanych",
    "ip_purchase": "Zakup IP",
    "depreciation": "Amortyzacja",
}

# Required legal references
LEGAL_REFERENCES = [
    (r"art\.?\s*18d", "Artykuł 18d ustawy o CIT"),
    (r"IP\s*Box|art\.?\s*24d", "Przepisy IP Box"),
    (r"B\+R|B&R|badawczo[-\s]?rozwojow", "Działalność badawczo-rozwojowa"),
]


class LegalValidator(BaseValidator):
    """Validates legal compliance of B+R documentation"""
    
    stage = ValidationStage.LEGAL
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate legal compliance"""
        issues = []
        content = context.content
        
        # Validate NIP numbers
        nip_pattern = r'\b(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})\b|\b(\d{10})\b'
        for match in re.finditer(nip_pattern, content):
            nip = match.group(0).replace('-', '').replace(' ', '')
            if len(nip) == 10 and nip.isdigit():
                valid, error = validate_nip(nip)
                if not valid:
                    issues.append(self.error(
                        f"Nieprawidłowy NIP: {nip} - {error}",
                        code="INVALID_NIP",
                        location=f"pozycja {match.start()}"
                    ))
        
        # Check for B+R category mentions
        has_category_mention = False
        for category, name in VALID_BR_CATEGORIES.items():
            if re.search(category.replace('_', r'[\s_-]?'), content, re.IGNORECASE) or \
               re.search(re.escape(name), content, re.IGNORECASE):
                has_category_mention = True
                break
        
        if not has_category_mention:
            issues.append(self.warning(
                "Brak wyraźnego odniesienia do kategorii kosztów B+R",
                code="MISSING_BR_CATEGORY",
                suggestion="Dodaj informacje o kategorii kosztu wg art. 18d CIT"
            ))
        
        # Check for legal references (for formal documents)
        if context.document_type in ["project_card", "nexus_calculation"]:
            has_legal_ref = False
            for pattern, name in LEGAL_REFERENCES:
                if re.search(pattern, content, re.IGNORECASE):
                    has_legal_ref = True
                    break
            
            if not has_legal_ref:
                issues.append(self.info(
                    "Brak odniesienia do podstawy prawnej",
                    code="MISSING_LEGAL_REFERENCE",
                    suggestion="Rozważ dodanie odniesienia do art. 18d CIT lub przepisów IP Box"
                ))
        
        # Validate expense qualification justifications
        if context.document_type in ["expense_registry", "project_card"]:
            # Check if expenses have justifications
            expense_pattern = r'(kwalifikowany|qualified|uzasadnienie|justification)'
            if not re.search(expense_pattern, content, re.IGNORECASE):
                issues.append(self.warning(
                    "Brak uzasadnień kwalifikowalności wydatków",
                    code="MISSING_QUALIFICATION_JUSTIFICATION",
                    suggestion="Każdy wydatek powinien mieć uzasadnienie kwalifikowalności B+R"
                ))
        
        # Check date ranges for fiscal year consistency
        year = context.year
        if year:
            date_pattern = r'(\d{4})[-/]\d{2}[-/]\d{2}'
            found_years = set(int(m.group(1)) for m in re.finditer(date_pattern, content))
            
            invalid_years = [y for y in found_years if y != year and y != year - 1 and y != year + 1]
            if invalid_years:
                issues.append(self.warning(
                    f"Znaleziono daty z nieoczekiwanych lat: {invalid_years}",
                    code="INCONSISTENT_DATES",
                    suggestion=f"Upewnij się, że wszystkie daty dotyczą roku {year}"
                ))
        
        # Check for prohibited terms (related party without disclosure)
        related_party_terms = [
            r'podmiot\s+powiązany',
            r'spółka\s+(córka|matka)',
            r'related\s+party',
        ]
        
        has_related_party = any(
            re.search(term, content, re.IGNORECASE) 
            for term in related_party_terms
        )
        
        if has_related_party:
            # Check for proper disclosure
            disclosure_terms = [r'ujawnienie', r'disclosure', r'ceny\s+transferowe']
            has_disclosure = any(
                re.search(term, content, re.IGNORECASE) 
                for term in disclosure_terms
            )
            
            if not has_disclosure:
                issues.append(self.warning(
                    "Dokument wspomina o podmiocie powiązanym bez odpowiedniego ujawnienia",
                    code="RELATED_PARTY_DISCLOSURE",
                    suggestion="Dodaj informacje o cenach transferowych i niezależności"
                ))
        
        # Calculate score
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        
        score = max(0, 1 - (error_count * 0.25 + warning_count * 0.1))
        
        result = ValidationResult(
            valid=error_count == 0,
            issues=issues,
            score=score,
            stage=self.stage.value,
        )
        
        context.set_stage_result(self.stage, result)
        context.add_issues(issues)
        
        return result
