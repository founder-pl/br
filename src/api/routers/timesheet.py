"""
Timesheet Router - Time tracking for B+R projects

Allows tracking work hours per project, person, and day with time slots.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()


# Time slots definition
TIME_SLOTS = [
    {"id": "morning", "label": "8:00-12:00", "start": 8, "end": 12},
    {"id": "afternoon", "label": "12:00-16:00", "start": 12, "end": 16},
    {"id": "evening", "label": "16:00-20:00", "start": 16, "end": 20},
    {"id": "night", "label": "20:00-24:00", "start": 20, "end": 24},
]


class WorkerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    role: Optional[str] = None
    hourly_rate: Optional[float] = None


class WorkerResponse(BaseModel):
    id: str
    name: str
    role: Optional[str]
    hourly_rate: Optional[float]
    created_at: datetime


class TimesheetEntry(BaseModel):
    project_id: str
    worker_id: str
    work_date: date
    time_slot: str  # morning, afternoon, evening, night
    hours: float = Field(ge=0, le=4)
    description: Optional[str] = None


class TimesheetResponse(BaseModel):
    id: str
    project_id: str
    worker_id: str
    work_date: date
    time_slot: str
    hours: float
    description: Optional[str]


class ContractorResponse(BaseModel):
    vendor_name: str
    vendor_nip: Optional[str]
    total_amount: float
    invoice_count: int


# Initialize tables
async def ensure_tables(db: AsyncSession):
    """Create timesheet tables if they don't exist"""
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS read_models.workers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            role VARCHAR(100),
            hourly_rate DECIMAL(10, 2),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """))
    
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS read_models.timesheet_entries (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            project_id UUID REFERENCES read_models.projects(id),
            worker_id UUID REFERENCES read_models.workers(id),
            work_date DATE NOT NULL,
            time_slot VARCHAR(20) NOT NULL,
            hours DECIMAL(4, 2) NOT NULL DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT unique_timesheet_entry UNIQUE (project_id, worker_id, work_date, time_slot)
        )
    """))
    
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_timesheet_project ON read_models.timesheet_entries(project_id)
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_timesheet_worker ON read_models.timesheet_entries(worker_id)
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_timesheet_date ON read_models.timesheet_entries(work_date)
    """))


# ==================== WORKERS ====================

@router.get("/workers", response_model=List[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    """List all workers"""
    await ensure_tables(db)
    
    result = await db.execute(text("""
        SELECT id, name, role, hourly_rate, created_at
        FROM read_models.workers
        WHERE is_active = true
        ORDER BY name
    """))
    
    return [
        WorkerResponse(
            id=str(row[0]),
            name=row[1],
            role=row[2],
            hourly_rate=float(row[3]) if row[3] else None,
            created_at=row[4]
        )
        for row in result.fetchall()
    ]


@router.post("/workers", response_model=WorkerResponse)
async def create_worker(worker: WorkerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new worker"""
    await ensure_tables(db)
    
    worker_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO read_models.workers (id, name, role, hourly_rate)
            VALUES (:id, :name, :role, :hourly_rate)
        """),
        {
            "id": worker_id,
            "name": worker.name,
            "role": worker.role,
            "hourly_rate": worker.hourly_rate
        }
    )
    
    return WorkerResponse(
        id=worker_id,
        name=worker.name,
        role=worker.role,
        hourly_rate=worker.hourly_rate,
        created_at=datetime.now()
    )


@router.delete("/workers/{worker_id}")
async def delete_worker(worker_id: str, db: AsyncSession = Depends(get_db)):
    """Deactivate a worker"""
    await db.execute(
        text("UPDATE read_models.workers SET is_active = false WHERE id = :id"),
        {"id": worker_id}
    )
    return {"status": "deleted", "worker_id": worker_id}


# ==================== TIMESHEET ENTRIES ====================

@router.get("/entries")
async def get_timesheet_entries(
    year: int = Query(...),
    month: int = Query(...),
    project_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get timesheet entries for a month"""
    await ensure_tables(db)
    
    query = """
        SELECT t.id, t.project_id, t.worker_id, t.work_date, t.time_slot, t.hours, t.description,
               p.name as project_name, w.name as worker_name
        FROM read_models.timesheet_entries t
        JOIN read_models.projects p ON t.project_id = p.id
        JOIN read_models.workers w ON t.worker_id = w.id
        WHERE EXTRACT(YEAR FROM t.work_date) = :year
          AND EXTRACT(MONTH FROM t.work_date) = :month
    """
    params = {"year": year, "month": month}
    
    if project_id:
        query += " AND t.project_id = :project_id"
        params["project_id"] = project_id
    
    if worker_id:
        query += " AND t.worker_id = :worker_id"
        params["worker_id"] = worker_id
    
    query += " ORDER BY t.work_date, t.time_slot"
    
    result = await db.execute(text(query), params)
    
    entries = []
    for row in result.fetchall():
        entries.append({
            "id": str(row[0]),
            "project_id": str(row[1]),
            "worker_id": str(row[2]),
            "work_date": str(row[3]),
            "time_slot": row[4],
            "hours": float(row[5]),
            "description": row[6],
            "project_name": row[7],
            "worker_name": row[8]
        })
    
    return {"entries": entries, "year": year, "month": month}


