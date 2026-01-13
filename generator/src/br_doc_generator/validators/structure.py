"""
BR Documentation Generator - Structure Validator

Validates markdown structure and required sections.
"""

from __future__ import annotations

import re
from typing import Optional

import structlog

from ..models import IssueSeverity, ValidationResult, ValidationStatus
from .base import BaseValidator, ValidationContext

logger = structlog.get_logger(__name__)


# Required sections for B+R documentation
REQUIRED_SECTIONS = {
    "executive_summary": {
        "patterns": [r"#+ *(?:streszczenie|executive summary|podsumowanie)", r"## *1\.? *streszczenie"],
        "description": "Streszczenie wykonawcze",
        "required": True,
    },
    "project_description": {
        "patterns": [r"#+ *(?:opis projektu|project description|cel projektu)"],
        "description": "Opis projektu",
        "required": True,
    },
    "methodology": {
        "patterns": [r"#+ *(?:metodologia|methodology|metody badawcze)"],
        "description": "Metodologia badawcza",
        "required": True,
    },
    "innovation": {
        "patterns": [r"#+ *(?:innowacyjność|innovation|nowatorstwo|analiza innowacji)"],
        "description": "Analiza innowacyjności",
        "required": True,
    },
    "costs": {
        "patterns": [r"#+ *(?:koszty|costs|kalkulacja|wydatki)"],
        "description": "Kalkulacja kosztów",
        "required": True,
    },
    "timeline": {
        "patterns": [r"#+ *(?:harmonogram|timeline|kamienie milowe)"],
        "description": "Harmonogram realizacji",
        "required": True,
    },
    "risk_assessment": {
        "patterns": [r"#+ *(?:ryzyko|risk|analiza ryzyka)"],
        "description": "Analiza ryzyka",
        "required": False,
    },
    "conclusions": {
        "patterns": [r"#+ *(?:wnioski|conclusions|podsumowanie$)"],
        "description": "Wnioski i podsumowanie",
        "required": True,
    },
}


