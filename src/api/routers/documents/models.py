"""
Documents Models - Pydantic models for document endpoints
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str
    filename: str
    document_type: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    extracted_data: Optional[dict] = None
    mime_type: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Upload response"""
    document_id: str
    filename: str
    status: str
    message: str


class DocumentNoteUpsert(BaseModel):
    notes: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """Detailed document response with extracted data"""
    id: str
    filename: str
    document_type: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    mime_type: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime
    expense_id: Optional[str] = None
    revenue_id: Optional[str] = None
    
    class Config:
        from_attributes = True
