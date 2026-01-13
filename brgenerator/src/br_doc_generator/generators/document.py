"""
BR Documentation Generator - Document Generator

LLM-powered documentation generation for B+R projects.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from ..config import AppConfig, get_config
from ..llm_client import LLMClient, get_llm_client
from ..models import ProjectInput

logger = structlog.get_logger(__name__)


# System prompt for B+R documentation generation
BR_DOCUMENTATION_SYSTEM_PROMPT = """Jesteś ekspertem w przygotowywaniu dokumentacji do polskiej ulgi badawczo-rozwojowej (B+R).
Generujesz profesjonalną dokumentację zgodną z wymaganiami art. 18d ustawy o CIT.

Kluczowe wymagania dla dokumentacji B+R:
1. SYSTEMATYCZNOŚĆ - projekt realizowany planowo według harmonogramu
2. TWÓRCZOŚĆ - działania kreatywne, oryginalne, nastawione na nowe rozwiązania
3. NOWATORSTWO - innowacja minimum w skali przedsiębiorstwa
4. NIEPEWNOŚĆ - element ryzyka nieosiągnięcia celu

Dokumentacja musi zawierać:
- Jasny opis celów projektu i metodologii
- Uzasadnienie innowacyjności rozwiązania
- Szczegółowy harmonogram z kamieniami milowymi
- Kalkulację kosztów kwalifikowanych według kategorii CIT
- Analizę ryzyka i działań mitygujących

