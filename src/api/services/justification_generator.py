"""
Expense Justification Generator - LLM-based individualized B+R justifications.

Generates unique justifications for each expense based on:
- Invoice details (amount, vendor, category)
- Project context (name, objectives, technical problem)
- B+R tasks and milestones

This addresses the critical issue of generic/duplicated justifications
that would fail tax authority audits.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import structlog
import httpx
import os

logger = structlog.get_logger()


class ExpenseContext(BaseModel):
    """Context for expense justification generation."""
    invoice_number: str
    invoice_date: Optional[str] = None
    amount: float
    currency: str = "PLN"
    vendor_name: Optional[str] = None
    vendor_nip: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    ocr_text: Optional[str] = None


class ProjectContext(BaseModel):
    """Project context for justification generation."""
    name: str
    description: Optional[str] = None
    technical_problem: Optional[str] = None
    objectives: Optional[List[str]] = None
    fiscal_year: int = 2025


class JustificationResult(BaseModel):
    """Result of justification generation."""
    justification: str
    confidence: float = Field(ge=0, le=1)
    br_category_suggestion: Optional[str] = None
    keywords_used: List[str] = []
    word_count: int = 0


class ExpenseJustificationGenerator:
    """Generator indywidualnych uzasadnień dla wydatków B+R."""
    
    # B+R categories with context for better justifications
    BR_CATEGORIES = {
        "personnel_employment": {
            "name": "Wynagrodzenia pracowników",
            "keywords": ["programista", "inżynier", "badacz", "specjalista", "analityk"],
            "template": "Wynagrodzenie za prace badawczo-rozwojowe"
        },
        "personnel_civil": {
            "name": "Umowy cywilnoprawne",
            "keywords": ["konsultant", "ekspert", "zlecenie", "dzieło"],
            "template": "Wynagrodzenie z tytułu umowy za prace B+R"
        },
        "materials": {
            "name": "Materiały i surowce",
            "keywords": ["komponent", "części", "materiał", "surowiec", "element"],
            "template": "Materiały wykorzystane w pracach badawczo-rozwojowych"
        },
        "equipment": {
            "name": "Sprzęt specjalistyczny",
            "keywords": ["serwer", "komputer", "urządzenie", "narzędzie", "sprzęt"],
            "template": "Sprzęt niezbędny do prowadzenia prac B+R"
        },
        "external_services": {
            "name": "Usługi zewnętrzne",
            "keywords": ["usługa", "hosting", "cloud", "API", "subskrypcja", "licencja"],
            "template": "Usługi zewnętrzne wspierające prace badawczo-rozwojowe"
        },
        "software": {
            "name": "Oprogramowanie",
            "keywords": ["licencja", "software", "aplikacja", "narzędzie", "IDE"],
            "template": "Oprogramowanie wykorzystywane w działalności B+R"
        }
    }
    
    JUSTIFICATION_PROMPT = """Wygeneruj profesjonalne uzasadnienie kwalifikacji B+R dla wydatku.

WYDATEK:
- Faktura: {invoice_number}
- Data: {invoice_date}
- Kwota: {amount} {currency}
- Dostawca: {vendor_name}
- Kategoria: {category}
- Opis z faktury: {description}

KONTEKST PROJEKTU B+R:
- Nazwa: {project_name}
- Opis: {project_description}
- Problem techniczny: {technical_problem}

WYMAGANIA DLA UZASADNIENIA:
1. Opisz konkretny związek wydatku z pracami badawczo-rozwojowymi
2. Wskaż jak zakup przyczynił się do postępu prac
3. Użyj specyficznych terminów technicznych
4. Unikaj generycznych sformułowań typu "wydatek związany z B+R"
5. Długość: 50-150 słów
6. Język: polski, formalny