@router.post("/entries")
async def save_timesheet_entry(entry: TimesheetEntry, db: AsyncSession = Depends(get_db)):
    """Save or update a timesheet entry"""
    await ensure_tables(db)
    
    # Upsert entry
    await db.execute(
        text("""
            INSERT INTO read_models.timesheet_entries 
            (project_id, worker_id, work_date, time_slot, hours, description)
            VALUES (:project_id, :worker_id, :work_date, :time_slot, :hours, :description)
            ON CONFLICT (project_id, worker_id, work_date, time_slot)
            DO UPDATE SET hours = :hours, description = :description, updated_at = NOW()
        """),
        {
            "project_id": entry.project_id,
            "worker_id": entry.worker_id,
            "work_date": entry.work_date,
            "time_slot": entry.time_slot,
            "hours": entry.hours,
            "description": entry.description
        }
    )
    
    return {"status": "saved", "entry": entry.model_dump()}


@router.post("/entries/batch")
async def save_timesheet_batch(entries: List[TimesheetEntry], db: AsyncSession = Depends(get_db)):
    """Save multiple timesheet entries at once"""
    await ensure_tables(db)
    
    saved = 0
    for entry in entries:
        if entry.hours > 0:
            await db.execute(
                text("""
                    INSERT INTO read_models.timesheet_entries 
                    (project_id, worker_id, work_date, time_slot, hours, description)
                    VALUES (:project_id, :worker_id, :work_date, :time_slot, :hours, :description)
                    ON CONFLICT (project_id, worker_id, work_date, time_slot)
                    DO UPDATE SET hours = :hours, description = :description, updated_at = NOW()
                """),
                {
                    "project_id": entry.project_id,
                    "worker_id": entry.worker_id,
                    "work_date": entry.work_date,
                    "time_slot": entry.time_slot,
                    "hours": entry.hours,
                    "description": entry.description
                }
            )
            saved += 1
    
    return {"status": "saved", "count": saved}


@router.delete("/entries/{entry_id}")
async def delete_timesheet_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a timesheet entry"""
    await db.execute(
        text("DELETE FROM read_models.timesheet_entries WHERE id = :id"),
        {"id": entry_id}
    )
    return {"status": "deleted", "entry_id": entry_id}


# ==================== SUMMARY ====================

@router.get("/summary")
async def get_timesheet_summary(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get summary of hours by project and worker"""
    await ensure_tables(db)
    
    # By project
    project_result = await db.execute(
        text("""
            SELECT p.id, p.name, SUM(t.hours) as total_hours
            FROM read_models.timesheet_entries t
            JOIN read_models.projects p ON t.project_id = p.id
            WHERE EXTRACT(YEAR FROM t.work_date) = :year
              AND EXTRACT(MONTH FROM t.work_date) = :month
            GROUP BY p.id, p.name
            ORDER BY total_hours DESC
        """),
        {"year": year, "month": month}
    )
    
    by_project = [
        {"project_id": str(row[0]), "project_name": row[1], "total_hours": float(row[2])}
        for row in project_result.fetchall()
    ]
    
    # By worker
    worker_result = await db.execute(
        text("""
            SELECT w.id, w.name, SUM(t.hours) as total_hours
            FROM read_models.timesheet_entries t
            JOIN read_models.workers w ON t.worker_id = w.id
            WHERE EXTRACT(YEAR FROM t.work_date) = :year
              AND EXTRACT(MONTH FROM t.work_date) = :month
            GROUP BY w.id, w.name
            ORDER BY total_hours DESC
        """),
        {"year": year, "month": month}
    )
    
    by_worker = [
        {"worker_id": str(row[0]), "worker_name": row[1], "total_hours": float(row[2])}
        for row in worker_result.fetchall()
    ]
    
    return {
        "year": year,
        "month": month,
        "by_project": by_project,
        "by_worker": by_worker,
        "total_hours": sum(p["total_hours"] for p in by_project)
    }


# ==================== CONTRACTORS ====================

@router.get("/contractors", response_model=List[ContractorResponse])
async def get_contractors(db: AsyncSession = Depends(get_db)):
    """Get list of contractors/vendors from expenses"""
    result = await db.execute(text("""
        SELECT vendor_name, vendor_nip, SUM(gross_amount) as total, COUNT(*) as count
        FROM read_models.expenses
        WHERE vendor_name IS NOT NULL AND vendor_name != ''
        GROUP BY vendor_name, vendor_nip
        ORDER BY total DESC
    """))
    
    return [
        ContractorResponse(
            vendor_name=row[0],
            vendor_nip=row[1],
            total_amount=float(row[2]),
            invoice_count=row[3]
        )
        for row in result.fetchall()
    ]


@router.get("/time-slots")
async def get_time_slots():
    """Get available time slots"""
    return {"slots": TIME_SLOTS}
