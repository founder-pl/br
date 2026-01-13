"""
BR Documentation Generator - Data Models

Pydantic models for project input, validation results, and documentation structure.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enums
# =============================================================================

class InnovationType(str, Enum):
    """Type of innovation in the project."""
    PRODUCT = "product"
    PROCESS = "process"
    MIXED = "mixed"


class InnovationScale(str, Enum):
    """Scale of innovation."""
    COMPANY = "company"      # Innowacja w skali przedsiębiorstwa
    INDUSTRY = "industry"    # Innowacja w skali branży
    GLOBAL = "global"        # Innowacja w skali globalnej


class CostCategory(str, Enum):
    """B+R cost categories according to Polish tax law."""
    PERSONNEL_EMPLOYMENT = "personnel_employment"    # Wynagrodzenia pracowników
    PERSONNEL_CIVIL = "personnel_civil"              # Umowy cywilnoprawne
    MATERIALS = "materials"                          # Materiały i surowce
    EQUIPMENT = "equipment"                          # Sprzęt specjalistyczny
    DEPRECIATION = "depreciation"                    # Amortyzacja
    EXPERTISE = "expertise"                          # Ekspertyzy i opinie
    EXTERNAL_RESEARCH = "external_research"          # Usługi jednostek naukowych
    IP_COSTS = "ip_costs"                           # Koszty ochrony własności


class ValidationStatus(str, Enum):
    """Status of validation result."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class IssueSeverity(str, Enum):
    """Severity level of validation issue."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# =============================================================================
# Company & Project Basic Info
# =============================================================================

class CompanyInfo(BaseModel):
    """Company information for documentation."""
    name: str = Field(..., min_length=1, description="Nazwa firmy")
    nip: str = Field(..., pattern=r"^\d{10}$", description="NIP (10 cyfr)")
    regon: Optional[str] = Field(None, pattern=r"^\d{9,14}$", description="REGON")
    address: Optional[str] = Field(None, description="Adres siedziby")
    
    @field_validator("nip")
    @classmethod
    def validate_nip(cls, v: str) -> str:
        """Validate NIP checksum."""
        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(v[i]) * weights[i] for i in range(9)) % 11
        if checksum != int(v[9]):
            raise ValueError("Invalid NIP checksum")
        return v


class ProjectBasicInfo(BaseModel):
    """Basic project information."""
    name: str = Field(..., min_length=1, description="Nazwa projektu")
    code: Optional[str] = Field(None, description="Kod projektu")
    fiscal_year: int = Field(..., ge=2020, le=2030, description="Rok podatkowy")
    company: CompanyInfo


# =============================================================================
# Timeline & Milestones
# =============================================================================

class Milestone(BaseModel):
    """Project milestone."""
    milestone_date: date = Field(..., description="Data kamienia milowego")
    name: str = Field(..., min_length=1, description="Nazwa etapu")
    description: Optional[str] = None
    deliverables: list[str] = Field(default_factory=list)


class ProjectTimeline(BaseModel):
    """Project timeline with milestones."""
    start_date: date
    end_date: date
    milestones: list[Milestone] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectTimeline":
        if self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


# =============================================================================
# Innovation Description
# =============================================================================

class InnovationInfo(BaseModel):
    """Innovation characteristics for B+R qualification."""
    type: InnovationType = Field(..., description="Typ innowacji")
    scale: InnovationScale = Field(
        default=InnovationScale.COMPANY,
        description="Skala innowacji"
    )
    description: str = Field(..., min_length=50, description="Opis innowacji")
    novelty_aspects: list[str] = Field(
        ..., 
        min_length=1, 
        description="Aspekty nowatorskie"
    )
    technical_challenges: list[str] = Field(
        default_factory=list,
        description="Wyzwania techniczne"
    )


# =============================================================================
# Methodology & Research
# =============================================================================

class ResearchMethod(BaseModel):
    """Research method description."""
    name: str
    description: Optional[str] = None
    tools: list[str] = Field(default_factory=list)


class RiskFactor(BaseModel):
    """Research risk factor."""
    description: str
    probability: Optional[str] = None  # low/medium/high
    mitigation: Optional[str] = None


class MethodologyInfo(BaseModel):
    """Research methodology for B+R qualification."""
    systematic: bool = Field(
        ..., 
        description="Czy projekt jest realizowany systematycznie?"
    )
    creative: bool = Field(
        ..., 
        description="Czy projekt ma charakter twórczy?"
    )
    innovative: bool = Field(
        ..., 
        description="Czy projekt prowadzi do innowacji?"
    )
    risk_factors: list[RiskFactor] = Field(
        default_factory=list,
        description="Czynniki ryzyka"
    )
    research_methods: list[ResearchMethod] = Field(
        default_factory=list,
        description="Metody badawcze"
    )
    hypotheses: list[str] = Field(
        default_factory=list,
        description="Hipotezy badawcze"
    )
    expected_results: list[str] = Field(
        default_factory=list,
        description="Oczekiwane rezultaty"
    )
    
    @model_validator(mode="after")
    def validate_br_criteria(self) -> "MethodologyInfo":
        """Validate that B+R criteria are met."""
        if not all([self.systematic, self.creative, self.innovative]):
            raise ValueError(
                "Project must be systematic, creative, and innovative "
                "to qualify for B+R tax relief"
            )
        return self


# =============================================================================
# Costs & Financial Data
# =============================================================================

class PersonnelEmploymentCost(BaseModel):
    """Employee cost (umowa o pracę)."""
    name: str = Field(..., description="Imię i nazwisko")
    role: str = Field(..., description="Stanowisko")
    percentage: float = Field(
        ..., 
        ge=0, 
        le=100, 
        description="% czasu na B+R"
    )
    gross_salary: Decimal = Field(..., ge=0, description="Wynagrodzenie brutto")
    months: int = Field(default=12, ge=1, le=12, description="Liczba miesięcy")
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total qualified cost."""
        return self.gross_salary * self.months * Decimal(self.percentage / 100)
    
    @property
    def deduction_amount(self) -> Decimal:
        """Calculate deduction amount (200% for employees)."""
        return self.total_cost * 2


