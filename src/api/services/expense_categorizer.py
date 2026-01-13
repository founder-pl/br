"""
Automatic Expense Categorizer - ML-based B+R expense classification.

P2 Task: Automatyczna kategoryzacja wydatków
Based on: todo/05-br-priority-roadmap.md

Uses keyword matching and LLM fallback for intelligent categorization.
"""

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import httpx
import os
import structlog

logger = structlog.get_logger()


class BRCategory(str, Enum):
    """B+R expense categories per Polish tax law."""
    SALARIES = "wynagrodzenia"           # Art. 18d ust. 2 pkt 1
    MATERIALS = "materialy"              # Art. 18d ust. 2 pkt 2  
    EQUIPMENT = "aparatura"              # Art. 18d ust. 2 pkt 3
    EXTERNAL_SERVICES = "uslugi_obce"    # Art. 18d ust. 2 pkt 4
    EXPERT_OPINIONS = "ekspertyzy"       # Art. 18d ust. 2 pkt 4a
    IP_COSTS = "ip_box"                  # Art. 18d ust. 2 pkt 5
    OTHER = "inne"                       # Not qualified


@dataclass
class CategorizationResult:
    """Result of expense categorization."""
    category: BRCategory
    confidence: float
    keywords_matched: List[str]
    reason: str
    is_br_qualified: bool
    deduction_rate: float = 1.0


