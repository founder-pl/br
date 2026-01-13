"""
Expense Service - Business logic for expense operations.

P3 Task: Refaktoryzacja expenses.py
Based on: todo/05-br-priority-roadmap.md

Extracts business logic from expenses router to reduce complexity.
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import date
from decimal import Decimal
from uuid import UUID
import structlog

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..validators.expense_pipeline import get_validation_pipeline
from ..services.expense_categorizer import get_expense_categorizer
from ..services.audit_trail import get_audit_service, AuditEventType

logger = structlog.get_logger()


class ExpenseService:
    """
    Service for expense business operations.
    
    Separates business logic from HTTP layer.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pipeline = get_validation_pipeline()
        self.categorizer = get_expense_categorizer()
    
    async def get_expense(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """Get expense by ID."""
        result = await self.db.execute(
            text("""
                SELECT id, project_id, document_id, invoice_number, invoice_date,
                       vendor_name, vendor_nip, net_amount, vat_amount, gross_amount,
                       currency, expense_category, br_category, br_qualified,
                       br_qualification_reason, br_deduction_rate, ip_qualified,
                       ip_category, nexus_category, llm_classification, llm_confidence,
                       manual_override, status, needs_clarification, clarification_questions,
                       created_at
                FROM read_models.expenses WHERE id = :id
            """),
            {"id": expense_id}
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        return self._row_to_dict(row)
    
    async def list_expenses(
        self,
        project_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        br_qualified: Optional[bool] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List expenses with filters.
        
        Returns tuple of (expenses, total_count).
        """
        conditions = ["1=1"]
        params = {"limit": limit, "offset": offset}
        
        if project_id:
            conditions.append("project_id = :project_id")
            params["project_id"] = project_id
        
        if year:
            conditions.append("EXTRACT(YEAR FROM invoice_date) = :year")
            params["year"] = year
        
        if month:
            conditions.append("EXTRACT(MONTH FROM invoice_date) = :month")
            params["month"] = month
        
        if br_qualified is not None:
            conditions.append("br_qualified = :br_qualified")
            params["br_qualified"] = br_qualified
        
        if status:
            conditions.append("status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM read_models.expenses WHERE {where_clause}"),
            params
        )
        total = count_result.scalar() or 0
        
        # Get expenses
        result = await self.db.execute(
            text(f"""
                SELECT id, project_id, document_id, invoice_number, invoice_date,
                       vendor_name, vendor_nip, net_amount, vat_amount, gross_amount,
                       currency, expense_category, br_category, br_qualified,
                       br_qualification_reason, br_deduction_rate, ip_qualified,
                       ip_category, nexus_category, llm_classification, llm_confidence,
                       manual_override, status, needs_clarification, clarification_questions,
                       created_at
                FROM read_models.expenses 
                WHERE {where_clause}
                ORDER BY invoice_date DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        expenses = [self._row_to_dict(row) for row in result.fetchall()]
        
        return expenses, total
    
    async def create_expense(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new expense."""
        import uuid
        
        expense_id = str(uuid.uuid4())
        
        await self.db.execute(
            text("""
                INSERT INTO read_models.expenses (
                    id, project_id, document_id, invoice_number, invoice_date,
                    vendor_name, vendor_nip, net_amount, vat_amount, gross_amount,
                    currency, expense_category, br_category, br_qualified,
                    br_qualification_reason, br_deduction_rate, status
                ) VALUES (
                    :id, :project_id, :document_id, :invoice_number, :invoice_date,
                    :vendor_name, :vendor_nip, :net_amount, :vat_amount, :gross_amount,
                    :currency, :expense_category, :br_category, :br_qualified,
                    :br_qualification_reason, :br_deduction_rate, :status
                )
            """),
            {
                "id": expense_id,
                "project_id": data.get("project_id"),
                "document_id": data.get("document_id"),
                "invoice_number": data.get("invoice_number"),
                "invoice_date": data.get("invoice_date"),
                "vendor_name": data.get("vendor_name"),
                "vendor_nip": data.get("vendor_nip"),
                "net_amount": data.get("net_amount"),
                "vat_amount": data.get("vat_amount"),
                "gross_amount": data.get("gross_amount"),
                "currency": data.get("currency", "PLN"),
                "expense_category": data.get("expense_category"),
                "br_category": data.get("br_category"),
                "br_qualified": data.get("br_qualified", False),
                "br_qualification_reason": data.get("br_qualification_reason"),
                "br_deduction_rate": data.get("br_deduction_rate", 1.0),
                "status": data.get("status", "pending")
            }
        )
        await self.db.commit()
        
        # Record audit event
        audit = get_audit_service(self.db)
        await audit.record(
            AuditEventType.EXPENSE_CREATED,
            expense_id,
            {"expense": data},
            "system"
        )
        
        logger.info("Expense created", expense_id=expense_id)
        
        return await self.get_expense(expense_id)
    
    async def update_expense(
        self, 
        expense_id: str, 
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update expense fields."""
        existing = await self.get_expense(expense_id)
        if not existing:
            return None
        
        # Build update query dynamically
        update_fields = []
        params = {"id": expense_id}
        
        allowed_fields = [
            "project_id", "invoice_number", "invoice_date", "vendor_name",
            "vendor_nip", "net_amount", "vat_amount", "gross_amount", "currency",
            "expense_category", "br_category", "br_qualified", "br_qualification_reason",
            "br_deduction_rate", "ip_qualified", "ip_category", "nexus_category",
            "status", "needs_clarification", "clarification_questions", "manual_override"
        ]
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = :{field}")
                params[field] = data[field]
        
        if not update_fields:
            return existing
        
        await self.db.execute(
            text(f"""
                UPDATE read_models.expenses 
                SET {', '.join(update_fields)}
                WHERE id = :id
            """),
            params
        )
        await self.db.commit()
        
        # Record audit event
        audit = get_audit_service(self.db)
        await audit.record(
            AuditEventType.EXPENSE_UPDATED,
            expense_id,
            {"changes": data, "previous": existing},
            "system"
        )
        
        logger.info("Expense updated", expense_id=expense_id)
        
        return await self.get_expense(expense_id)
    
    async def delete_expense(self, expense_id: str) -> bool:
        """Delete expense."""
        existing = await self.get_expense(expense_id)
        if not existing:
            return False
        
        await self.db.execute(
            text("DELETE FROM read_models.expenses WHERE id = :id"),
            {"id": expense_id}
        )
        await self.db.commit()
        
        # Record audit event
        audit = get_audit_service(self.db)
        await audit.record(
            AuditEventType.EXPENSE_DELETED,
            expense_id,
            {"deleted_expense": existing},
            "system"
        )
        
        logger.info("Expense deleted", expense_id=expense_id)
        
        return True
    
    async def validate_expense(self, expense_id: str) -> Dict[str, Any]:
        """Run validation pipeline on expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return {"error": "Expense not found"}
        
        result = self.pipeline.validate(expense)
        
        # Record validation
        audit = get_audit_service(self.db)
        await audit.record(
            AuditEventType.EXPENSE_VALIDATED,
            expense_id,
            {"score": result.score, "issues": len(result.issues)},
            "system"
        )
        
        return result.to_dict()
    
    async def categorize_expense(
        self,
        expense_id: str,
        apply: bool = False
    ) -> Dict[str, Any]:
        """Auto-categorize expense for B+R."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return {"error": "Expense not found"}
        
        description = expense.get("expense_category", "")
        vendor = expense.get("vendor_name", "")
        
        result = self.categorizer.categorize(description, vendor)
        
        if apply and result.is_br_qualified:
            await self.update_expense(expense_id, {
                "br_category": result.category.value,
                "br_qualified": True,
                "br_qualification_reason": result.reason,
                "br_deduction_rate": result.deduction_rate
            })
            
            # Record classification
            audit = get_audit_service(self.db)
            await audit.record(
                AuditEventType.EXPENSE_CLASSIFIED,
                expense_id,
                {
                    "category": result.category.value,
                    "confidence": result.confidence,
                    "reason": result.reason
                },
                "system"
            )
        
        return {
            "expense_id": expense_id,
            "category": result.category.value,
            "confidence": result.confidence,
            "is_br_qualified": result.is_br_qualified,
            "reason": result.reason,
            "applied": apply and result.is_br_qualified
        }
    
    async def get_summary(
        self,
        project_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get expense summary statistics."""
        conditions = ["1=1"]
        params = {}
        
        if project_id:
            conditions.append("project_id = :project_id")
            params["project_id"] = project_id
        
        if year:
            conditions.append("EXTRACT(YEAR FROM invoice_date) = :year")
            params["year"] = year
        
        where_clause = " AND ".join(conditions)
        
        result = await self.db.execute(
            text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE br_qualified = true) as br_qualified,
                    COUNT(*) FILTER (WHERE ip_qualified = true) as ip_qualified,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE needs_clarification = true) as needs_clarification,
                    COALESCE(SUM(gross_amount), 0) as total_gross,
                    COALESCE(SUM(gross_amount) FILTER (WHERE br_qualified = true), 0) as br_gross,
                    COALESCE(SUM(gross_amount) FILTER (WHERE ip_qualified = true), 0) as ip_gross
                FROM read_models.expenses
                WHERE {where_clause}
            """),
            params
        )
        
        row = result.fetchone()
        
        return {
            "total_expenses": row[0],
            "br_qualified_count": row[1],
            "ip_qualified_count": row[2],
            "pending_count": row[3],
            "needs_clarification_count": row[4],
            "total_gross": float(row[5]),
            "br_qualified_gross": float(row[6]),
            "ip_qualified_gross": float(row[7]),
            "br_rate": round(row[1] / row[0] * 100, 1) if row[0] > 0 else 0,
            "ip_rate": round(row[2] / row[0] * 100, 1) if row[0] > 0 else 0
        }
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        return {
            "id": str(row[0]),
            "project_id": str(row[1]) if row[1] else None,
            "document_id": str(row[2]) if row[2] else None,
            "invoice_number": row[3],
            "invoice_date": row[4].isoformat() if row[4] else None,
            "vendor_name": row[5],
            "vendor_nip": row[6],
            "net_amount": float(row[7]) if row[7] else None,
            "vat_amount": float(row[8]) if row[8] else None,
            "gross_amount": float(row[9]) if row[9] else None,
            "currency": row[10],
            "expense_category": row[11],
            "br_category": row[12],
            "br_qualified": row[13],
            "br_qualification_reason": row[14],
            "br_deduction_rate": float(row[15]) if row[15] else None,
            "ip_qualified": row[16],
            "ip_category": row[17],
            "nexus_category": row[18],
            "llm_classification": row[19],
            "llm_confidence": float(row[20]) if row[20] else None,
            "manual_override": row[21],
            "status": row[22],
            "needs_clarification": row[23],
            "clarification_questions": row[24],
            "created_at": row[25].isoformat() if row[25] else None
        }


def get_expense_service(db: AsyncSession) -> ExpenseService:
    """Get expense service instance."""
    return ExpenseService(db)
