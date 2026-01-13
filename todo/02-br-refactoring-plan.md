# Plan Refaktoryzacji Systemu BR – Konkretne Kroki Implementacji

**Data publikacji:** 2026-01-13  
**Projekt:** BR Documentation Generator  
**Priorytet:** Wysoki  

## Cel Refaktoryzacji

Podniesienie jakości generowanych raportów B+R do poziomu zgodnego z wymogami prawnymi i oczekiwaniami organów skarbowych. Dokumentacja musi przejść weryfikację merytoryczną podczas potencjalnej kontroli.

## Faza 1: Naprawienie Krytycznych Błędów (Tydzień 1-2)

### 1.1 Indywidualizacja Uzasadnień Wydatków

**Lokalizacja:** `brgenerator/src/br_doc_generator/generators/document.py`

**Obecny problem:**
```python
# Wszystkie wydatki mają identyczny tekst uzasadnienia
uzasadnienie = "Wydatek związany z realizacją prac badawczo-rozwojowych..."
```

**Rozwiązanie – Implementacja LLM-based uzasadnień:**

```python
class ExpenseJustificationGenerator:
    """Generator indywidualnych uzasadnień dla wydatków B+R."""
    
    def generate_justification(
        self,
        expense: Expense,
        project_context: ProjectInput,
        br_tasks: List[BRTask]
    ) -> str:
        """
        Generuje unikalne uzasadnienie dla wydatku.
        
        Args:
            expense: Dane wydatku (faktura, kwota, kategoria)
            project_context: Kontekst projektu B+R
            br_tasks: Lista zadań B+R do powiązania
        
        Returns:
            Indywidualne uzasadnienie wydatku
        """
        prompt = self._build_justification_prompt(
            expense, project_context, br_tasks
        )
        return self.llm_client.generate(prompt)
    
    def _build_justification_prompt(self, expense, project, tasks) -> str:
        return f"""
        Wygeneruj profesjonalne uzasadnienie kwalifikacji B+R dla wydatku:
        
        WYDATEK:
        - Faktura: {expense.invoice_number}
        - Kwota: {expense.amount} {expense.currency}
        - Kategoria: {expense.category}
        - Dostawca: {expense.supplier_name}
        - Opis z faktury: {expense.description}
        
        KONTEKST PROJEKTU:
        - Nazwa: {project.name}
        - Cel: {project.objective}
        - Problem techniczny: {project.technical_problem}
        
        ZADANIA B+R DO POWIĄZANIA:
        {self._format_tasks(tasks)}
        
        WYMAGANIA:
        1. Opisz konkretny związek wydatku z zadaniem B+R
        2. Wskaż jak zakup przyczynił się do postępu prac
        3. Użyj specyficznych terminów technicznych
        4. Unikaj generycznych sformułowań
        5. Max 150 słów
        """
```

### 1.2 Walidacja i Konwersja Walut

**Lokalizacja:** `src/api/routers/expenses.py`

**Implementacja:**

```python
from decimal import Decimal
from datetime import date
import httpx

class CurrencyConverter:
    """Konwerter walut z cache'owaniem kursów NBP."""
    
    NBP_API = "https://api.nbp.pl/api/exchangerates/rates/a"
    
    async def convert_to_pln(
        self,
        amount: Decimal,
        currency: str,
        expense_date: date
    ) -> Decimal:
        """Przelicza kwotę na PLN według kursu NBP z dnia wydatku."""
        if currency.upper() == "PLN":
            return amount
        
        rate = await self._get_nbp_rate(currency, expense_date)
        return (amount * rate).quantize(Decimal("0.01"))
    
    async def _get_nbp_rate(self, currency: str, target_date: date) -> Decimal:
        """Pobiera kurs z API NBP (z fallback na poprzedni dzień roboczy)."""
        for days_back in range(7):
            check_date = target_date - timedelta(days=days_back)
            url = f"{self.NBP_API}/{currency}/{check_date.isoformat()}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return Decimal(str(data["rates"][0]["mid"]))
        
        raise ValueError(f"Nie znaleziono kursu {currency} dla {target_date}")
```

### 1.3 Walidacja Numerów Faktur

**Nowy moduł:** `src/api/validators/invoice_validator.py`

