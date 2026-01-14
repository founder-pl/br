"""
Expenses Models - Pydantic models and B+R categories
"""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    """Create expense request"""
    document_id: Optional[str] = None
    project_id: str = "00000000-0000-0000-0000-000000000001"
    
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_nip: Optional[str] = None
    
    net_amount: Decimal
    vat_amount: Decimal = Decimal("0")
    gross_amount: Decimal
    currency: str = "PLN"
    
    expense_category: Optional[str] = None
    description: Optional[str] = None


class ExpenseResponse(BaseModel):
    """Expense response"""
    id: str
    project_id: str
    document_id: Optional[str]
    
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    vendor_name: Optional[str]
    vendor_nip: Optional[str]
    
    net_amount: float
    vat_amount: float
    gross_amount: float
    currency: str
    
    expense_category: Optional[str]
    br_category: Optional[str]
    br_qualified: bool
    br_qualification_reason: Optional[str]
    br_deduction_rate: float
    
    ip_qualified: bool
    ip_category: Optional[str]
    nexus_category: Optional[str]
    
    llm_classification: Optional[dict]
    llm_confidence: Optional[float]
    manual_override: bool
    
    status: str
    needs_clarification: bool
    clarification_questions: Optional[List[dict]]
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExpenseClassifyRequest(BaseModel):
    """Manual classification request"""
    br_qualified: Optional[bool] = None
    br_category: Optional[str] = None
    br_qualification_reason: Optional[str] = None
    br_deduction_rate: Optional[float] = None
    ip_qualified: Optional[bool] = None
    ip_category: Optional[str] = None
    nexus_category: Optional[str] = None


class ProcessAllRequest(BaseModel):
    project_id: str = "00000000-0000-0000-0000-000000000001"
    fiscal_year: Optional[int] = None
    month: Optional[int] = Field(default=None, ge=1, le=12)


class ExpenseStatusUpdate(BaseModel):
    """Status update request"""
    status: str


class BRCategory(BaseModel):
    """B+R expense category"""
    code: str
    name: str
    description: str
    deduction_rate: float
    examples: List[str]


# B+R Categories (zgodnie z art. 26e PIT)
BR_CATEGORIES = [
    BRCategory(
        code="personnel_employment",
        name="Wynagrodzenia pracowników (umowa o pracę)",
        description="Wynagrodzenia pracowników zatrudnionych na umowę o pracę, realizujących działalność B+R",
        deduction_rate=2.0,
        examples=["Pensje programistów", "Wynagrodzenia inżynierów", "Premie za projekty B+R"]
    ),
    BRCategory(
        code="personnel_civil",
        name="Wynagrodzenia (umowy cywilnoprawne)",
        description="Wynagrodzenia z tytułu umów zlecenie i o dzieło za działalność B+R",
        deduction_rate=2.0,
        examples=["Umowy zlecenie z konsultantami", "Umowy o dzieło za prototypy"]
    ),
    BRCategory(
        code="materials",
        name="Materiały i surowce",
        description="Materiały i surowce bezpośrednio związane z działalnością B+R",
        deduction_rate=1.0,
        examples=["Komponenty elektroniczne", "Licencje oprogramowania", "Materiały do prototypów"]
    ),
    BRCategory(
        code="equipment",
        name="Sprzęt specjalistyczny",
        description="Sprzęt specjalistyczny niebędący środkami trwałymi",
        deduction_rate=1.0,
        examples=["Narzędzia pomiarowe", "Sprzęt laboratoryjny", "Urządzenia testowe"]
    ),
    BRCategory(
        code="depreciation",
        name="Odpisy amortyzacyjne",
        description="Odpisy amortyzacyjne od środków trwałych używanych w B+R",
        deduction_rate=1.0,
        examples=["Amortyzacja komputerów", "Amortyzacja serwerów", "Amortyzacja sprzętu laboratoryjnego"]
    ),
    BRCategory(
        code="expertise",
        name="Ekspertyzy od jednostek naukowych",
        description="Ekspertyzy, opinie, usługi doradcze od jednostek naukowych",
        deduction_rate=1.0,
        examples=["Opinie uczelni", "Ekspertyzy instytutów badawczych", "Recenzje naukowe"]
    ),
    BRCategory(
        code="external_services",
        name="Usługi zewnętrzne B+R",
        description="Usługi od podmiotów zewnętrznych związane z działalnością B+R",
        deduction_rate=1.0,
        examples=["Testy laboratoryjne", "Certyfikacje", "Usługi prototypowania"]
    ),
]
