"""
BR Documentation Generator - Legal Compliance Validator

Validates documentation against Polish B+R tax relief requirements.
"""

from __future__ import annotations

import re

import structlog

from ..models import IssueSeverity, ValidationResult, ValidationStatus
from .base import BaseValidator, ValidationContext

logger = structlog.get_logger(__name__)


# B+R legal requirements based on Polish tax law
BR_LEGAL_REQUIREMENTS = {
    "systematicity": {
        "description": "Systematyczność - projekt realizowany zgodnie z harmonogramem",
        "keywords": ["harmonogram", "etap", "faza", "kamień milowy", "systematycznie", "planowo"],
        "required_count": 2,
    },
    "creativity": {
        "description": "Twórczość - projekt kreatywny i oryginalny",
        "keywords": ["twórczy", "kreatywny", "oryginalny", "nowy", "niestandardowy", "unikalny"],
        "required_count": 2,
    },
    "innovation": {
        "description": "Nowatorstwo - projekt prowadzi do innowacji",
        "keywords": ["innowacja", "innowacyjny", "nowatorski", "nowy", "ulepszenie", "rozwój"],
        "required_count": 3,
    },
    "uncertainty": {
        "description": "Niepewność - ryzyko nieosiągnięcia celu",
        "keywords": ["ryzyko", "niepewność", "wyzwanie", "problem", "hipoteza", "test"],
        "required_count": 2,
    },
    "documentation": {
        "description": "Dokumentacja - odpowiednia ewidencja prac",
        "keywords": ["dokumentacja", "ewidencja", "raport", "protokół", "zestawienie"],
        "required_count": 1,
    },
}

# Required NIP validation patterns
NIP_PATTERN = r'\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b|\b\d{10}\b'