UZASADNIENIE:"""

    def __init__(self, llm_base_url: str = None):
        self.llm_base_url = llm_base_url or os.getenv("LLM_API_URL", "http://br-llm:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.2")
    
    async def generate_justification(
        self,
        expense: ExpenseContext,
        project: ProjectContext
    ) -> JustificationResult:
        """
        Generuje unikalne uzasadnienie dla wydatku.
        
        Uses LLM if available, falls back to template-based generation.
        """
        # Try LLM-based generation first
        try:
            llm_result = await self._generate_with_llm(expense, project)
            if llm_result and len(llm_result) > 50:
                return JustificationResult(
                    justification=llm_result,
                    confidence=0.85,
                    br_category_suggestion=self._detect_category(expense),
                    keywords_used=self._extract_keywords(llm_result),
                    word_count=len(llm_result.split())
                )
        except Exception as e:
            logger.warning("LLM generation failed, using template", error=str(e))
        
        # Fallback to template-based generation
        return self._generate_from_template(expense, project)
    
    async def _generate_with_llm(
        self,
        expense: ExpenseContext,
        project: ProjectContext
    ) -> Optional[str]:
        """Generate justification using LLM."""
        prompt = self.JUSTIFICATION_PROMPT.format(
            invoice_number=expense.invoice_number or "brak",
            invoice_date=expense.invoice_date or "brak",
            amount=expense.amount,
            currency=expense.currency,
            vendor_name=expense.vendor_name or "nieznany",
            category=expense.category or "do klasyfikacji",
            description=expense.description or expense.ocr_text or "brak opisu",
            project_name=project.name,
            project_description=project.description or "Projekt badawczo-rozwojowy",
            technical_problem=project.technical_problem or "Rozwiązanie problemu technicznego"
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.llm_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 300
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
        
        return None
    
    def _generate_from_template(
        self,
        expense: ExpenseContext,
        project: ProjectContext
    ) -> JustificationResult:
        """Generate justification from template (fallback)."""
        category = self._detect_category(expense)
        cat_info = self.BR_CATEGORIES.get(category, self.BR_CATEGORIES["external_services"])
        
        # Build individualized justification from template
        parts = []
        
        # Opening based on category
        parts.append(cat_info["template"])
        
        # Add vendor context if available
        if expense.vendor_name:
            parts.append(f"od {expense.vendor_name}")
        
        # Add project context
        parts.append(f"w ramach projektu \"{project.name}\"")
        
        # Add specific details based on description/OCR
        if expense.description:
            parts.append(f"obejmujący: {expense.description[:100]}")
        elif expense.ocr_text:
            # Extract key phrases from OCR
            key_phrase = self._extract_key_phrase(expense.ocr_text)
            if key_phrase:
                parts.append(f"dotyczący: {key_phrase}")
        
        # Add technical context
        if project.technical_problem:
            parts.append(f"Zakup bezpośrednio wspiera rozwiązanie problemu: {project.technical_problem[:100]}")
        
        # Add amount context for significant expenses
        if expense.amount > 1000:
            parts.append(f"Inwestycja o wartości {expense.amount:.2f} {expense.currency} jest kluczowa dla postępu prac B+R")
        
        justification = ". ".join(parts) + "."
        
        return JustificationResult(
            justification=justification,
            confidence=0.6,
            br_category_suggestion=category,
            keywords_used=cat_info["keywords"][:3],
            word_count=len(justification.split())
        )
    
    def _detect_category(self, expense: ExpenseContext) -> str:
        """Detect B+R category based on expense details."""
        text = " ".join([
            expense.description or "",
            expense.vendor_name or "",
            expense.ocr_text or ""
        ]).lower()
        
        # Score each category
        scores = {}
        for cat_code, cat_info in self.BR_CATEGORIES.items():
            score = sum(1 for kw in cat_info["keywords"] if kw.lower() in text)
            scores[cat_code] = score
        
        # Return highest scoring category, default to external_services
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "external_services"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract B+R keywords from generated text."""
        keywords = []
        text_lower = text.lower()
        
        br_keywords = [
            "badawczo-rozwojowy", "innowacja", "prototyp", "eksperyment",
            "testowanie", "analiza", "optymalizacja", "implementacja",
            "architektura", "algorytm", "moduł", "system"
        ]
        
        for kw in br_keywords:
            if kw in text_lower:
                keywords.append(kw)
        
        return keywords[:5]
    
    def _extract_key_phrase(self, ocr_text: str) -> Optional[str]:
        """Extract key phrase from OCR text for justification."""
        if not ocr_text:
            return None
        
        # Take first meaningful line (skip headers, dates)
        lines = [l.strip() for l in ocr_text.split('\n') if len(l.strip()) > 10]
        
        for line in lines[:5]:
            # Skip lines that look like headers or metadata
            if any(skip in line.lower() for skip in ['faktura', 'data', 'nip', 'regon', 'adres']):
                continue
            if len(line) > 20:
                return line[:100]
        
        return None


# Singleton instance
_generator_instance: Optional[ExpenseJustificationGenerator] = None


def get_justification_generator() -> ExpenseJustificationGenerator:
    """Get or create justification generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ExpenseJustificationGenerator()
    return _generator_instance
