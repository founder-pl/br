"""
Documents Router - Upload and OCR processing
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import httpx
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str
    filename: str
    document_type: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    extracted_data: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Upload response"""
    document_id: str
    filename: str
    status: str
    message: str


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(default="00000000-0000-0000-0000-000000000001"),
    document_type: str = Query(default="invoice"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for OCR processing.
    
    Supported formats:
    - Images: PNG, JPG, JPEG, TIFF
    - PDFs: Single and multi-page
    
    The document will be processed with OCR and data extraction in the background.
    """
    # Validate file type
    allowed_types = {
        "image/png", "image/jpeg", "image/jpg", "image/tiff",
        "application/pdf"
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # Save file
    file_ext = Path(file.filename).suffix.lower()
    file_path = UPLOAD_DIR / f"{doc_id}{file_ext}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Insert document record
    await db.execute(
        """
        INSERT INTO read_models.documents 
        (id, project_id, document_type, filename, original_path, file_size, mime_type, ocr_status)
        VALUES (:id, :project_id, :doc_type, :filename, :path, :size, :mime, 'pending')
        """,
        {
            "id": doc_id,
            "project_id": project_id,
            "doc_type": document_type,
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content),
            "mime": file.content_type
        }
    )
    
    # Queue OCR processing
    background_tasks.add_task(process_document_ocr, doc_id, str(file_path), document_type)
    
    logger.info("Document uploaded", doc_id=doc_id, filename=file.filename)
    
    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="pending",
        message="Document uploaded and queued for OCR processing"
    )


async def process_document_ocr(doc_id: str, file_path: str, document_type: str):
    """Background task to process document with OCR service"""
    from ..database import get_db_context
    
    try:
        # Call OCR service
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f, 'application/octet-stream')}
                params = {
                    'engine': 'paddleocr',
                    'language': 'pol',
                    'dpi': 300,
                    'extract_data': True,
                    'document_type': document_type
                }
                
                response = await client.post(
                    f"{settings.OCR_SERVICE_URL}/ocr/upload",
                    files=files,
                    params=params
                )
        
        if response.status_code == 200:
            result = response.json()
            
            # Update document with OCR results
            async with get_db_context() as db:
                await db.execute(
                    """
                    UPDATE read_models.documents 
                    SET ocr_status = 'completed',
                        ocr_confidence = :confidence,
                        ocr_text = :text,
                        extracted_data = :data::jsonb,
                        updated_at = NOW()
                    WHERE id = :id
                    """,
                    {
                        "id": doc_id,
                        "confidence": result.get('confidence'),
                        "text": result.get('text'),
                        "data": str(result.get('extracted_data', {}))
                    }
                )
            
            logger.info("OCR completed", doc_id=doc_id, confidence=result.get('confidence'))
        else:
            raise Exception(f"OCR service error: {response.status_code}")
            
    except Exception as e:
        logger.error("OCR processing failed", doc_id=doc_id, error=str(e))
        
        async with get_db_context() as db:
            await db.execute(
                """
                UPDATE read_models.documents 
                SET ocr_status = 'failed',
                    validation_errors = :errors::jsonb,
                    updated_at = NOW()
                WHERE id = :id
                """,
                {
                    "id": doc_id,
                    "errors": f'["{str(e)}"]'
                }
            )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get document details"""
    result = await db.execute(
        """
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               extracted_data, created_at
        FROM read_models.documents 
        WHERE id = :id
        """,
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=str(row[0]),
        filename=row[1],
        document_type=row[2],
        ocr_status=row[3],
        ocr_confidence=row[4],
        extracted_data=row[5],
        created_at=row[6]
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    project_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """List documents with optional filtering"""
    query = """
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               extracted_data, created_at
        FROM read_models.documents 
        WHERE 1=1
    """
    params = {}
    
    if project_id:
        query += " AND project_id = :project_id"
        params["project_id"] = project_id
    
    if status:
        query += " AND ocr_status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    return [
        DocumentResponse(
            id=str(row[0]),
            filename=row[1],
            document_type=row[2],
            ocr_status=row[3],
            ocr_confidence=row[4],
            extracted_data=row[5],
            created_at=row[6]
        )
        for row in rows
    ]


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Reprocess document with OCR"""
    result = await db.execute(
        "SELECT original_path, document_type FROM read_models.documents WHERE id = :id",
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status
    await db.execute(
        "UPDATE read_models.documents SET ocr_status = 'pending' WHERE id = :id",
        {"id": document_id}
    )
    
    # Queue reprocessing
    background_tasks.add_task(process_document_ocr, document_id, row[0], row[1])
    
    return {"status": "queued", "message": "Document queued for reprocessing"}
