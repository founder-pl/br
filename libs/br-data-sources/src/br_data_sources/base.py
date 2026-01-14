"""
Base classes for data sources.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DataSourceResult:
    """Result from a data source query"""
    data: Any
    source_type: str
    source_name: str
    query_info: str
    fetched_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.error is None
    
    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "fetched_at": self.fetched_at.isoformat(),
            "success": self.success,
            "error": self.error,
        }


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def fetch(self, params: Dict[str, Any], **kwargs) -> DataSourceResult:
        """Fetch data from the source"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return schema/description of available data"""
        pass
    
    def get_api_url(self, params: Dict[str, Any], base_url: str = "http://localhost:81") -> str:
        """
        Get API URL for accessing this data source.
        
        Used for variable tracking and footnotes.
        """
        param_str = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        return f"{base_url}/api/data-source/{self.name}?{param_str}"