class ExpenseCategorizer:
    """
    Automatic expense categorizer for B+R qualification.
    
    Uses a two-stage approach:
    1. Fast keyword matching
    2. LLM fallback for ambiguous cases
    """
    
    # Category keyword mappings
    CATEGORY_KEYWORDS: Dict[BRCategory, List[str]] = {
        BRCategory.SALARIES: [
            "wynagrodzenie", "pensja", "premia", "zus", "składka",
            "umowa o pracę", "kontrakt", "developer", "programista",
            "inżynier", "analityk", "tester", "devops", "administrator"
        ],
        BRCategory.MATERIALS: [
            "materiał", "surowiec", "komponent", "część", "element",
            "licencja", "oprogramowanie", "software", "subscription",
            "subskrypcja", "saas", "paas", "iaas", "cloud"
        ],
        BRCategory.EQUIPMENT: [
            "sprzęt", "komputer", "laptop", "serwer", "monitor",
            "urządzenie", "maszyna", "aparatura", "hardware",
            "gpu", "cpu", "ram", "dysk", "ssd"
        ],
        BRCategory.EXTERNAL_SERVICES: [
            "usługa", "konsultacja", "doradztwo", "hosting", "serwer",
            "api", "integration", "zewnętrzny", "outsourcing",
            "freelancer", "b2b", "faktura", "zlecenie"
        ],
        BRCategory.EXPERT_OPINIONS: [
            "ekspertyza", "opinia", "audyt", "certyfikacja",
            "badanie", "analiza", "raport", "ocena"
        ],
        BRCategory.IP_COSTS: [
            "patent", "wzór użytkowy", "znak towarowy", "prawa autorskie",
            "know-how", "licencja wyłączna", "prawo ochronne"
        ]
    }
    
    # Vendor patterns for quick categorization
    VENDOR_PATTERNS: Dict[str, BRCategory] = {
        r"github|gitlab|bitbucket": BRCategory.MATERIALS,
        r"aws|amazon|azure|google cloud|gcp": BRCategory.EXTERNAL_SERVICES,
        r"digitalocean|linode|vultr|hetzner": BRCategory.EXTERNAL_SERVICES,
        r"openai|anthropic|hugging\s*face": BRCategory.EXTERNAL_SERVICES,
        r"jetbrains|intellij|pycharm|webstorm": BRCategory.MATERIALS,
        r"dell|hp|lenovo|apple": BRCategory.EQUIPMENT,
        r"komputronik|x-kom|morele": BRCategory.EQUIPMENT,
    }
    
    def __init__(self, llm_url: str = None):
        self.llm_url = llm_url or os.getenv("LLM_API_URL", "http://br-llm:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.2")
    
    def categorize(
        self,
        description: str,
        vendor_name: Optional[str] = None,
        amount: Optional[float] = None
    ) -> CategorizationResult:
        """
        Categorize an expense for B+R qualification.
        
        Args:
            description: Expense description or invoice text
            vendor_name: Vendor/supplier name
            amount: Expense amount (for threshold checks)
            
        Returns:
            CategorizationResult with category and confidence
        """
        text = f"{description or ''} {vendor_name or ''}".lower()
        
        # Stage 1: Vendor pattern matching
        if vendor_name:
            for pattern, category in self.VENDOR_PATTERNS.items():
                if re.search(pattern, vendor_name.lower()):
                    return CategorizationResult(
                        category=category,
                        confidence=0.9,
                        keywords_matched=[pattern],
                        reason=f"Rozpoznany dostawca pasujący do kategorii {category.value}",
                        is_br_qualified=True,
                        deduction_rate=1.0
                    )
        
        # Stage 2: Keyword matching
        category_scores: Dict[BRCategory, Tuple[int, List[str]]] = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text]
            if matched:
                category_scores[category] = (len(matched), matched)
        
        if category_scores:
            # Get best match
            best_category = max(category_scores.keys(), key=lambda c: category_scores[c][0])
            match_count, matched_keywords = category_scores[best_category]
            
            # Calculate confidence based on match count
            confidence = min(0.95, 0.5 + (match_count * 0.15))
            
            return CategorizationResult(
                category=best_category,
                confidence=confidence,
                keywords_matched=matched_keywords,
                reason=self._generate_reason(best_category, matched_keywords, vendor_name),
                is_br_qualified=True,
                deduction_rate=1.0
            )
        
        # No matches - return as "other" (not qualified)
        return CategorizationResult(
            category=BRCategory.OTHER,
            confidence=0.3,
            keywords_matched=[],
            reason="Nie rozpoznano kategorii B+R - wymaga ręcznej klasyfikacji",
            is_br_qualified=False,
            deduction_rate=0.0
        )
    
    async def categorize_with_llm(
        self,
        description: str,
        vendor_name: Optional[str] = None,
        ocr_text: Optional[str] = None
    ) -> CategorizationResult:
        """
        Categorize expense using LLM for complex cases.
        
        Falls back to keyword matching if LLM is unavailable.
        """
        # Try keyword matching first
        basic_result = self.categorize(description, vendor_name)
        if basic_result.confidence >= 0.8:
            return basic_result
        
        # Use LLM for ambiguous cases
        prompt = f"""Sklasyfikuj wydatek do kategorii B+R (działalność badawczo-rozwojowa).

OPIS: {description}
DOSTAWCA: {vendor_name or 'brak'}
TEKST OCR: {(ocr_text or '')[:500]}

KATEGORIE B+R:
1. wynagrodzenia - koszty pracowników B+R
2. materialy - materiały, licencje oprogramowania, subskrypcje
3. aparatura - sprzęt komputerowy, urządzenia badawcze
4. uslugi_obce - usługi zewnętrzne, hosting, API, konsultacje
5. ekspertyzy - ekspertyzy, opinie, certyfikacje
6. ip_box - koszty patentów, praw własności intelektualnej
7. inne - nie kwalifikuje się do B+R

Odpowiedz w formacie:
KATEGORIA: [nazwa]
KWALIFIKACJA_BR: [tak/nie]
UZASADNIENIE: [krótkie uzasadnienie]"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.llm_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 200}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    return self._parse_llm_response(result, basic_result)
                    
        except Exception as e:
            logger.warning("LLM categorization failed", error=str(e))
        
        # Return basic result as fallback
        return basic_result
    
    def _generate_reason(
        self,
        category: BRCategory,
        keywords: List[str],
        vendor_name: Optional[str]
    ) -> str:
        """Generate categorization reason."""
        category_names = {
            BRCategory.SALARIES: "Wynagrodzenia pracowników B+R",
            BRCategory.MATERIALS: "Materiały i licencje do prac B+R",
            BRCategory.EQUIPMENT: "Aparatura i sprzęt badawczy",
            BRCategory.EXTERNAL_SERVICES: "Usługi zewnętrzne wspierające B+R",
            BRCategory.EXPERT_OPINIONS: "Ekspertyzy i opinie specjalistyczne",
            BRCategory.IP_COSTS: "Koszty własności intelektualnej",
            BRCategory.OTHER: "Inne koszty"
        }
        
        base = category_names.get(category, "Koszt B+R")
        
        if vendor_name:
            base += f" od {vendor_name}"
        
        if keywords:
            base += f" (rozpoznano: {', '.join(keywords[:3])})"
        
        return base
    
    def _parse_llm_response(
        self,
        response: str,
        fallback: CategorizationResult
    ) -> CategorizationResult:
        """Parse LLM response into CategorizationResult."""
        try:
            lines = response.strip().split('\n')
            category_str = None
            is_qualified = False
            reason = ""
            
            for line in lines:
                if line.startswith("KATEGORIA:"):
                    category_str = line.replace("KATEGORIA:", "").strip().lower()
                elif line.startswith("KWALIFIKACJA_BR:"):
                    is_qualified = "tak" in line.lower()
                elif line.startswith("UZASADNIENIE:"):
                    reason = line.replace("UZASADNIENIE:", "").strip()
            
            # Map category string to enum
            category_map = {
                "wynagrodzenia": BRCategory.SALARIES,
                "materialy": BRCategory.MATERIALS,
                "aparatura": BRCategory.EQUIPMENT,
                "uslugi_obce": BRCategory.EXTERNAL_SERVICES,
                "ekspertyzy": BRCategory.EXPERT_OPINIONS,
                "ip_box": BRCategory.IP_COSTS,
                "inne": BRCategory.OTHER
            }
            
            category = category_map.get(category_str, BRCategory.OTHER)
            
            return CategorizationResult(
                category=category,
                confidence=0.75,
                keywords_matched=["llm"],
                reason=reason or fallback.reason,
                is_br_qualified=is_qualified,
                deduction_rate=1.0 if is_qualified else 0.0
            )
            
        except Exception:
            return fallback


# Singleton
_categorizer: Optional[ExpenseCategorizer] = None


def get_expense_categorizer() -> ExpenseCategorizer:
    """Get or create expense categorizer instance."""
    global _categorizer
    if _categorizer is None:
        _categorizer = ExpenseCategorizer()
    return _categorizer
