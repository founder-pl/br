"""
Clarifications Router - Questions and answers for B+R documentation
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database import get_db

logger = structlog.get_logger()
router = APIRouter()


class ClarificationResponse(BaseModel):
    id: str
    expense_id: str
    question: str
    question_type: Optional[str]
    answer: Optional[str]
    answered_at: Optional[datetime]
    auto_generated: bool
    llm_suggested_answer: Optional[str]
    created_at: datetime


class ClarificationAnswer(BaseModel):
    answer: str


class ClarificationCreate(BaseModel):
    expense_id: str
    question: str
    question_type: Optional[str] = None


@router.get("/", response_model=List[ClarificationResponse])
async def list_clarifications(
    expense_id: Optional[str] = Query(default=None),
    unanswered_only: bool = Query(default=False),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List clarification questions"""
    query = """
        SELECT id, expense_id, question, question_type, answer, answered_at,
               auto_generated, llm_suggested_answer, created_at
        FROM read_models.clarifications WHERE 1=1
    """
    params = {}
    
    if expense_id:
        query += " AND expense_id = :expense_id"
        params["expense_id"] = expense_id
    
    if unanswered_only:
        query += " AND answer IS NULL"
    
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit
    
    result = await db.execute(query, params)
    
    return [
        ClarificationResponse(
            id=str(row[0]),
            expense_id=str(row[1]),
            question=row[2],
            question_type=row[3],
            answer=row[4],
            answered_at=row[5],
            auto_generated=row[6] or False,
            llm_suggested_answer=row[7],
            created_at=row[8]
        )
        for row in result.fetchall()
    ]


@router.get("/pending/count")
async def get_pending_count(db: AsyncSession = Depends(get_db)):
    """Get count of unanswered clarifications"""
    result = await db.execute(
        "SELECT COUNT(*) FROM read_models.clarifications WHERE answer IS NULL"
    )
    count = result.scalar() or 0
    return {"pending_count": count}


@router.get("/{clarification_id}", response_model=ClarificationResponse)
async def get_clarification(clarification_id: str, db: AsyncSession = Depends(get_db)):
    """Get clarification details"""
    result = await db.execute(
        """
        SELECT id, expense_id, question, question_type, answer, answered_at,
               auto_generated, llm_suggested_answer, created_at
        FROM read_models.clarifications WHERE id = :id
        """,
        {"id": clarification_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Clarification not found")
    
    return ClarificationResponse(
        id=str(row[0]),
        expense_id=str(row[1]),
        question=row[2],
        question_type=row[3],
        answer=row[4],
        answered_at=row[5],
        auto_generated=row[6] or False,
        llm_suggested_answer=row[7],
        created_at=row[8]
    )


@router.post("/", response_model=ClarificationResponse)
async def create_clarification(
    clarification: ClarificationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new clarification question"""
    clarification_id = str(uuid.uuid4())
    
    await db.execute(
        """
        INSERT INTO read_models.clarifications 
        (id, expense_id, question, question_type, auto_generated)
        VALUES (:id, :expense_id, :question, :question_type, false)
        """,
        {
            "id": clarification_id,
            "expense_id": clarification.expense_id,
            "question": clarification.question,
            "question_type": clarification.question_type
        }
    )
    
    # Update expense needs_clarification flag
    await db.execute(
        "UPDATE read_models.expenses SET needs_clarification = true WHERE id = :id",
        {"id": clarification.expense_id}
    )
    
    logger.info("Clarification created", clarification_id=clarification_id)
    return await get_clarification(clarification_id, db)


@router.put("/{clarification_id}/answer", response_model=ClarificationResponse)
async def answer_clarification(
    clarification_id: str,
    answer: ClarificationAnswer,
    db: AsyncSession = Depends(get_db)
):
    """Answer a clarification question"""
    # Update clarification
    await db.execute(
        """
        UPDATE read_models.clarifications SET
            answer = :answer,
            answered_at = NOW(),
            updated_at = NOW()
        WHERE id = :id
        """,
        {"id": clarification_id, "answer": answer.answer}
    )
    
    # Check if expense has any remaining unanswered clarifications
    result = await db.execute(
        """
        SELECT c.expense_id, COUNT(*) as pending
        FROM read_models.clarifications c
        WHERE c.id = :id
        GROUP BY c.expense_id
        """,
        {"id": clarification_id}
    )
    row = result.fetchone()
    
    if row:
        expense_id = row[0]
        # Check for remaining unanswered
        remaining = await db.execute(
            """
            SELECT COUNT(*) FROM read_models.clarifications 
            WHERE expense_id = :expense_id AND answer IS NULL
            """,
            {"expense_id": expense_id}
        )
        remaining_count = remaining.scalar() or 0
        
        if remaining_count == 0:
            await db.execute(
                "UPDATE read_models.expenses SET needs_clarification = false WHERE id = :id",
                {"id": expense_id}
            )
    
    logger.info("Clarification answered", clarification_id=clarification_id)
    return await get_clarification(clarification_id, db)


@router.delete("/{clarification_id}")
async def delete_clarification(clarification_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a clarification question"""
    await db.execute(
        "DELETE FROM read_models.clarifications WHERE id = :id",
        {"id": clarification_id}
    )
    return {"status": "deleted", "id": clarification_id}
