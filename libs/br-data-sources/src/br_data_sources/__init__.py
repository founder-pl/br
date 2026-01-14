"""
BR Data Sources - DSL for data extraction from SQL, REST, and external sources.

Provides unified interface for fetching data for document generation.
"""

from .base import DataSource, DataSourceResult
from .sql import SQLDataSource
from .rest import RESTDataSource
from .curl import CurlDataSource
from .registry import DataSourceRegistry, get_data_registry
from .variable_tracker import VariableTracker, TrackedVariable

__version__ = "0.1.0"

__all__ = [
    "DataSource",
    "DataSourceResult",
    "SQLDataSource",
    "RESTDataSource",
    "CurlDataSource",
    "DataSourceRegistry",
    "get_data_registry",
    "VariableTracker",
    "TrackedVariable",
]