class PersonnelCivilCost(BaseModel):
    """Civil contract cost (umowa zlecenie/dzieło)."""
    name: str = Field(..., description="Imię i nazwisko")
    role: str = Field(..., description="Rola w projekcie")
    contract_type: str = Field(
        ..., 
        description="Typ umowy: UZ (zlecenie) lub UD (dzieło)"
    )
    amount: Decimal = Field(..., ge=0, description="Kwota umowy")
    description: Optional[str] = None
    
    @property
    def deduction_amount(self) -> Decimal:
        """Calculate deduction amount (200% for civil contracts)."""
        return self.amount * 2


class MaterialCost(BaseModel):
    """Material or equipment cost."""
    name: str
    category: CostCategory
    amount: Decimal = Field(..., ge=0)
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    
    @property
    def deduction_amount(self) -> Decimal:
        """Calculate deduction amount (100% for materials/equipment)."""
        return self.amount


class ExternalServiceCost(BaseModel):
    """External service cost (ekspertyzy, usługi naukowe)."""
    name: str
    provider: str = Field(..., description="Nazwa dostawcy")
    amount: Decimal = Field(..., ge=0)
    description: Optional[str] = None
    is_scientific_unit: bool = Field(
        default=False,
        description="Czy jednostka naukowa?"
    )
    
    @property
    def deduction_amount(self) -> Decimal:
        """Calculate deduction amount."""
        return self.amount