class StructureValidator(BaseValidator):
    """
    Validates markdown document structure.
    
    Checks:
    - Presence of required sections
    - Proper heading hierarchy
    - Minimum content length per section
    - Markdown formatting correctness
    """
    
    @property
    def stage_name(self) -> str:
        return "structure_validation"
    
    @property
    def validation_criteria(self) -> list[str]:
        return [
            "All required sections are present",
            "Heading hierarchy is correct (H1 -> H2 -> H3)",
            "Each section has minimum content length",
            "Markdown syntax is valid",
            "Document has proper title",
            "No orphaned content before first heading",
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate document structure."""
        logger.info("Starting structure validation", iteration=context.current_iteration)
        
        issues = []
        content = context.markdown_content
        
        # Check for document title
        if not self._has_title(content):
            issues.append(self.create_issue(
                issue_type="missing_title",
                severity=IssueSeverity.ERROR,
                location="document:start",
                message="Dokument nie ma tytułu (nagłówek H1)",
                suggestion="Dodaj tytuł na początku dokumentu: # Dokumentacja Projektu B+R"
            ))
        
        # Check required sections
        section_issues = self._check_required_sections(content)
        issues.extend(section_issues)
        
        # Check heading hierarchy
        hierarchy_issues = self._check_heading_hierarchy(content)
        issues.extend(hierarchy_issues)
        
        # Check section content length
        length_issues = self._check_section_lengths(content)
        issues.extend(length_issues)
        
        # Check markdown syntax
        syntax_issues = self._check_markdown_syntax(content)
        issues.extend(syntax_issues)
        
        # Calculate score
        score = self.calculate_score_from_issues(issues)
        status = self.determine_status(score, issues)
        
        logger.info(
            "Structure validation complete",
            score=score,
            status=status.value,
            issue_count=len(issues)
        )
        
        return self.create_result(
            status=status,
            score=score,
            issues=issues,
            metadata={
                "sections_found": self._count_sections(content),
                "total_headings": len(re.findall(r'^#+\s+', content, re.MULTILINE)),
                "total_paragraphs": len(re.findall(r'\n\n[^#\n]', content)),
            }
        )
    
    def _has_title(self, content: str) -> bool:
        """Check if document has H1 title."""
        lines = content.strip().split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# ') and not line.startswith('## '):
                return True
        return False
    
    def _check_required_sections(self, content: str) -> list:
        """Check for required sections."""
        issues = []
        content_lower = content.lower()
        
        for section_id, section_info in REQUIRED_SECTIONS.items():
            if not section_info["required"]:
                continue
                
            found = False
            for pattern in section_info["patterns"]:
                if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                    found = True
                    break
            
            if not found:
                issues.append(self.create_issue(
                    issue_type="missing_section",
                    severity=IssueSeverity.ERROR,
                    location=f"section:{section_id}",
                    message=f"Brak wymaganej sekcji: {section_info['description']}",
                    suggestion=f"Dodaj sekcję '{section_info['description']}' do dokumentu"
                ))
        
        return issues
    
    def _check_heading_hierarchy(self, content: str) -> list:
        """Check heading level hierarchy."""
        issues = []
        headings = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        
        if not headings:
            return issues
        
        prev_level = 0
        for heading_marks, heading_text in headings:
            level = len(heading_marks)
            
            # Check for level jumps (e.g., H1 -> H3)
            if level > prev_level + 1 and prev_level > 0:
                issues.append(self.create_issue(
                    issue_type="heading_hierarchy",
                    severity=IssueSeverity.WARNING,
                    location=f"heading:{heading_text[:30]}",
                    message=f"Przeskok w hierarchii nagłówków: H{prev_level} -> H{level}",
                    suggestion=f"Użyj nagłówka H{prev_level + 1} zamiast H{level}"
                ))
            
            prev_level = level
        
        return issues
    
    def _check_section_lengths(self, content: str) -> list:
        """Check minimum content length per section."""
        issues = []
        
        # Split by headings
        sections = re.split(r'^(#+\s+.+)$', content, flags=re.MULTILINE)
        
        current_heading = None
        for i, part in enumerate(sections):
            if re.match(r'^#+\s+', part):
                current_heading = part.strip()
            elif current_heading and part.strip():
                # Check content length (minimum 100 chars for main sections)
                if len(part.strip()) < 100 and '##' in current_heading:
                    issues.append(self.create_issue(
                        issue_type="section_too_short",
                        severity=IssueSeverity.WARNING,
                        location=f"section:{current_heading[:30]}",
                        message=f"Sekcja '{current_heading[:30]}...' ma zbyt krótką treść",
                        suggestion="Rozwiń treść sekcji o więcej szczegółów"
                    ))
        
        return issues
    
    def _check_markdown_syntax(self, content: str) -> list:
        """Check for common markdown syntax issues."""
        issues = []
        
        # Check for unclosed code blocks
        code_blocks = content.count('```')
        if code_blocks % 2 != 0:
            issues.append(self.create_issue(
                issue_type="unclosed_code_block",
                severity=IssueSeverity.ERROR,
                location="document",
                message="Niezamknięty blok kodu (```))",
                suggestion="Upewnij się, że każdy blok kodu ma otwarcie i zamknięcie ```"
            ))
        
        # Check for broken links
        broken_links = re.findall(r'\[([^\]]+)\]\(\s*\)', content)
        for link_text in broken_links:
            issues.append(self.create_issue(
                issue_type="broken_link",
                severity=IssueSeverity.WARNING,
                location=f"link:{link_text[:20]}",
                message=f"Link bez URL: [{link_text}]()",
                suggestion="Dodaj URL do linku lub usuń puste nawiasy"
            ))
        
        # Check for orphaned list items
        orphaned_items = re.findall(r'(?<!\n)\n[-*]\s+', content)
        if len(orphaned_items) > 3:
            issues.append(self.create_issue(
                issue_type="orphaned_list",
                severity=IssueSeverity.INFO,
                location="document",
                message="Wykryto listy bez poprzedzającej pustej linii",
                suggestion="Dodaj pustą linię przed listami dla lepszego formatowania"
            ))
        
        return issues
    
    def _count_sections(self, content: str) -> int:
        """Count number of sections (H2 headings)."""
        return len(re.findall(r'^##\s+', content, re.MULTILINE))
    
    def _get_correction_instructions(self) -> str:
        return """Fix structural issues in the document:
1. Ensure all required sections are present
2. Fix heading hierarchy (H1 -> H2 -> H3)
3. Expand sections that are too short
4. Fix markdown syntax issues
Maintain the same content and meaning while improving structure."""