class LegalComplianceValidator(BaseValidator):
    """
    Validates documentation against Polish B+R legal requirements.
    
    Checks:
    - Presence of required B+R criteria (systematicity, creativity, innovation)
    - Correct company identification (NIP)
    - Proper cost categorization language
    - Required legal phrases and declarations
    """
    
    @property
    def stage_name(self) -> str:
        return "legal_compliance_validation"
    
    @property
    def validation_criteria(self) -> list[str]:
        return [
            "Systematyczność jest udokumentowana",
            "Twórczość projektu jest opisana",
            "Nowatorstwo jest wykazane",
            "Elementy ryzyka/niepewności są wymienione",
            "NIP firmy jest poprawny",
            "Kategorie kosztów są zgodne z ustawą CIT",
            "Dokumentacja spełnia wymogi formalne",
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate legal compliance."""
        logger.info("Starting legal compliance validation", iteration=context.current_iteration)
        
        issues = []
        content = context.markdown_content.lower()
        
        # Check B+R criteria keywords
        criteria_issues = self._check_br_criteria(content)
        issues.extend(criteria_issues)
        
        # Check NIP presence and validity
        nip_issues = self._check_nip(context)
        issues.extend(nip_issues)
        
        # Check cost categories
        cost_issues = self._check_cost_categories(content)
        issues.extend(cost_issues)
        
        # Check required declarations
        declaration_issues = self._check_declarations(content)
        issues.extend(declaration_issues)
        
        # LLM validation for legal language
        if self.use_llm:
            llm_issues = await self._llm_legal_validation(context)
            issues.extend(llm_issues)
        
        # Calculate score
        score = self.calculate_score_from_issues(issues)
        status = self.determine_status(score, issues)
        
        logger.info(
            "Legal compliance validation complete",
            score=score,
            status=status.value,
            issue_count=len(issues)
        )
        
        return self.create_result(
            status=status,
            score=score,
            issues=issues,
            metadata={
                "criteria_met": self._count_met_criteria(content),
                "total_criteria": len(BR_LEGAL_REQUIREMENTS),
            }
        )
    
    def _check_br_criteria(self, content: str) -> list:
        """Check for B+R criteria keywords."""
        issues = []
        
        for criterion_id, criterion_info in BR_LEGAL_REQUIREMENTS.items():
            keywords_found = sum(
                1 for kw in criterion_info["keywords"] 
                if kw in content
            )
            
            if keywords_found < criterion_info["required_count"]:
                issues.append(self.create_issue(
                    issue_type=f"br_criterion_{criterion_id}",
                    severity=IssueSeverity.ERROR,
                    location=f"criterion:{criterion_id}",
                    message=f"Niewystarczająca dokumentacja kryterium: {criterion_info['description']}",
                    suggestion=f"Użyj słów kluczowych: {', '.join(criterion_info['keywords'][:5])}"
                ))
        
        return issues
    
    def _check_nip(self, context: ValidationContext) -> list:
        """Check NIP presence and validity."""
        issues = []
        content = context.markdown_content
        project = context.project_input
        
        # Find NIPs in document
        nips_found = re.findall(NIP_PATTERN, content)
        
        if not nips_found:
            issues.append(self.create_issue(
                issue_type="missing_nip",
                severity=IssueSeverity.CRITICAL,
                location="document",
                message="Dokument nie zawiera numeru NIP",
                suggestion=f"Dodaj NIP firmy: {project.project.company.nip}"
            ))
        else:
            # Check if company NIP is present
            expected_nip = project.project.company.nip.replace("-", "").replace(" ", "")
            found_normalized = [n.replace("-", "").replace(" ", "") for n in nips_found]
            
            if expected_nip not in found_normalized:
                issues.append(self.create_issue(
                    issue_type="nip_mismatch",
                    severity=IssueSeverity.ERROR,
                    location="document",
                    message="NIP w dokumencie nie zgadza się z danymi firmy",
                    suggestion=f"Użyj poprawnego NIP: {project.project.company.nip}"
                ))
        
        return issues
    
    def _check_cost_categories(self, content: str) -> list:
        """Check for proper cost category language."""
        issues = []
        
        # Required cost category keywords according to CIT
        cost_categories = {
            "wynagrodzenia": ["wynagrodzenie", "płaca", "pensja", "premia"],
            "materiały": ["materiał", "surowiec", "komponent"],
            "sprzęt": ["sprzęt", "urządzenie", "narzędzie"],
            "ekspertyzy": ["ekspertyza", "opinia", "doradztwo"],
            "amortyzacja": ["amortyzacja", "odpis"],
        }
        
        categories_found = 0
        for category, keywords in cost_categories.items():
            if any(kw in content for kw in keywords):
                categories_found += 1
        
        if categories_found < 2:
            issues.append(self.create_issue(
                issue_type="cost_categories",
                severity=IssueSeverity.WARNING,
                location="section:costs",
                message="Niewystarczająca kategoryzacja kosztów kwalifikowanych",
                suggestion="Użyj terminologii zgodnej z ustawą CIT dla kategorii kosztów"
            ))
        
        return issues
    
    def _check_declarations(self, content: str) -> list:
        """Check for required declarations and phrases."""
        issues = []
        
        # Required phrases for B+R documentation
        required_phrases = [
            ("rok podatkowy", "Brak wskazania roku podatkowego"),
            ("koszty kwalifikowane", "Brak określenia 'koszty kwalifikowane'"),
        ]
        
        for phrase, message in required_phrases:
            if phrase not in content:
                issues.append(self.create_issue(
                    issue_type="missing_declaration",
                    severity=IssueSeverity.WARNING,
                    location="document",
                    message=message,
                    suggestion=f"Dodaj frazę: '{phrase}'"
                ))
        
        return issues
    
    async def _llm_legal_validation(self, context: ValidationContext) -> list:
        """Use LLM to validate legal language and compliance."""
        issues = []
        
        try:
            llm = await self.get_llm_client()
            
            legal_criteria = [
                "Dokumentacja jasno wskazuje systematyczność prac B+R",
                "Twórczy charakter działalności jest udokumentowany",
                "Innowacyjność rozwiązania jest wykazana w skali przedsiębiorstwa",
                "Wymienione są elementy ryzyka i niepewności badawczej",
                "Język dokumentacji jest formalny i zgodny z wymogami podatkowymi",
            ]
            
            result = await llm.validate_content(
                content=context.markdown_content,
                validation_criteria=legal_criteria,
                context="Walidacja zgodności z wymaganiami polskiej ulgi B+R (art. 18d ustawy o CIT)"
            )
            
            if not result.get("passed", True) or result.get("score", 1.0) < 0.7:
                for llm_issue in result.get("issues", []):
                    issues.append(self.create_issue(
                        issue_type="legal_compliance_llm",
                        severity=IssueSeverity.WARNING,
                        location=llm_issue.get("location", "document"),
                        message=llm_issue.get("message", "Problem ze zgodnością prawną"),
                        suggestion=llm_issue.get("suggestion")
                    ))
                    
        except Exception as e:
            logger.warning("LLM legal validation failed", error=str(e))
        
        return issues
    
    def _count_met_criteria(self, content: str) -> int:
        """Count how many B+R criteria are met."""
        met = 0
        for criterion_info in BR_LEGAL_REQUIREMENTS.values():
            keywords_found = sum(
                1 for kw in criterion_info["keywords"] 
                if kw in content
            )
            if keywords_found >= criterion_info["required_count"]:
                met += 1
        return met
    
    def _get_correction_instructions(self) -> str:
        return """Fix legal compliance issues:
1. Ensure all B+R criteria are clearly documented (systematyczność, twórczość, nowatorstwo)
2. Include proper NIP identification
3. Use correct cost category terminology from Polish CIT law
4. Add required legal phrases and declarations
5. Emphasize risk and uncertainty elements
Use formal, legal language appropriate for tax documentation."""