```python
import re
from typing import Optional, List
from pydantic import BaseModel

class InvoiceValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]
    normalized_number: Optional[str]
    warnings: List[str]

class InvoiceValidator:
    """Walidator numerów faktur zgodny z polskimi standardami."""
    
    GENERIC_PATTERNS = [
        r"^faktury?$",
        r"^sprzedaz[y]?$",
        r"^brak$",
        r"^none$",
        r"^\d{1,3}$",  # Zbyt krótkie numery
    ]
    
    VALID_PATTERNS = [
        r"^FV[/-]?\d{1,4}[/-]\d{2,4}[/-]\d{4}$",  # FV/123/01/2025
        r"^[A-Z]{2,10}[-_]?\d{4,}$",  # SVFOB8UM-0001
        r"^\d{1,4}/\d{1,2}/\d{4}$",  # 269/11/2025
    ]
    
    def validate(self, invoice_number: str) -> InvoiceValidationResult:
        errors = []
        warnings = []
        
        if not invoice_number or invoice_number.lower() == "none":
            errors.append("Brak numeru faktury")
            return InvoiceValidationResult(
                is_valid=False,
                errors=errors,
                normalized_number=None,
                warnings=warnings
            )
        
        # Sprawdź generyczne numery
        for pattern in self.GENERIC_PATTERNS:
            if re.match(pattern, invoice_number.lower()):
                errors.append(
                    f"Generyczny numer faktury: '{invoice_number}' - "
                    "wymaga uzupełnienia prawidłowym numerem"
                )
        
        # Sprawdź czy pasuje do znanego formatu
        normalized = invoice_number.strip().upper()
        is_valid_format = any(
            re.match(p, normalized, re.IGNORECASE)
            for p in self.VALID_PATTERNS
        )
        
        if not is_valid_format and not errors:
            warnings.append(
                f"Niestandardowy format numeru: '{invoice_number}'"
            )
        
        return InvoiceValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            normalized_number=normalized if not errors else None,
            warnings=warnings
        )
```

## Faza 2: Rozbudowa Struktury Dokumentacji (Tydzień 3-4)

### 2.1 Nowe Sekcje Dokumentacji

**Plik:** `brgenerator/src/br_doc_generator/models.py`

**Rozszerzenie modelu ProjectInput:**

```python
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum

class UncertaintyLevel(str, Enum):
    HIGH = "wysokie"
    MEDIUM = "średnie"
    LOW = "niskie"

class TechnicalProblem(BaseModel):
    """Opis problemu technicznego/naukowego."""
    description: str = Field(..., min_length=100)
    why_no_standard_solution: str
    required_knowledge_domains: List[str]
    uncertainty_factors: List[str]
    uncertainty_level: UncertaintyLevel

class ResearchMethodology(BaseModel):
    """Metodologia badawcza projektu."""
    approach: str  # np. "eksperymentalna", "iteracyjna", "prototypowa"
    phases: List[str]
    validation_methods: List[str]
    success_criteria: List[str]

class Milestone(BaseModel):
    """Kamień milowy projektu B+R."""
    name: str
    target_date: date
    actual_date: Optional[date] = None
    deliverables: List[str]
    status: str  # "completed", "in_progress", "planned"
    findings: Optional[str] = None

class RiskAnalysis(BaseModel):
    """Analiza ryzyka niepowodzenia (wymagana dla B+R)."""
    identified_risks: List[str]
    mitigation_strategies: List[str]
    actual_failures: List[str]  # Udokumentowane niepowodzenia
    lessons_learned: List[str]

class ProjectInputExtended(BaseModel):
    """Rozszerzony model projektu B+R."""
    # Podstawowe dane
    name: str
    code: str
    fiscal_year: int
    company_name: str
    company_nip: str
    
    # NOWE: Wymagane sekcje
    technical_problem: TechnicalProblem
    methodology: ResearchMethodology
    milestones: List[Milestone]
    risk_analysis: RiskAnalysis
    
    # Innowacyjność
    innovation_scope: str  # "firma", "rynek krajowy", "rynek globalny"
    innovation_description: str
    comparison_to_existing: str
    
    # Dane finansowe i kadrowe
    expenses: List[Expense]
    personnel: List[PersonnelEntry]
    time_entries: List[TimeEntry]
```

### 2.2 Generator Sekcji Niepewności Technologicznej

**Plik:** `brgenerator/src/br_doc_generator/generators/uncertainty.py`