Używaj języka formalnego, technicznego, odpowiedniego dla dokumentacji podatkowej.
Pisz w języku polskim, używając terminologii zgodnej z polskim prawem podatkowym."""


class DocumentGenerator:
    """
    LLM-powered B+R documentation generator.
    
    Generates complete documentation in markdown format based on project input.
    """
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize document generator.
        
        Args:
            config: Application configuration
            llm_client: LLM client (created from config if not provided)
        """
        self.config = config or get_config()
        self.llm = llm_client or get_llm_client(self.config.llm)
    
    async def generate(
        self,
        project_input: ProjectInput,
        sections: Optional[list[str]] = None
    ) -> str:
        """
        Generate complete B+R documentation.
        
        Args:
            project_input: Project data for documentation
            sections: Specific sections to generate (default: all)
            
        Returns:
            Generated markdown documentation
        """
        logger.info(
            "Starting documentation generation",
            project=project_input.project.name,
            sections=sections or "all"
        )
        
        sections = sections or project_input.documentation.generate_sections
        
        # Build generation prompt
        prompt = self._build_generation_prompt(project_input, sections)
        
        # Generate documentation
        try:
            content = await self.llm.generate(
                prompt=prompt,
                system_prompt=BR_DOCUMENTATION_SYSTEM_PROMPT,
                max_tokens=self.config.llm.max_tokens,
                temperature=0.3  # Lower for more consistent output
            )
            
            logger.info(
                "Documentation generated",
                length=len(content),
                project=project_input.project.name
            )
            
            return content
            
        except Exception as e:
            logger.error("Documentation generation failed", error=str(e))
            raise
    
    async def generate_section(
        self,
        project_input: ProjectInput,
        section: str
    ) -> str:
        """
        Generate single documentation section.
        
        Args:
            project_input: Project data
            section: Section identifier
            
        Returns:
            Generated section markdown
        """
        prompt = self._build_section_prompt(project_input, section)
        
        return await self.llm.generate(
            prompt=prompt,
            system_prompt=BR_DOCUMENTATION_SYSTEM_PROMPT,
            temperature=0.3
        )
    
    def _build_generation_prompt(
        self,
        project_input: ProjectInput,
        sections: list[str]
    ) -> str:
        """Build prompt for full documentation generation."""
        project = project_input.project
        innovation = project_input.innovation
        methodology = project_input.methodology
        costs = project_input.costs
        timeline = project_input.timeline
        
        # Build project context
        context = f"""
DANE PROJEKTU:
- Nazwa projektu: {project.name}
- Kod projektu: {project.code or 'N/A'}
- Rok podatkowy: {project.fiscal_year}
- Firma: {project.company.name}
- NIP: {project.company.nip}

INNOWACJA:
- Typ: {innovation.type.value}
- Skala: {innovation.scale.value}
- Opis: {innovation.description}
- Aspekty nowatorskie:
{self._format_list(innovation.novelty_aspects)}

METODOLOGIA:
- Systematyczność: {'Tak' if methodology.systematic else 'Nie'}
- Twórczość: {'Tak' if methodology.creative else 'Nie'}
- Innowacyjność: {'Tak' if methodology.innovative else 'Nie'}
- Czynniki ryzyka:
{self._format_risks(methodology.risk_factors)}
- Metody badawcze:
{self._format_methods(methodology.research_methods)}

HARMONOGRAM:
- Początek: {timeline.start_date}
- Koniec: {timeline.end_date}
- Kamienie milowe:
{self._format_milestones(timeline.milestones)}

KOSZTY:
- Wynagrodzenia pracowników: {costs.total_personnel_employment} PLN
- Umowy cywilnoprawne: {costs.total_personnel_civil} PLN
- Materiały i sprzęt: {costs.total_materials} PLN
- Usługi zewnętrzne: {costs.total_external_services} PLN
- RAZEM: {costs.total_costs} PLN
- Kwota odliczenia B+R: {costs.total_deduction} PLN

SEKCJE DO WYGENEROWANIA: {', '.join(sections)}
"""
        
        prompt = f"""Na podstawie poniższych danych projektu wygeneruj kompletną dokumentację B+R w formacie Markdown.

{context}

Wygeneruj dokumentację zawierającą następujące sekcje:
1. Tytuł (H1) - "Dokumentacja Projektu B+R: [Nazwa projektu]"
2. Streszczenie wykonawcze
3. Opis projektu (cel, zakres, innowacyjność)
4. Metodologia badawcza (systematyczność, twórczość, nowatorstwo)
5. Harmonogram realizacji z kamieniami milowymi
6. Kalkulacja kosztów kwalifikowanych (z podziałem na kategorie CIT)
7. Analiza ryzyka
8. Wnioski i podsumowanie

Wymagania formalne:
- Użyj formalnego języka odpowiedniego dla dokumentacji podatkowej
- Podkreśl elementy kwalifikujące projekt do ulgi B+R
- Uwzględnij wszystkie kwoty w PLN
- Dodaj datę dokumentu: {datetime.now().strftime('%Y-%m-%d')}
- Wyraźnie wskaż niepewność i ryzyko badawcze

Wygeneruj pełną dokumentację w formacie Markdown:"""

        return prompt
    
    def _build_section_prompt(self, project_input: ProjectInput, section: str) -> str:
        """Build prompt for single section generation."""
        section_prompts = {
            "executive_summary": self._build_summary_prompt,
            "project_description": self._build_description_prompt,
            "methodology": self._build_methodology_prompt,
            "innovation_analysis": self._build_innovation_prompt,
            "cost_calculation": self._build_costs_prompt,
            "timeline": self._build_timeline_prompt,
            "risk_assessment": self._build_risk_prompt,
            "conclusions": self._build_conclusions_prompt,
        }
        
        builder = section_prompts.get(section)
        if builder:
            return builder(project_input)
        else:
            return f"Wygeneruj sekcję '{section}' dla projektu {project_input.project.name}"
    
    def _build_summary_prompt(self, project_input: ProjectInput) -> str:
        return f"""Wygeneruj streszczenie wykonawcze dla projektu B+R:

Projekt: {project_input.project.name}
Firma: {project_input.project.company.name}
Rok podatkowy: {project_input.project.fiscal_year}
Typ innowacji: {project_input.innovation.type.value}
Całkowite koszty: {project_input.costs.total_costs} PLN
Kwota odliczenia: {project_input.costs.total_deduction} PLN

Streszczenie powinno zawierać:
- Krótki opis projektu (2-3 zdania)
- Główny cel i oczekiwane rezultaty
- Podsumowanie kosztów i odliczeń
- Kluczowe elementy innowacyjności

Wygeneruj sekcję w formacie Markdown (H2):"""

    def _build_description_prompt(self, project_input: ProjectInput) -> str:
        return f"""Wygeneruj opis projektu B+R:

Nazwa: {project_input.project.name}
Opis innowacji: {project_input.innovation.description}
Aspekty nowatorskie: {', '.join(project_input.innovation.novelty_aspects)}

Sekcja powinna zawierać:
- Cel projektu
- Zakres prac
- Innowacyjność rozwiązania
- Korzyści biznesowe

Wygeneruj sekcję w formacie Markdown (H2):"""

    def _build_methodology_prompt(self, project_input: ProjectInput) -> str:
        methodology = project_input.methodology
        return f"""Wygeneruj opis metodologii badawczej:

Systematyczność: {'Tak' if methodology.systematic else 'Nie'}
Twórczość: {'Tak' if methodology.creative else 'Nie'}
Innowacyjność: {'Tak' if methodology.innovative else 'Nie'}
Hipotezy: {', '.join(methodology.hypotheses) if methodology.hypotheses else 'N/A'}
Oczekiwane rezultaty: {', '.join(methodology.expected_results) if methodology.expected_results else 'N/A'}

Sekcja powinna wykazać spełnienie kryteriów B+R:
1. Systematyczność - planowe prowadzenie prac
2. Twórczość - oryginalny, kreatywny charakter
3. Nowatorstwo - element innowacji w skali firmy

Wygeneruj sekcję w formacie Markdown (H2):"""

    def _build_innovation_prompt(self, project_input: ProjectInput) -> str:
        innovation = project_input.innovation
        return f"""Wygeneruj analizę innowacyjności projektu:

Typ innowacji: {innovation.type.value}
Skala: {innovation.scale.value}
Opis: {innovation.description}
Aspekty nowatorskie:
{self._format_list(innovation.novelty_aspects)}

Wyzwania techniczne:
{self._format_list(innovation.technical_challenges)}

Sekcja powinna uzasadnić innowacyjność w kontekście ulgi B+R.

Wygeneruj sekcję w formacie Markdown (H2):"""

    def _build_costs_prompt(self, project_input: ProjectInput) -> str:
        costs = project_input.costs
        return f"""Wygeneruj kalkulację kosztów kwalifikowanych:

WYNAGRODZENIA PRACOWNIKÓW (200% odliczenia):
{self._format_personnel_employment(costs.personnel_employment)}
Suma: {costs.total_personnel_employment} PLN

UMOWY CYWILNOPRAWNE (200% odliczenia):
{self._format_personnel_civil(costs.personnel_civil)}
Suma: {costs.total_personnel_civil} PLN

MATERIAŁY I SPRZĘT (100% odliczenia):
{self._format_materials(costs.materials)}
Suma: {costs.total_materials} PLN

USŁUGI ZEWNĘTRZNE (100% odliczenia):
{self._format_external_services(costs.external_services)}
Suma: {costs.total_external_services} PLN

PODSUMOWANIE:
- Całkowite koszty kwalifikowane: {costs.total_costs} PLN
- Kwota odliczenia B+R: {costs.total_deduction} PLN

Wygeneruj tabelę kosztów w formacie Markdown (H2):"""

    def _build_timeline_prompt(self, project_input: ProjectInput) -> str:
        timeline = project_input.timeline
        return f"""Wygeneruj harmonogram realizacji projektu:

Okres realizacji: {timeline.start_date} - {timeline.end_date}

Kamienie milowe:
{self._format_milestones(timeline.milestones)}

Wygeneruj harmonogram w formacie Markdown z tabelą (H2):"""

    def _build_risk_prompt(self, project_input: ProjectInput) -> str:
        risks = project_input.methodology.risk_factors
        return f"""Wygeneruj analizę ryzyka projektu:

Czynniki ryzyka:
{self._format_risks(risks)}

Sekcja powinna:
- Opisać zidentyfikowane ryzyka
- Wskazać działania mitygujące
- Podkreślić element niepewności badawczej (kluczowy dla B+R)

Wygeneruj sekcję w formacie Markdown (H2):"""

    def _build_conclusions_prompt(self, project_input: ProjectInput) -> str:
        return f"""Wygeneruj wnioski i podsumowanie dokumentacji B+R:

Projekt: {project_input.project.name}
Rok podatkowy: {project_input.project.fiscal_year}
Kwota odliczenia: {project_input.costs.total_deduction} PLN

Podsumowanie powinno:
- Potwierdzić spełnienie kryteriów B+R
- Wskazać kluczowe rezultaty projektu
- Podsumować korzyści podatkowe

Wygeneruj sekcję w formacie Markdown (H2):"""

    # Helper formatting methods
    def _format_list(self, items: list) -> str:
        if not items:
            return "- Brak"
        return "\n".join(f"- {item}" for item in items)
    
    def _format_risks(self, risks: list) -> str:
        if not risks:
            return "- Brak zidentyfikowanych ryzyk"
        return "\n".join(
            f"- {r.description}" + (f" (Mitygacja: {r.mitigation})" if hasattr(r, 'mitigation') and r.mitigation else "")
            for r in risks
        )
    
    def _format_methods(self, methods: list) -> str:
        if not methods:
            return "- Standardowe metody badawcze"
        return "\n".join(
            f"- {m.name}" + (f": {m.description}" if hasattr(m, 'description') and m.description else "")
            for m in methods
        )
    
    def _format_milestones(self, milestones: list) -> str:
        if not milestones:
            return "- Brak zdefiniowanych kamieni milowych"
        return "\n".join(
            f"- {m.date}: {m.name}"
            for m in milestones
        )
    
    def _format_personnel_employment(self, personnel: list) -> str:
        if not personnel:
            return "- Brak kosztów pracowniczych"
        return "\n".join(
            f"- {p.name} ({p.role}): {p.percentage}% czasu, {p.gross_salary} PLN/mies."
            for p in personnel
        )
    
    def _format_personnel_civil(self, personnel: list) -> str:
        if not personnel:
            return "- Brak umów cywilnoprawnych"
        return "\n".join(
            f"- {p.name} ({p.role}): {p.amount} PLN"
            for p in personnel
        )
    
    def _format_materials(self, materials: list) -> str:
        if not materials:
            return "- Brak kosztów materiałowych"
        return "\n".join(
            f"- {m.name}: {m.amount} PLN"
            for m in materials
        )
    
    def _format_external_services(self, services: list) -> str:
        if not services:
            return "- Brak usług zewnętrznych"
        return "\n".join(
            f"- {s.name} ({s.provider}): {s.amount} PLN"
            for s in services
        )
