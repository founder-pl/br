"""
Documents CRUD - Basic CRUD operations
"""
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db
from .models import DocumentResponse
from .upload import UPLOAD_DIR, process_document_ocr

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get document details"""
    result = await db.execute(
        text("""
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               extracted_data, mime_type, created_at
        FROM read_models.documents WHERE id = :id
        """),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=str(row[0]), filename=row[1], document_type=row[2],
        ocr_status=row[3], ocr_confidence=row[4], extracted_data=row[5],
        mime_type=row[6], file_url=f"/api/documents/{str(row[0])}/file", created_at=row[7]
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
               extracted_data, mime_type, created_at
        FROM read_models.documents WHERE 1=1
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
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        DocumentResponse(
            id=str(row[0]), filename=row[1], document_type=row[2],
            ocr_status=row[3], ocr_confidence=row[4], extracted_data=row[5],
            mime_type=row[6], file_url=f"/api/documents/{str(row[0])}/file", created_at=row[7]
        )
        for row in rows
    ]


@router.get("/{document_id}/file")
async def download_document_file(document_id: str, db: AsyncSession = Depends(get_db)):
    """Download document file"""
    result = await db.execute(
        text("SELECT original_path, mime_type, filename FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(row[0]) if row[0] else None
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    resolved = file_path.resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in resolved.parents and resolved != upload_root:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return FileResponse(path=str(resolved), media_type=row[1] or "application/octet-stream", filename=row[2] or resolved.name)


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Reprocess document with OCR"""
    result = await db.execute(
        text("SELECT original_path, document_type FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.execute(
        text("UPDATE read_models.documents SET ocr_status = 'pending', updated_at = NOW() WHERE id = :id"),
        {"id": document_id}
    )
    
    background_tasks.add_task(process_document_ocr, document_id, row[0], row[1])
    logger.info("Document reprocessing queued", document_id=document_id)
    
    return {"status": "queued", "message": "Document queued for reprocessing"}


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete document and associated file"""
    result = await db.execute(
        text("SELECT original_path FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if row[0]:
        file_path = Path(row[0])
        if file_path.exists():
            file_path.unlink()
    
    # Delete record
    await db.execute(text("DELETE FROM read_models.documents WHERE id = :id"), {"id": document_id})
    await db.commit()
    
    logger.info("Document deleted", document_id=document_id)
    return {"status": "deleted", "document_id": document_id}


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update document extracted data"""
    result = await db.execute(
        text("SELECT id FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Document not found")
    
    if 'extracted_data' in updates:
        import json
        await db.execute(
            text("UPDATE read_models.documents SET extracted_data = CAST(:data AS jsonb), updated_at = NOW() WHERE id = :id"),
            {"id": document_id, "data": json.dumps(updates['extracted_data'])}
        )
    
    if 'document_type' in updates:
        await db.execute(
            text("UPDATE read_models.documents SET document_type = :doc_type, updated_at = NOW() WHERE id = :id"),
            {"id": document_id, "doc_type": updates['document_type']}
        )
    
    await db.commit()
    logger.info("Document updated", document_id=document_id)
    
    return {"status": "updated", "document_id": document_id}


@router.get("/{document_id}/detail")
async def get_document_detail(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed document info including OCR text"""
    result = await db.execute(
        text("""
        SELECT d.id, d.filename, d.document_type, d.ocr_status, d.ocr_confidence,
               d.ocr_text, d.extracted_data, d.mime_type, d.created_at,
               e.id as expense_id, r.id as revenue_id
        FROM read_models.documents d
        LEFT JOIN read_models.expenses e ON e.document_id = d.id
        LEFT JOIN read_models.revenues r ON r.document_id = d.id
        WHERE d.id = :id
        """),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": str(row[0]), "filename": row[1], "document_type": row[2],
        "ocr_status": row[3], "ocr_confidence": row[4], "ocr_text": row[5],
        "extracted_data": row[6], "mime_type": row[7],
        "file_url": f"/api/documents/{str(row[0])}/file",
        "created_at": row[8].isoformat() if row[8] else None,
        "expense_id": str(row[9]) if row[9] else None,
        "revenue_id": str(row[10]) if row[10] else None
    }