```python
class UncertaintyGenerator:
    """Generator sekcji niepewności technologicznej."""
    
    UNCERTAINTY_PROMPT = """
    Na podstawie danych projektu wygeneruj sekcję dokumentacji B+R
    opisującą niepewność technologiczną:
    
    PROJEKT: {project_name}
    PROBLEM TECHNICZNY: {technical_problem}
    ZIDENTYFIKOWANE RYZYKA: {risks}
    FAKTYCZNE NIEPOWODZENIA: {failures}
    
    SEKCJA POWINNA ZAWIERAĆ:
    1. Opis elementów niepewności co do osiągnięcia rezultatu
    2. Dlaczego standardowe rozwiązania nie były wystarczające
    3. Jakie eksperymenty/testy przeprowadzono
    4. Jakie niepowodzenia wystąpiły i czego nauczyły
    5. Jak niepewność wpłynęła na kierunek prac
    
    FORMAT: Markdown z nagłówkami H3
    """
    
    def generate(self, project: ProjectInputExtended) -> str:
        prompt = self.UNCERTAINTY_PROMPT.format(
            project_name=project.name,
            technical_problem=project.technical_problem.description,
            risks="\n".join(f"- {r}" for r in project.risk_analysis.identified_risks),
            failures="\n".join(f"- {f}" for f in project.risk_analysis.actual_failures)
        )
        return self.llm_client.generate(prompt)
```

## Faza 3: Ewidencja Czasu Pracy (Tydzień 5-6)

### 3.1 Model Dziennego Rejestru

**Plik:** `src/api/models/timesheet.py`

```python
from pydantic import BaseModel, Field, validator
from datetime import date, time
from typing import Optional, List
from enum import Enum

class WorkCategory(str, Enum):
    APPLIED_RESEARCH = "badania_stosowane"
    DEVELOPMENT = "prace_rozwojowe"
    DOCUMENTATION = "dokumentacja"
    TESTING = "testowanie"
    PROTOTYPE = "prototypowanie"

class DailyTimeEntry(BaseModel):
    """Dzienny wpis ewidencji czasu pracy B+R."""
    
    date: date
    employee_name: str
    project_code: str
    task_id: str
    
    start_time: time
    end_time: time
    hours: float = Field(..., ge=0, le=24)
    
    category: WorkCategory
    description: str = Field(..., min_length=50)
    
    deliverables: Optional[List[str]] = None
    blockers: Optional[List[str]] = None
    
    @validator('description')
    def description_not_generic(cls, v):
        generic_phrases = [
            "prace badawczo-rozwojowe",
            "praca nad projektem",
            "kontynuacja prac",
        ]
        for phrase in generic_phrases:
            if v.lower().strip() == phrase:
                raise ValueError(
                    f"Opis '{v}' jest zbyt ogólny. "
                    "Wymagany szczegółowy opis wykonanych czynności."
                )
        return v

class TimesheetReport(BaseModel):
    """Raport ewidencji czasu dla dokumentacji B+R."""
    
    project_code: str
    period_start: date
    period_end: date
    entries: List[DailyTimeEntry]
    
    @property
    def total_hours(self) -> float:
        return sum(e.hours for e in self.entries)
    
    @property
    def hours_by_category(self) -> dict:
        result = {}
        for entry in self.entries:
            cat = entry.category.value
            result[cat] = result.get(cat, 0) + entry.hours
        return result
    
    @property
    def hours_by_employee(self) -> dict:
        result = {}
        for entry in self.entries:
            result[entry.employee_name] = (
                result.get(entry.employee_name, 0) + entry.hours
            )
        return result
```

### 3.2 Integracja z Git dla Automatycznej Ewidencji

**Rozbudowa:** `src/api/routers/git_timesheet.py`

```python
class GitTimesheetEnhancer:
    """Wzbogacanie ewidencji czasu na podstawie commitów Git."""
    
    async def enrich_timesheet(
        self,
        entries: List[DailyTimeEntry],
        repo_path: str
    ) -> List[DailyTimeEntry]:
        """
        Wzbogaca wpisy ewidencji o dane z Git.
        
        - Dodaje linki do commitów jako dowody pracy
        - Uzupełnia opisy o informacje z commit messages
        - Waliduje spójność dat z historią Git
        """
        git_log = await self._get_git_log(repo_path)
        
        for entry in entries:
            matching_commits = self._find_commits_for_date(
                git_log, entry.date, entry.employee_name
            )
            if matching_commits:
                entry.deliverables = entry.deliverables or []
                entry.deliverables.extend([
                    f"Commit {c.sha[:8]}: {c.message}"
                    for c in matching_commits
                ])
        
        return entries
```

