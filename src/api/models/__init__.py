"""
API Models module.

Contains extended models for B+R documentation.
"""

from .project_extended import (
    ProjectInputExtended,
    TechnicalProblem,
    ResearchMethodology,
    Milestone,
    RiskAnalysis,
    UncertaintySection,
    UncertaintyLevel,
    MilestoneStatus,
    InnovationScope,
    DEFAULT_TECHNICAL_PROBLEM,
    DEFAULT_METHODOLOGY,
    DEFAULT_RISK_ANALYSIS,
)

from .daily_time_entry import (
    DailyTimeEntry,
    DailyTimeEntryCreate,
    DailyTimeEntryResponse,
    TimeEntryValidationResult,
    BRTaskType,
    TimeSlot,
    GitCommitLink,
    validate_time_entry,
)

__all__ = [
    # Project models
    "ProjectInputExtended",
    "TechnicalProblem",
    "ResearchMethodology",
    "Milestone",
    "RiskAnalysis",
    "UncertaintySection",
    "UncertaintyLevel",
    "MilestoneStatus",
    "InnovationScope",
    "DEFAULT_TECHNICAL_PROBLEM",
    "DEFAULT_METHODOLOGY",
    "DEFAULT_RISK_ANALYSIS",
    # Time entry models
    "DailyTimeEntry",
    "DailyTimeEntryCreate",
    "DailyTimeEntryResponse",
    "TimeEntryValidationResult",
    "BRTaskType",
    "TimeSlot",
    "GitCommitLink",
    "validate_time_entry",
]
