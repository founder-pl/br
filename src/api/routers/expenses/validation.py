"""
Expenses Validation - Validation endpoints for expenses
"""
from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db
from ...validators import InvoiceValidator, CurrencyConverter

logger = structlog.get_logger()
router = APIRouter()

invoice_validator = InvoiceValidator()
currency_converter = CurrencyConverter()


@router.post("/validate-pipeline")
async def validate_expense_pipeline(expense_data: dict):
    """Run comprehensive validation pipeline on expense data."""
    from ...validators.expense_pipeline import get_validation_pipeline
    
    pipeline = get_validation_pipeline()
    result = pipeline.validate(expense_data)
    
    logger.info("Pipeline validation", score=result.score, errors=len(result.errors))
    return result.to_dict()


@router.post("/categorize")
async def categorize_expense(
    description: str = Query(...),
    vendor_name: Optional[str] = Query(default=None),
    amount: Optional[float] = Query(default=None)
):
    """Automatically categorize expense for B+R qualification."""
    from ...services.expense_categorizer import get_expense_categorizer
    
    categorizer = get_expense_categorizer()
    result = categorizer.categorize(description, vendor_name, amount)
    
    logger.info("Expense categorized", 
                category=result.category.value, 
                confidence=result.confidence)
    
    return {
        "category": result.category.value,
        "confidence": result.confidence,
        "keywords_matched": result.keywords_matched,
        "reason": result.reason,
        "is_br_qualified": result.is_br_qualified,
        "deduction_rate": result.deduction_rate
    }


@router.post("/validate-invoice")
async def validate_invoice_number(invoice_number: str = Query(...)):
    """Validate invoice number against Polish standards."""
    result = invoice_validator.validate(invoice_number)
    return {
        "is_valid": result.is_valid,
        "normalized_number": result.normalized_number,
        "errors": result.errors,
        "warnings": result.warnings
    }


@router.post("/convert-currency")
async def convert_currency_to_pln(
    amount: Decimal = Query(...),
    currency: str = Query(...),
    expense_date: date = Query(...)
):
    """Convert foreign currency to PLN using NBP exchange rates."""
    try:
        pln_amount = await currency_converter.convert_to_pln(amount, currency, expense_date)
        return {
            "original_amount": float(amount),
            "original_currency": currency,
            "pln_amount": float(pln_amount),
            "expense_date": expense_date.isoformat(),
            "status": "converted"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate-all")
async def validate_all_expenses(
    project_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    """Validate all expenses for a project."""
    result = await db.execute(
        text("""
            SELECT id, invoice_number, vendor_name, vendor_nip, currency, gross_amount
            FROM read_models.expenses
            WHERE project_id = :project_id
        """),
        {"project_id": project_id}
    )
    rows = result.fetchall()
    
    issues = []
    valid_count = 0
    
    for row in rows:
        expense_id, invoice_num, vendor_name, vendor_nip, currency, amount = row
        expense_issues = []
        
        inv_result = invoice_validator.validate(invoice_num)
        if not inv_result.is_valid:
            expense_issues.extend([{"type": "invoice", "message": e} for e in inv_result.errors])
        if inv_result.warnings:
            expense_issues.extend([{"type": "invoice_warning", "message": w} for w in inv_result.warnings])
        
        if not vendor_name or vendor_name.lower() in ("none", "null", ""):
            expense_issues.append({"type": "vendor", "message": "Brak nazwy dostawcy"})
        
        if currency and currency.upper() != "PLN":
            expense_issues.append({
                "type": "currency",
                "message": f"Waluta {currency} wymaga przeliczenia na PLN",
                "amount": float(amount) if amount else 0
            })
        
        if expense_issues:
            issues.append({
                "expense_id": str(expense_id),
                "invoice_number": invoice_num,
                "issues": expense_issues
            })
        else:
            valid_count += 1
    
    total = len(rows)
    return {
        "project_id": project_id,
        "total_expenses": total,
        "valid_count": valid_count,
        "invalid_count": total - valid_count,
        "validation_rate": round(valid_count / total * 100, 1) if total > 0 else 0,
        "issues": issues
    }
