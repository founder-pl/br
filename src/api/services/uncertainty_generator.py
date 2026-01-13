"""
Uncertainty Section Generator - Critical B+R Documentation Component.

Generates the "Niepewność technologiczna" section required for B+R qualification.
This is the most important section - its absence is the main reason for rejection.

Based on: todo/02-br-refactoring-plan.md - Section 2.2
"""

from typing import Optional, List
import structlog
import httpx
import os

from ..models.project_extended import (
    ProjectInputExtended,
    UncertaintySection,
    RiskAnalysis,
    TechnicalProblem
)

logger = structlog.get_logger()


class UncertaintyGenerator:
    """Generator sekcji niepewności technologicznej."""
    
    UNCERTAINTY_PROMPT = """Na podstawie danych projektu wygeneruj sekcję dokumentacji B+R
opisującą niepewność technologiczną.

PROJEKT: {project_name}
PROBLEM TECHNICZNY: {technical_problem}
ZIDENTYFIKOWANE RYZYKA: {risks}
FAKTYCZNE NIEPOWODZENIA: {failures}
WNIOSKI: {lessons}

SEKCJA POWINNA ZAWIERAĆ:
1. Opis elementów niepewności co do osiągnięcia rezultatu
2. Dlaczego standardowe rozwiązania nie były wystarczające
3. Jakie eksperymenty/testy przeprowadzono
4. Jakie niepowodzenia wystąpiły i czego nauczyły
5. Jak niepewność wpłynęła na kierunek prac

WYMAGANIA:
- Minimum 100 słów
- Użyj słów kluczowych: niepewność, ryzyko, eksperyment, test, prototyp
- Język formalny, polski
- Format: ciągły tekst, bez nagłówków

SEKCJA NIEPEWNOŚCI TECHNOLOGICZNEJ:"""

    REQUIRED_KEYWORDS = [
        "niepewność", "ryzyko", "eksperyment", "test", "prototyp",
        "badanie", "weryfikacja", "walidacja", "hipoteza"
    ]

    def __init__(self, llm_base_url: str = None):
        self.llm_base_url = llm_base_url or os.getenv("LLM_API_URL", "http://br-llm:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.2")

    async def generate(
        self,
        project: ProjectInputExtended
    ) -> UncertaintySection:
        """
        Generate uncertainty section for project documentation.
        
        Args:
            project: Extended project data with risk analysis
            
        Returns:
            UncertaintySection with generated content
        """
        # Try LLM generation first
        try:
            content = await self._generate_with_llm(project)
            if content and len(content.split()) >= 80:
                keywords = self._find_keywords(content)
                return UncertaintySection(
                    content=content,
                    word_count=len(content.split()),
                    keywords_present=keywords,
                    confidence_score=0.85 if len(keywords) >= 3 else 0.7
                )
        except Exception as e:
            logger.warning("LLM uncertainty generation failed", error=str(e))
        
        # Fallback to template
        return self._generate_from_template(project)

    async def _generate_with_llm(self, project: ProjectInputExtended) -> Optional[str]:
        """Generate using LLM."""
        tech_problem = project.technical_problem
        risk_analysis = project.risk_analysis
        
        prompt = self.UNCERTAINTY_PROMPT.format(
            project_name=project.name,
            technical_problem=tech_problem.description if tech_problem else "Brak opisu",
            risks="\n".join(f"- {r}" for r in (risk_analysis.identified_risks if risk_analysis else [])) or "Brak",
            failures="\n".join(f"- {f}" for f in (risk_analysis.actual_failures if risk_analysis else [])) or "Brak udokumentowanych",
            lessons="\n".join(f"- {l}" for l in (risk_analysis.lessons_learned if risk_analysis else [])) or "W trakcie analizy"
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.llm_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        
        return None

    def _generate_from_template(self, project: ProjectInputExtended) -> UncertaintySection:
        """Generate from template (fallback)."""
        tech_problem = project.technical_problem
        risk_analysis = project.risk_analysis
        
        sections = []
        
        # Opening - uncertainty description
        sections.append(
            f"Projekt \"{project.name}\" charakteryzuje się znacznym poziomem niepewności "
            f"technologicznej, wynikającym z innowacyjnego charakteru prowadzonych prac "
            f"badawczo-rozwojowych."
        )
        
        # Technical problem context
        if tech_problem:
            sections.append(
                f"Głównym źródłem niepewności jest {tech_problem.description[:200]}. "
                f"Standardowe rozwiązania dostępne na rynku nie spełniają wymagań projektu, "
                f"ponieważ {tech_problem.why_no_standard_solution[:150]}."
            )
            
            if tech_problem.uncertainty_factors:
                factors = ", ".join(tech_problem.uncertainty_factors[:3])
                sections.append(
                    f"Zidentyfikowane czynniki niepewności obejmują: {factors}."
                )
        else:
            sections.append(
                "Niepewność wynika z braku gotowych rozwiązań spełniających specyficzne "
                "wymagania techniczne projektu, co wymusza przeprowadzenie własnych "
                "prac badawczo-rozwojowych."
            )
        
        # Risk and experiments
        if risk_analysis and risk_analysis.identified_risks:
            risks = ", ".join(risk_analysis.identified_risks[:3])
            sections.append(
                f"W trakcie realizacji projektu zidentyfikowano następujące ryzyka: {risks}. "
                f"Przeprowadzono szereg eksperymentów i testów weryfikujących przyjęte hipotezy."
            )
        else:
            sections.append(
                "Realizacja projektu wymagała przeprowadzenia licznych eksperymentów "
                "i testów prototypowych rozwiązań w celu weryfikacji przyjętych założeń."
            )
        
        # Failures and lessons (strengthens B+R case)
        if risk_analysis and risk_analysis.actual_failures:
            failures = risk_analysis.actual_failures[0]
            sections.append(
                f"W trakcie prac wystąpiły niepowodzenia, w tym: {failures}. "
                f"Analiza przyczyn niepowodzeń pozwoliła na korektę kierunku prac "
                f"i ostateczne osiągnięcie zakładanych celów."
            )
        else:
            sections.append(
                "Iteracyjny charakter prac pozwolił na stopniowe eliminowanie "
                "zidentyfikowanych problemów technicznych poprzez cykl: "
                "hipoteza → eksperyment → walidacja → korekta."
            )
        
        # Closing
        sections.append(
            "Powyższe elementy niepewności potwierdzają badawczo-rozwojowy charakter "
            "prowadzonych prac, zgodnie z definicją działalności B+R określoną "
            "w art. 4a pkt 26-28 ustawy o CIT oraz art. 5a pkt 38-40 ustawy o PIT."
        )
        
        content = " ".join(sections)
        keywords = self._find_keywords(content)
        
        return UncertaintySection(
            content=content,
            word_count=len(content.split()),
            keywords_present=keywords,
            confidence_score=0.65
        )

    def _find_keywords(self, text: str) -> List[str]:
        """Find B+R keywords in text."""
        text_lower = text.lower()
        return [kw for kw in self.REQUIRED_KEYWORDS if kw in text_lower]


# Singleton
_generator: Optional[UncertaintyGenerator] = None


def get_uncertainty_generator() -> UncertaintyGenerator:
    """Get or create uncertainty generator instance."""
    global _generator
    if _generator is None:
        _generator = UncertaintyGenerator()
    return _generator