class ProjectCosts(BaseModel):
    """All project costs for B+R calculation."""
    personnel_employment: list[PersonnelEmploymentCost] = Field(default_factory=list)
    personnel_civil: list[PersonnelCivilCost] = Field(default_factory=list)
    materials: list[MaterialCost] = Field(default_factory=list)
    external_services: list[ExternalServiceCost] = Field(default_factory=list)
    
    @property
    def total_personnel_employment(self) -> Decimal:
        return sum(c.total_cost for c in self.personnel_employment)
    
    @property
    def total_personnel_civil(self) -> Decimal:
        return sum(c.amount for c in self.personnel_civil)
    
    @property
    def total_materials(self) -> Decimal:
        return sum(c.amount for c in self.materials)
    
    @property
    def total_external_services(self) -> Decimal:
        return sum(c.amount for c in self.external_services)
    
    @property
    def total_costs(self) -> Decimal:
        return (
            self.total_personnel_employment +
            self.total_personnel_civil +
            self.total_materials +
            self.total_external_services
        )
    
    @property
    def total_deduction(self) -> Decimal:
        """Calculate total B+R deduction amount."""
        personnel_deduction = (
            sum(c.deduction_amount for c in self.personnel_employment) +
            sum(c.deduction_amount for c in self.personnel_civil)
        )
        other_deduction = (
            sum(c.deduction_amount for c in self.materials) +
            sum(c.deduction_amount for c in self.external_services)
        )
        return personnel_deduction + other_deduction


# =============================================================================
# Documentation Configuration
# =============================================================================

class ExistingFile(BaseModel):
    """Reference to existing documentation file."""
    path: Path
    description: Optional[str] = None


class DocumentationConfig(BaseModel):
    """Documentation generation configuration."""
    existing_files: list[ExistingFile] = Field(default_factory=list)
    generate_sections: list[str] = Field(
        default=[
            "executive_summary",
            "project_description",
            "methodology",
            "innovation_analysis",
            "cost_calculation",
            "timeline",
            "risk_assessment",
            "conclusions",
        ]
    )
    include_appendices: bool = True
    language: str = "pl"


# =============================================================================
# Complete Project Input
# =============================================================================

class ProjectInput(BaseModel):
    """Complete project input for documentation generation."""
    project: ProjectBasicInfo
    timeline: ProjectTimeline
    innovation: InnovationInfo
    methodology: MethodologyInfo
    costs: ProjectCosts
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)
    
    class Config:
        json_schema_extra = {
            "example": {
                "project": {
                    "name": "System automatyzacji B+R",
                    "code": "BR-2025-001",
                    "fiscal_year": 2025,
                    "company": {
                        "name": "Softreck Sp. z o.o.",
                        "nip": "1234567890",
                    }
                }
            }
        }


# =============================================================================
# Validation Results
# =============================================================================

class ValidationIssue(BaseModel):
    """Single validation issue."""
    type: str
    severity: IssueSeverity
    location: str
    message: str
    suggestion: Optional[str] = None


class CorrectionApplied(BaseModel):
    """Record of automatic correction."""
    location: str
    original: str
    corrected: str
    reason: str


class ValidationResult(BaseModel):
    """Result of a validation stage."""
    stage: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ValidationStatus
    score: float = Field(ge=0.0, le=1.0)
    issues: list[ValidationIssue] = Field(default_factory=list)
    corrections_applied: list[CorrectionApplied] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == IssueSeverity.CRITICAL for i in self.issues)
    
    @property
    def has_errors(self) -> bool:
        return any(
            i.severity in [IssueSeverity.CRITICAL, IssueSeverity.ERROR] 
            for i in self.issues
        )


class PipelineResult(BaseModel):
    """Complete result of documentation pipeline."""
    status: ValidationStatus
    quality_score: float = Field(ge=0.0, le=1.0)
    validation_stages: list[ValidationResult] = Field(default_factory=list)
    output_path: Optional[Path] = None
    markdown_content: Optional[str] = None
    generation_time_seconds: float = 0.0
    iterations_used: int = 0
    errors: list[str] = Field(default_factory=list)
    
    def to_yaml(self) -> str:
        """Export result as YAML."""
        import yaml
        return yaml.dump(
            self.model_dump(mode="json"),
            allow_unicode=True,
            default_flow_style=False
        )
    
    def save_validation_report(self, path: Path) -> None:
        """Save validation report to file."""
        path.write_text(self.to_yaml(), encoding="utf-8")


# =============================================================================
# Type Aliases for backward compatibility
# =============================================================================

Timeline = ProjectTimeline
Innovation = InnovationInfo
Methodology = MethodologyInfo
