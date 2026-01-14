"""
Documents Notes - Document notes/annotations management
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db
from .models import DocumentNoteUpsert

logger = structlog.get_logger()
router = APIRouter()


async def ensure_document_notes_table(db: AsyncSession) -> None:
    """Ensure document_notes table exists"""
    await db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS read_models.document_notes (
                document_id UUID PRIMARY KEY REFERENCES read_models.documents(id) ON DELETE CASCADE,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
    )


@router.get("/notes")
async def list_document_notes(
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """List all documents with their annotations"""
    await ensure_document_notes_table(db)
    
    query = """
        SELECT d.id, d.filename, d.document_type, d.ocr_status, d.ocr_confidence,
               d.extracted_data, substring(d.ocr_text for 240) as ocr_excerpt,
               d.mime_type, d.created_at, n.notes, n.updated_at
        FROM read_models.documents d
        LEFT JOIN read_models.document_notes n ON n.document_id = d.id
        WHERE 1=1
    """
    params = {"limit": limit, "offset": offset}
    if project_id:
        query += " AND d.project_id = :project_id"
        params["project_id"] = project_id
    query += " ORDER BY d.created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    items = []
    for r in rows:
        doc_id = str(r[0])
        extracted = r[5] or {}
        if isinstance(extracted, dict) and isinstance(extracted.get('extracted_data'), dict):
            nested = extracted.get('extracted_data') or {}
            extracted = {k: v for k, v in extracted.items() if k != 'extracted_data'}
            extracted.update(nested)

        items.append({
            "id": doc_id,
            "filename": r[1],
            "document_type": r[2],
            "ocr_status": r[3],
            "ocr_confidence": float(r[4]) if r[4] is not None else None,
            "extracted_data": extracted,
            "ocr_excerpt": r[6],
            "mime_type": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
            "notes": r[9],
            "notes_updated_at": r[10].isoformat() if r[10] else None,
            "file_url": f"/api/documents/{doc_id}/file",
            "open_url": f"/?page=expenses&doc={doc_id}",
        })

    return {"items": items, "total": len(items)}


@router.put("/{document_id}/notes")
async def upsert_document_notes(
    document_id: str,
    payload: DocumentNoteUpsert,
    db: AsyncSession = Depends(get_db)
):
    """Create or update document notes"""
    await ensure_document_notes_table(db)

    exists = await db.execute(
        text("SELECT id FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="Document not found")

    await db.execute(
        text("""
            INSERT INTO read_models.document_notes (document_id, notes)
            VALUES (:document_id, :notes)
            ON CONFLICT (document_id)
            DO UPDATE SET notes = EXCLUDED.notes, updated_at = NOW()
        """),
        {"document_id": document_id, "notes": payload.notes}
    )
    await db.commit()

    logger.info("Document notes updated", document_id=document_id)
    return {"status": "updated", "document_id": document_id}
