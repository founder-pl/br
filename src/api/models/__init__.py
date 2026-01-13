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

__all__ = [
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
]
