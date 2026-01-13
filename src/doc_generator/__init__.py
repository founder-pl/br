"""
Document Generator Module

Autonomous module for generating B+R and IP Box documentation.
Provides DSL for data extraction from SQL, REST APIs, and external sources.
"""

from .engine import DocumentEngine
from .data_sources import DataSourceRegistry
from .templates import TemplateRegistry

__all__ = ["DocumentEngine", "DataSourceRegistry", "TemplateRegistry"]
