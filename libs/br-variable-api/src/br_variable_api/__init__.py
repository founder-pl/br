"""
BR Variable API - Access variables with URL queries for document verification.

Provides:
- REST API endpoints for variable access
- Authentication via API key, Basic Auth, or session token
- Invoice data access (OCR, JSON, plain text)
- Variable tracking with footnotes
"""

from .router import create_variable_router
from .auth import (
    AuthMethod,
    APIKeyAuth,
    BasicAuth,
    SessionAuth,
    SSHKeyAuth,
    get_current_auth,
)
from .models import (
    VariableResponse,
    InvoiceVariableResponse,
    ProjectVariableResponse,
)

__version__ = "0.1.0"

__all__ = [
    "create_variable_router",
    "AuthMethod",
    "APIKeyAuth",
    "BasicAuth",
    "SessionAuth",
    "SSHKeyAuth",
    "get_current_auth",
    "VariableResponse",
    "InvoiceVariableResponse",
    "ProjectVariableResponse",
]
