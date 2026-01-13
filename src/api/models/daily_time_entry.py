"""
Daily Time Entry Model - B+R work time tracking with validation.

Requirements from todo/02-br-refactoring-plan.md - Faza 3:
- Minimum 50 characters description
- B+R task type classification
- Git commit linking for evidence
- Validation of time entries for tax compliance
"""

from typing import Optional, List
from datetime import date, time
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class BRTaskType(str, Enum):
    """Types of B+R tasks for classification."""
    RESEARCH = "badania"
    DEVELOPMENT = "rozwój"
    TESTING = "testowanie"
    DOCUMENTATION = "dokumentacja"
    ANALYSIS = "analiza"
    PROTOTYPING = "prototypowanie"
    EXPERIMENT = "eksperyment"


class TimeSlot(str, Enum):
    """Standard time slots for work tracking."""
    MORNING = "morning"      # 08:00-12:00
    AFTERNOON = "afternoon"  # 12:00-16:00
    EVENING = "evening"      # 16:00-20:00
    NIGHT = "night"          # 20:00-08:00


class GitCommitLink(BaseModel):
    """Link to a git commit as work evidence."""
    repo_name: str
    commit_hash: str
    commit_message: str
    commit_url: Optional[str] = None


class DailyTimeEntry(BaseModel):
    """
    Dzienny wpis czasu pracy B+R.
    
    Minimum requirements for tax compliance:
    - Description: min 50 characters, specific to work done
    - Hours: realistic (0.5-12 per entry)
    - Task type: must be B+R related
    """
    project_id: str
    worker_id: str
    work_date: date
    time_slot: TimeSlot
    
    hours: float = Field(..., ge=0.5, le=12, description="Godziny pracy (0.5-12)")
    task_type: BRTaskType = BRTaskType.DEVELOPMENT
    
    description: str = Field(
        ..., 
        min_length=50,
        description="Szczegółowy opis wykonanych prac B+R (min. 50 znaków)"
    )
    
    # Git integration
    git_commits: List[GitCommitLink] = Field(default_factory=list)
    
    # Validation status
    is_validated: bool = False
    validation_notes: Optional[str] = None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is meaningful, not generic."""
        generic_phrases = [
            "praca nad projektem",
            "prace programistyczne",
            "development",
            "coding",
            "różne zadania"
        ]
        
        v_lower = v.lower()
        for phrase in generic_phrases:
            if v_lower.strip() == phrase:
                raise ValueError(
                    f"Opis zbyt ogólny: '{phrase}'. Podaj konkretne informacje o wykonanych pracach."
                )
        
        # Check for B+R keywords
        br_keywords = [
            "implementacja", "analiza", "test", "prototyp", "badanie",
            "eksperyment", "optymalizacja", "architektura", "moduł",
            "algorytm", "walidacja", "integracja", "refaktoryzacja"
        ]
        
        has_br_keyword = any(kw in v_lower for kw in br_keywords)
        if not has_br_keyword and len(v) < 100:
            # Allow longer descriptions without keywords
            raise ValueError(
                "Opis powinien zawierać słowa kluczowe B+R lub być bardziej szczegółowy (min. 100 znaków)"
            )
        
        return v
    
    @property
    def has_evidence(self) -> bool:
        """Check if entry has git commit evidence."""
        return len(self.git_commits) > 0
    
    def to_db_dict(self) -> dict:
        """Convert to dictionary for database insert."""
        return {
            "project_id": self.project_id,
            "worker_id": self.worker_id,
            "work_date": self.work_date,
            "time_slot": self.time_slot.value,
            "hours": self.hours,
            "description": self.description,
            "task_type": self.task_type.value,
            "git_commits": [c.model_dump() for c in self.git_commits],
            "is_validated": self.is_validated
        }


class DailyTimeEntryCreate(BaseModel):
    """Request model for creating a time entry."""
    project_id: str
    worker_id: str
    work_date: date
    time_slot: TimeSlot = TimeSlot.MORNING
    hours: float = Field(default=4, ge=0.5, le=12)
    task_type: BRTaskType = BRTaskType.DEVELOPMENT
    description: str = Field(..., min_length=50)
    git_commits: List[GitCommitLink] = Field(default_factory=list)


class DailyTimeEntryResponse(BaseModel):
    """Response model for time entries."""
    id: str
    project_id: str
    worker_id: str
    work_date: date
    time_slot: str
    hours: float
    task_type: str
    description: str
    git_commits: List[GitCommitLink]
    is_validated: bool
    has_evidence: bool
    created_at: Optional[str] = None


class TimeEntryValidationResult(BaseModel):
    """Result of time entry validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


def validate_time_entry(entry: DailyTimeEntry) -> TimeEntryValidationResult:
    """
    Validate a time entry for B+R compliance.
    
    Returns validation result with errors, warnings, and suggestions.
    """
    errors = []
    warnings = []
    suggestions = []
    
    # Check description length
    if len(entry.description) < 50:
        errors.append(f"Opis za krótki ({len(entry.description)} znaków, minimum 50)")
    elif len(entry.description) < 100:
        warnings.append("Rozważ bardziej szczegółowy opis (zalecane 100+ znaków)")
    
    # Check for evidence
    if not entry.has_evidence:
        warnings.append("Brak powiązanych commitów git jako dowodu pracy")
        suggestions.append("Dodaj linki do commitów git dla lepszej dokumentacji")
    
    # Check hours reasonability
    if entry.hours > 8:
        warnings.append(f"Nietypowa liczba godzin ({entry.hours}h) - sprawdź poprawność")
    
    # Check task type matches description
    task_keywords = {
        BRTaskType.RESEARCH: ["badanie", "analiza", "przegląd", "research"],
        BRTaskType.TESTING: ["test", "qa", "weryfikacja", "walidacja"],
        BRTaskType.DOCUMENTATION: ["dokumentacja", "opis", "specyfikacja"],
        BRTaskType.PROTOTYPING: ["prototyp", "poc", "demo", "mvp"],
        BRTaskType.EXPERIMENT: ["eksperyment", "próba", "sprawdzenie"]
    }
    
    desc_lower = entry.description.lower()
    expected_keywords = task_keywords.get(entry.task_type, [])
    if expected_keywords and not any(kw in desc_lower for kw in expected_keywords):
        suggestions.append(
            f"Opis nie zawiera słów kluczowych dla typu '{entry.task_type.value}'. "
            f"Rozważ: {', '.join(expected_keywords)}"
        )
    
    return TimeEntryValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions
    )
