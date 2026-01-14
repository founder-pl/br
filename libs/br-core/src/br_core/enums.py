"""
Enumerations for B+R documentation system.
"""
from enum import Enum


class DocumentCategory(str, Enum):
    """Categories of B+R documents"""
    PROJECT = "project"
    FINANCIAL = "financial"
    TIMESHEET = "timesheet"
    LEGAL = "legal"
    TAX = "tax"
    REPORT = "report"


class TimeScope(str, Enum):
    """Time scope for document generation"""
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PROJECT = "project"
    CUSTOM = "custom"


class BRCategory(str, Enum):
    """B+R expense categories according to Polish tax law (art. 18d CIT)"""
    PERSONNEL_EMPLOYMENT = "personnel_employment"  # Wynagrodzenia UoP
    PERSONNEL_CIVIL = "personnel_civil"            # Umowy cywilnoprawne
    MATERIALS = "materials"                        # Materiały i surowce
    EQUIPMENT = "equipment"                        # Sprzęt i wyposażenie
    EXTERNAL_SERVICES = "external_services"        # Usługi zewnętrzne (niepowiązane)
    RELATED_SERVICES = "related_services"          # Usługi od podmiotów powiązanych
    IP_PURCHASE = "ip_purchase"                    # Zakup gotowego IP
    DEPRECIATION = "depreciation"                  # Amortyzacja
    OTHER = "other"                                # Inne koszty kwalifikowane
    
    @property
    def nexus_component(self) -> str:
        """Return Nexus formula component for this category"""
        if self in (self.PERSONNEL_EMPLOYMENT, self.PERSONNEL_CIVIL, 
                    self.MATERIALS, self.EQUIPMENT, self.DEPRECIATION):
            return "a"  # Direct B+R costs
        elif self == self.EXTERNAL_SERVICES:
            return "b"  # Unrelated party costs
        elif self == self.RELATED_SERVICES:
            return "c"  # Related party costs
        elif self == self.IP_PURCHASE:
            return "d"  # IP acquisition costs
        return "a"  # Default to direct


class ExpenseType(str, Enum):
    """Types of expense documents"""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    PAYROLL = "payroll"
    OTHER = "other"


class VATRate(str, Enum):
    """Polish VAT rates"""
    VAT_23 = "23"
    VAT_8 = "8"
    VAT_5 = "5"
    VAT_0 = "0"
    ZW = "zw"    # Exempt
    NP = "np"    # Not applicable
    
    @property
    def rate(self) -> float:
        """Get VAT rate as decimal"""
        if self.value.isdigit():
            return int(self.value) / 100
        return 0.0


class DocumentStatus(str, Enum):
    """Status of document processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"
    REJECTED = "rejected"