## Faza 4: Pipeline Walidacji (Tydzień 7-8)

### 4.1 Rozszerzenie Walidatora Prawnego

**Plik:** `brgenerator/src/br_doc_generator/validators/legal.py`

**Dodatkowe reguły walidacji:**

```python
class LegalComplianceValidatorExtended(LegalComplianceValidator):
    """Rozszerzony walidator zgodności prawnej."""
    
    BR_REQUIRED_SECTIONS = {
        "technical_problem": {
            "min_length": 200,
            "required_keywords": ["problem", "wyzwanie", "trudność"],
            "error": "Brak opisu problemu technicznego"
        },
        "methodology": {
            "min_length": 150,
            "required_keywords": ["metoda", "podejście", "proces"],
            "error": "Brak opisu metodologii badawczej"
        },
        "uncertainty": {
            "min_length": 100,
            "required_keywords": ["niepewność", "ryzyko", "niepowodzenie"],
            "error": "KRYTYCZNE: Brak sekcji niepewności technologicznej"
        },
        "innovation": {
            "min_length": 100,
            "required_keywords": ["innowacja", "nowe", "ulepszone"],
            "error": "Brak opisu innowacyjności"
        }
    }
    
    def _check_required_sections(self, content: str) -> List[ValidationIssue]:
        issues = []
        
        for section, rules in self.BR_REQUIRED_SECTIONS.items():
            section_content = self._extract_section(content, section)
            
            if not section_content:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message=rules["error"],
                    location=section,
                    suggestion=f"Dodaj sekcję {section} z min. {rules['min_length']} znaków"
                ))
                continue
            
            if len(section_content) < rules["min_length"]:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    message=f"Sekcja {section} zbyt krótka ({len(section_content)} < {rules['min_length']})",
                    location=section
                ))
            
            # Sprawdź obecność kluczowych słów
            has_keywords = any(
                kw in section_content.lower()
                for kw in rules["required_keywords"]
            )
            if not has_keywords:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    message=f"Sekcja {section} może nie zawierać wymaganej treści",
                    location=section,
                    suggestion=f"Uwzględnij: {', '.join(rules['required_keywords'])}"
                ))
        
        return issues
    
    def _check_expense_justifications(
        self,
        expenses: List[Expense]
    ) -> List[ValidationIssue]:
        """Sprawdza unikalność uzasadnień wydatków."""
        issues = []
        justifications = [e.justification for e in expenses if e.justification]
        
        # Znajdź duplikaty
        seen = set()
        duplicates = []
        for j in justifications:
            normalized = j.strip().lower()[:100]
            if normalized in seen:
                duplicates.append(j[:50])
            seen.add(normalized)
        
        if duplicates:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Znaleziono {len(duplicates)} powtórzonych uzasadnień wydatków",
                location="expenses",
                suggestion="Każdy wydatek wymaga indywidualnego uzasadnienia"
            ))
        
        return issues
```

## Harmonogram Wdrożenia

| Faza | Tydzień | Zadania | Priorytet |
|------|---------|---------|-----------|
| 1 | 1-2 | Indywidualizacja uzasadnień, walidacja walut/faktur | Krytyczny |
| 2 | 3-4 | Nowe sekcje dokumentacji, generator niepewności | Wysoki |
| 3 | 5-6 | Ewidencja czasu pracy, integracja Git | Wysoki |
| 4 | 7-8 | Rozszerzenie pipeline'u walidacji | Średni |

## Metryki Sukcesu

1. **Unikalność uzasadnień:** 100% wydatków z indywidualnym opisem
2. **Kompletność sekcji:** Wszystkie wymagane sekcje obecne i zwalidowane
3. **Spójność danych:** 0 błędów walidacji walut i numerów faktur
4. **Ewidencja czasu:** Każdy dzień pracy z opisem >50 znaków
5. **Ocena walidatora:** Minimalny wynik 80% na wszystkich poziomach

---

*Plan refaktoryzacji opracowany na podstawie analizy projektu BR v1.0*
