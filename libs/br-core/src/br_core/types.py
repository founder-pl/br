"""
Core types for B+R documentation system.

Provides Result types for consistent error handling and validation types.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar, Union

T = TypeVar("T")


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    ERROR = "error"      # Blocks document approval
    WARNING = "warning"  # Requires attention
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: ValidationSeverity
    message: str
    code: str = ""
    location: Optional[str] = None
    suggestion: Optional[str] = None
    source_url: Optional[str] = None  # URL to verify the data
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "code": self.code,
            "location": self.location,
            "suggestion": self.suggestion,
            "source_url": self.source_url,
        }


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0 - 1.0
    stage: str = ""
    validated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "score": self.score,
            "stage": self.stage,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


@dataclass
class Success(Generic[T]):
    """Success result wrapper"""
    value: T
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return True
    
    @property
    def is_failure(self) -> bool:
        return False


@dataclass
class Failure:
    """Failure result wrapper"""
    error: str
    code: str = ""
    details: Optional[dict] = None
    
    @property
    def is_success(self) -> bool:
        return False
    
    @property
    def is_failure(self) -> bool:
        return True


Result = Union[Success[T], Failure]


@dataclass
class VariableReference:
    """Reference to a variable in a document with source URL"""
    name: str
    value: Any
    source_url: str
    description: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    
    def to_footnote(self, index: int) -> str:
        """Generate markdown footnote reference"""
        return f"[^{index}]"
    
    def to_footnote_definition(self, index: int) -> str:
        """Generate markdown footnote definition"""
        return f"[^{index}]: [{self.name}]({self.source_url})"


@dataclass
class DocumentContext:
    """Context for document generation with variable tracking"""
    project_id: str
    year: int
    month: Optional[int] = None
    variables: List[VariableReference] = field(default_factory=list)
    base_url: str = "http://localhost:81"
    
    def add_variable(self, name: str, value: Any, path: str) -> VariableReference:
        """Add a tracked variable with source URL"""
        url = f"{self.base_url}/api/project/{self.project_id}/variable/{path}"
        ref = VariableReference(name=name, value=value, source_url=url)
        self.variables.append(ref)
        return ref
    
    def get_footnotes(self) -> str:
        """Generate all footnotes for the document"""
        lines = ["\n---\n## Przypisy źródłowe\n"]
        for i, var in enumerate(self.variables, 1):
            lines.append(var.to_footnote_definition(i))
        return "\n".join(lines)
