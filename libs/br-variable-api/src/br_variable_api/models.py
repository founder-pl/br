"""
Models for Variable API responses.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VariableResponse(BaseModel):
    """Response for a single variable"""
    name: str
    value: Any
    source: str
    path: str
    fetched_at: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None
    unit: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectVariableResponse(BaseModel):
    """Response for project-level variable"""
    project_id: str
    variable: VariableResponse
    verification_url: str
    
    
class InvoiceVariableResponse(BaseModel):
    """Response for invoice-level variable"""
    invoice_id: str
    variable: VariableResponse
    ocr_source: Optional[str] = None  # Path to OCR text
    document_id: Optional[str] = None


class InvoiceDataResponse(BaseModel):
    """Response for full invoice data"""
    invoice_id: str
    format: str  # json, plain_text, ocr
    data: Any
    document_id: Optional[str] = None
    ocr_confidence: Optional[float] = None
    fetched_at: datetime = Field(default_factory=datetime.now)


class NexusCalculationResponse(BaseModel):
    """Response for Nexus indicator calculation"""
    project_id: str
    year: int
    a_direct: float = Field(description="Koszty B+R bezpośrednie")
    b_unrelated: float = Field(description="Koszty B+R od niepowiązanych")
    c_related: float = Field(description="Koszty B+R od powiązanych")
    d_ip: float = Field(description="Koszty zakupu gotowego IP")
    nexus: float = Field(description="Obliczony wskaźnik Nexus (0-1)")
    formula: str = "((a + b) × 1.3) / (a + b + c + d)"
    verification_urls: Dict[str, str] = Field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        return 0 <= self.nexus <= 1


class VariableListResponse(BaseModel):
    """Response for listing available variables"""
    project_id: Optional[str] = None
    variables: List[Dict[str, Any]]
    total: int
    base_url: str


class AuthInfoResponse(BaseModel):
    """Response for authentication info"""
    method: str
    user: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
