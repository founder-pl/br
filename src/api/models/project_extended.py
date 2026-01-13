"""
Extended Project Model for B+R Documentation.

Adds required sections for tax authority compliance:
- Technical problem description
- Research methodology
- Milestones with deliverables
- Risk analysis and uncertainty documentation

Based on: todo/02-br-refactoring-plan.md - Faza 2
"""

from typing import Optional, List
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class UncertaintyLevel(str, Enum):
    """Level of technological uncertainty in the project."""
    HIGH = "wysokie"
    MEDIUM = "średnie"
    LOW = "niskie"


class MilestoneStatus(str, Enum):
    """Status of a project milestone."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class TechnicalProblem(BaseModel):
    """
    Opis problemu technicznego/naukowego.
    
    Required by tax authorities to demonstrate B+R qualification.
    Must clearly describe WHY standard solutions don't work.
    """
    description: str = Field(..., min_length=100, description="Szczegółowy opis problemu")
    why_no_standard_solution: str = Field(..., description="Dlaczego standardowe rozwiązania nie wystarczają")
    required_knowledge_domains: List[str] = Field(default_factory=list, description="Wymagane dziedziny wiedzy")
    uncertainty_factors: List[str] = Field(default_factory=list, description="Czynniki niepewności")
    uncertainty_level: UncertaintyLevel = Field(default=UncertaintyLevel.MEDIUM)


class ResearchMethodology(BaseModel):
    """
    Metodologia badawcza projektu.
    
    Describes the systematic approach to solving the technical problem.
    """
    approach: str = Field(..., description="Podejście badawcze (eksperymentalna, iteracyjna, prototypowa)")
    phases: List[str] = Field(default_factory=list, description="Fazy projektu")
    validation_methods: List[str] = Field(default_factory=list, description="Metody walidacji wyników")
    success_criteria: List[str] = Field(default_factory=list, description="Kryteria sukcesu")


class Milestone(BaseModel):
    """
    Kamień milowy projektu B+R.
    
    Tracks project progress with concrete deliverables.
    """
    name: str
    target_date: date
    actual_date: Optional[date] = None
    deliverables: List[str] = Field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.PLANNED
    findings: Optional[str] = None
    hours_spent: float = 0


class RiskAnalysis(BaseModel):
    """
    Analiza ryzyka niepowodzenia (wymagana dla B+R).
    
    Documents the uncertainty element required for B+R qualification.
    Actual failures and lessons learned strengthen the case.
    """
    identified_risks: List[str] = Field(default_factory=list, description="Zidentyfikowane ryzyka")
    mitigation_strategies: List[str] = Field(default_factory=list, description="Strategie mitygacji")
    actual_failures: List[str] = Field(default_factory=list, description="Udokumentowane niepowodzenia")
    lessons_learned: List[str] = Field(default_factory=list, description="Wnioski z niepowodzeń")


class InnovationScope(str, Enum):
    """Scope of innovation."""
    COMPANY = "firma"
    NATIONAL = "rynek krajowy"
    GLOBAL = "rynek globalny"


class ProjectInputExtended(BaseModel):
    """
    Rozszerzony model projektu B+R.
    
    Contains all required sections for complete B+R documentation
    that will pass tax authority audits.
    """
    # Basic data
    name: str
    code: str
    fiscal_year: int
    company_name: str
    company_nip: str
    
    # Required sections (P1)
    technical_problem: Optional[TechnicalProblem] = None
    methodology: Optional[ResearchMethodology] = None
    milestones: List[Milestone] = Field(default_factory=list)
    risk_analysis: Optional[RiskAnalysis] = None
    
    # Innovation description
    innovation_scope: InnovationScope = InnovationScope.COMPANY
    innovation_description: Optional[str] = None
    comparison_to_existing: Optional[str] = None
    
    # Summary metrics
    total_br_hours: float = 0
    total_br_expenses: float = 0
    
    class Config:
        use_enum_values = True


class UncertaintySection(BaseModel):
    """
    Generated uncertainty section for documentation.
    
    This is a CRITICAL section - lack of uncertainty documentation
    is the main reason for B+R qualification rejection.
    """
    content: str
    word_count: int
    keywords_present: List[str]
    confidence_score: float = Field(ge=0, le=1)
    
    @property
    def is_sufficient(self) -> bool:
        """Check if section meets minimum requirements."""
        required_keywords = ["niepewność", "ryzyko"]
        has_keywords = any(kw in self.content.lower() for kw in required_keywords)
        return self.word_count >= 100 and has_keywords


# Default templates for quick project setup
DEFAULT_TECHNICAL_PROBLEM = TechnicalProblem(
    description="Projekt dotyczy stworzenia innowacyjnego rozwiązania technicznego, "
                "które wymaga przeprowadzenia prac badawczo-rozwojowych ze względu na "
                "brak dostępnych na rynku gotowych rozwiązań spełniających wymagania.",
    why_no_standard_solution="Dostępne rozwiązania nie spełniają specyficznych wymagań "
                            "dotyczących wydajności, skalowalności lub integracji z istniejącymi systemami.",
    required_knowledge_domains=["informatyka", "inżynieria oprogramowania"],
    uncertainty_factors=["możliwość osiągnięcia zakładanej wydajności", "kompatybilność z istniejącymi systemami"],
    uncertainty_level=UncertaintyLevel.MEDIUM
)

DEFAULT_METHODOLOGY = ResearchMethodology(
    approach="iteracyjna z elementami eksperymentalnymi",
    phases=["analiza wymagań", "projektowanie architektury", "implementacja prototypu", "testowanie", "walidacja"],
    validation_methods=["testy jednostkowe", "testy integracyjne", "testy wydajnościowe", "code review"],
    success_criteria=["działający prototyp", "dokumentacja techniczna", "wyniki testów"]
)

DEFAULT_RISK_ANALYSIS = RiskAnalysis(
    identified_risks=[
        "Ryzyko nieosiągnięcia zakładanej wydajności",
        "Ryzyko problemów z integracją",
        "Ryzyko przekroczenia budżetu czasowego"
    ],
    mitigation_strategies=[
        "Iteracyjne podejście z częstymi walidacjami",
        "Prototypowanie przed pełną implementacją",
        "Regularne przeglądy postępów"
    ],
    actual_failures=[],
    lessons_learned=[]
)
