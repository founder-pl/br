# System Walidacji Dokumentów B+R - Architektura i Implementacja

## Wprowadzenie

Niniejszy artykuł opisuje architekturę systemu walidacji dokumentów B+R w projekcie BR Documentation Generator. System wykorzystuje wielopoziomowy pipeline walidacji z integracją LLM do oceny jakościowej.

---

## Architektura Pipeline'u

### Diagram Przepływu

```
┌─────────────────┐
│  Wygenerowany   │
│    Dokument     │
│   (Markdown)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   POZIOM 1:     │
│   Structure     │◄──── Sprawdza nagłówki, tabele, sekcje
│   Validator     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   POZIOM 2:     │
│    Content      │◄──── Weryfikuje kompletność danych
│   Validator     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   POZIOM 3:     │
│     Legal       │◄──── Sprawdza zgodność z ustawami
│   Validator     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   POZIOM 4:     │
│   Financial     │◄──── Waliduje obliczenia
│   Validator     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   POZIOM 5:     │
│   LLM Review    │◄──── AI ocena jakościowa
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validation     │
│    Result       │
│  (pass/fail)    │
└─────────────────┘
```

---

## Implementacja Walidatorów

### BaseValidator (Klasa Bazowa)

```python
# brgenerator/src/br_doc_generator/validators/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class IssueSeverity(str, Enum):
    ERROR = "error"      # Blokuje zatwierdzenie
    WARNING = "warning"  # Wymaga uwagi
    INFO = "info"        # Informacyjne

@dataclass
class ValidationIssue:
    severity: IssueSeverity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationContext:
    content: str
    project_input: 'ProjectInput'
    document_type: str
    costs: Optional[dict] = None
    llm_client: Optional['LLMClient'] = None

@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue]
    score: float  # 0.0 - 1.0
    stage: str

class BaseValidator(ABC):
    """Abstrakcyjna klasa bazowa dla walidatorów"""
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Nazwa etapu walidacji"""
        pass
    
    @property
    @abstractmethod
    def validation_criteria(self) -> List[str]:
        """Lista kryteriów walidacji"""
        pass
    
    @abstractmethod
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Główna metoda walidacji"""
        pass
    
    def _get_correction_instructions(self) -> str:
        """Instrukcje do poprawy dla LLM"""
        return ""
```

### StructureValidator

```python
# brgenerator/src/br_doc_generator/validators/structure.py

import re
from base import BaseValidator, ValidationContext, ValidationResult, ValidationIssue

class StructureValidator(BaseValidator):
    """Waliduje strukturę dokumentu Markdown"""
    
    REQUIRED_SECTIONS = {
        'project_card': ['IDENTYFIKACJA', 'OPIS', 'ZESPÓŁ', 'KOSZTY', 'ZATWIERDZENIE'],
        'expense_registry': ['EWIDENCJA', 'PODSUMOWANIE'],
        'nexus_calculation': ['SKŁADNIKI', 'OBLICZENIE', 'ZASTOSOWANIE'],
    }
    
    @property
    def stage_name(self) -> str:
        return "structure"
    
    @property
    def validation_criteria(self) -> List[str]:
        return [
            "Dokument zawiera wymagane sekcje",
            "Nagłówki są poprawnie sformatowane",
            "Tabele mają poprawną strukturę",
            "Brak pustych sekcji"
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        issues = []
        
        # 1. Sprawdź wymagane sekcje
        issues += self._check_required_sections(context)
        
        # 2. Sprawdź format nagłówków
        issues += self._check_headings(context.content)
        
        # 3. Sprawdź tabele
        issues += self._check_tables(context.content)
        
        # 4. Sprawdź puste sekcje
        issues += self._check_empty_sections(context.content)
        
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        
        return ValidationResult(
            valid=len(errors) == 0,
            issues=issues,
            score=1.0 - (len(issues) * 0.1),
            stage=self.stage_name
        )
    
    def _check_required_sections(self, context: ValidationContext) -> List[ValidationIssue]:
        issues = []
        doc_type = context.document_type
        required = self.REQUIRED_SECTIONS.get(doc_type, [])
        
        for section in required:
            pattern = rf'##?\s+.*{section}.*'
            if not re.search(pattern, context.content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message=f"Brak wymaganej sekcji: {section}",
                    suggestion=f"Dodaj sekcję '## {section}' do dokumentu"
                ))
        
        return issues
    
    def _check_headings(self, content: str) -> List[ValidationIssue]:
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Sprawdź czy jest spacja po #
                if re.match(r'^#+[^ #]', line):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        message=f"Brak spacji po # w linii {i+1}",
                        location=f"Linia {i+1}",
                        suggestion="Dodaj spację po znakach #"
                    ))
        
        return issues
    
    def _check_tables(self, content: str) -> List[ValidationIssue]:
        issues = []
        
        # Znajdź wszystkie tabele
        table_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|\n(\|[^\n]+\|\n)*'
        tables = re.findall(table_pattern, content)
        
        for table in tables:
            rows = table.strip().split('\n')
            if len(rows) < 2:
                continue
            
            header_cols = len(rows[0].split('|')) - 2
            for i, row in enumerate(rows[2:], start=3):
                row_cols = len(row.split('|')) - 2
                if row_cols != header_cols:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        message=f"Niezgodna liczba kolumn w tabeli",
                        location=f"Wiersz {i}",
                        suggestion=f"Tabela powinna mieć {header_cols} kolumn"
                    ))
        
        return issues
    
    def _check_empty_sections(self, content: str) -> List[ValidationIssue]:
        issues = []
        
        # Znajdź sekcje z pustą zawartością
        pattern = r'(^##?\s+[^\n]+)\n\n(##|\Z)'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        for match in matches:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                message=f"Pusta sekcja: {match[0].strip()}",
                suggestion="Uzupełnij treść sekcji lub usuń ją"
            ))
        
        return issues
```

### LegalComplianceValidator

```python
# brgenerator/src/br_doc_generator/validators/legal.py

import re
from base import BaseValidator, ValidationContext, ValidationResult, ValidationIssue

# Wymagania prawne B+R wg ustawy o CIT/PIT
BR_LEGAL_REQUIREMENTS = {
    "systematicity": {
        "description": "Systematyczność prowadzenia prac B+R",
        "keywords": ["systematycznie", "regularnie", "harmonogram", "etapy"]
    },
    "creativity": {
        "description": "Twórczy charakter działalności",
        "keywords": ["innowacyj", "nowość", "twórcz", "oryginaln"]
    },
    "knowledge": {
        "description": "Zwiększanie zasobów wiedzy",
        "keywords": ["wiedza", "badania", "rozwój", "nauka"]
    },
    "application": {
        "description": "Wykorzystanie wiedzy do nowych zastosowań",
        "keywords": ["zastosowanie", "wdrożenie", "implementacja", "produkt"]
    }
}

NIP_PATTERN = r'\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b|\b\d{10}\b'

class LegalComplianceValidator(BaseValidator):
    """Waliduje zgodność dokumentacji z wymogami prawnymi B+R"""
    
    @property
    def stage_name(self) -> str:
        return "legal"
    
    @property
    def validation_criteria(self) -> List[str]:
        return [
            "Dokumentacja spełnia kryteria B+R (art. 4a pkt 26 CIT)",
            "NIP jest poprawny (format i suma kontrolna)",
            "Kategorie kosztów są zgodne z ustawą",
            "Wymagane oświadczenia są obecne"
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        issues = []
        
        # 1. Sprawdź kryteria B+R
        issues += self._check_br_criteria(context.content)
        
        # 2. Sprawdź NIP
        issues += self._check_nip(context)
        
        # 3. Sprawdź kategorie kosztów
        issues += self._check_cost_categories(context.content)
        
        # 4. Sprawdź oświadczenia
        issues += self._check_declarations(context.content)
        
        # 5. Opcjonalnie: walidacja LLM
        if context.llm_client:
            issues += await self._llm_legal_validation(context)
        
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        
        return ValidationResult(
            valid=len(errors) == 0,
            issues=issues,
            score=self._calculate_score(issues, context),
            stage=self.stage_name
        )
    
    def _check_br_criteria(self, content: str) -> List[ValidationIssue]:
        issues = []
        content_lower = content.lower()
        
        for criterion, config in BR_LEGAL_REQUIREMENTS.items():
            found = any(kw in content_lower for kw in config["keywords"])
            if not found:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    message=f"Brak odniesienia do: {config['description']}",
                    suggestion=f"Dodaj opis dotyczący {criterion} w dokumentacji"
                ))
        
        return issues
    
    def _check_nip(self, context: ValidationContext) -> List[ValidationIssue]:
        issues = []
        
        # Znajdź NIP w dokumencie
        nips = re.findall(NIP_PATTERN, context.content)
        
        if not nips:
            # Sprawdź czy NIP jest w danych wejściowych
            if hasattr(context.project_input, 'company_nip'):
                nip = context.project_input.company_nip
                if not self._validate_nip_checksum(nip):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        message=f"Nieprawidłowy NIP: {nip}",
                        suggestion="Sprawdź poprawność numeru NIP"
                    ))
        else:
            for nip in nips:
                if not self._validate_nip_checksum(nip):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        message=f"Nieprawidłowy NIP w dokumencie: {nip}",
                        location="Dokument",
                        suggestion="Popraw numer NIP"
                    ))
        
        return issues
    
    def _validate_nip_checksum(self, nip: str) -> bool:
        """Walidacja sumy kontrolnej NIP"""
        # Usuń separatory
        nip_clean = re.sub(r'[-\s]', '', nip)
        
        if len(nip_clean) != 10 or not nip_clean.isdigit():
            return False
        
        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(nip_clean[i]) * weights[i] for i in range(9))
        control = checksum % 11
        
        return control == int(nip_clean[9])
    
    def _check_cost_categories(self, content: str) -> List[ValidationIssue]:
        issues = []
        
        valid_categories = [
            'wynagrodzenia', 'materiały', 'surowce', 'ekspertyzy',
            'opinie', 'usługi doradcze', 'sprzęt', 'oprogramowanie',
            'amortyzacja'
        ]
        
        content_lower = content.lower()
        
        # Sprawdź czy w dokumencie są wymienione kategorie
        found_categories = [cat for cat in valid_categories if cat in content_lower]
        
        if len(found_categories) == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                message="Brak wymienionych kategorii kosztów kwalifikowanych",
                suggestion="Dodaj podział kosztów na kategorie zgodnie z art. 18d CIT"
            ))
        
        return issues
    
    def _check_declarations(self, content: str) -> List[ValidationIssue]:
        issues = []
        
        required_declarations = [
            ('oświadczam', 'Brak oświadczenia'),
            ('zatwierdzam', 'Brak sekcji zatwierdzenia'),
            ('podpis', 'Brak miejsca na podpis')
        ]
        
        content_lower = content.lower()
        
        for keyword, message in required_declarations:
            if keyword not in content_lower:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    message=message,
                    suggestion=f"Rozważ dodanie sekcji z {keyword}"
                ))
        
        return issues
    
    async def _llm_legal_validation(self, context: ValidationContext) -> List[ValidationIssue]:
        """Walidacja prawna z wykorzystaniem LLM"""
        issues = []
        
        prompt = f"""Przeanalizuj poniższy dokument B+R pod kątem zgodności z polskim prawem podatkowym
(art. 18d ustawy o CIT, art. 26e ustawy o PIT).

Dokument:
{context.content[:3000]}

Oceń:
1. Czy działalność spełnia definicję B+R (twórczość, systematyczność, nowość)?
2. Czy kategorie kosztów są prawidłowe?
3. Czy dokumentacja jest kompletna?

Odpowiedz w formacie JSON:
{{"valid": true/false, "issues": ["issue1", "issue2"], "score": 0.0-1.0}}"""

        try:
            response = await context.llm_client.generate(prompt, temperature=0.2)
            result = json.loads(response)
            
            for issue_text in result.get('issues', []):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    message=f"[LLM] {issue_text}"
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                message=f"Nie udało się przeprowadzić walidacji LLM: {e}"
            ))
        
        return issues
```

### FinancialValidator

```python
# brgenerator/src/br_doc_generator/validators/financial.py

import re
from decimal import Decimal
from base import BaseValidator, ValidationContext, ValidationResult, ValidationIssue

class FinancialValidator(BaseValidator):
    """Waliduje obliczenia finansowe w dokumentacji"""
    
    @property
    def stage_name(self) -> str:
        return "financial"
    
    @property
    def validation_criteria(self) -> List[str]:
        return [
            "Sumy częściowe zgadzają się z sumą całkowitą",
            "Wskaźnik Nexus jest poprawnie obliczony (≤1.0)",
            "Kwoty są w poprawnym formacie",
            "Procenty zaangażowania nie przekraczają 100%"
        ]
    
    async def validate(self, context: ValidationContext) -> ValidationResult:
        issues = []
        
        # 1. Sprawdź sumy kosztów
        issues += self._validate_cost_totals(context.costs)
        
        # 2. Sprawdź obliczenia Nexus
        issues += self._validate_nexus(context)
        
        # 3. Sprawdź format kwot w dokumencie
        issues += self._check_document_amounts(context.content, context.costs)
        
        # 4. Sprawdź alokacje osobowe
        issues += self._check_personnel_allocations(context.costs)
        
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        
        return ValidationResult(
            valid=len(errors) == 0,
            issues=issues,
            score=1.0 - (len(errors) * 0.2),
            stage=self.stage_name
        )
    
    def _validate_cost_totals(self, costs: dict) -> List[ValidationIssue]:
        issues = []
        
        if not costs:
            return issues
        
        # Sprawdź sumowanie kategorii
        categories = costs.get('by_category', [])
        expected_total = sum(cat.get('total_gross', 0) for cat in categories)
        actual_total = costs.get('total_gross', 0)
        
        tolerance = Decimal('0.01')  # 1 grosz tolerancji
        if abs(Decimal(str(expected_total)) - Decimal(str(actual_total))) > tolerance:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Suma kategorii ({expected_total}) ≠ suma całkowita ({actual_total})",
                suggestion="Sprawdź obliczenia sum częściowych"
            ))
        
        return issues
    
    def _validate_nexus(self, context: ValidationContext) -> List[ValidationIssue]:
        issues = []
        
        if not context.costs:
            return issues
        
        nexus_data = context.costs.get('nexus', {})
        
        if not nexus_data:
            return issues
        
        a = Decimal(str(nexus_data.get('a_direct', 0)))
        b = Decimal(str(nexus_data.get('b_unrelated', 0)))
        c = Decimal(str(nexus_data.get('c_related', 0)))
        d = Decimal(str(nexus_data.get('d_ip', 0)))
        
        total = a + b + c + d
        
        if total == 0:
            # Nexus = 1 gdy brak kosztów
            expected_nexus = Decimal('1')
        else:
            expected_nexus = min(Decimal('1'), ((a + b) * Decimal('1.3')) / total)
        
        actual_nexus = Decimal(str(nexus_data.get('nexus', 0)))
        
        if abs(expected_nexus - actual_nexus) > Decimal('0.0001'):
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Błąd obliczenia Nexus: oczekiwano {expected_nexus:.4f}, jest {actual_nexus:.4f}",
                suggestion="Przelicz wskaźnik Nexus zgodnie ze wzorem"
            ))
        
        if actual_nexus > Decimal('1'):
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Nexus przekracza 1.0: {actual_nexus}",
                suggestion="Wskaźnik Nexus nie może przekraczać 1.0"
            ))
        
        return issues
    
    def _check_document_amounts(self, content: str, costs: dict) -> List[ValidationIssue]:
        issues = []
        
        # Znajdź wszystkie kwoty w dokumencie
        amount_pattern = r'(\d{1,3}(?:[\s\xa0]?\d{3})*(?:[,\.]\d{2})?)\s*(?:zł|PLN)'
        found_amounts = set()
        
        for match in re.finditer(amount_pattern, content):
            amount_str = match.group(1).replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                found_amounts.add(float(amount_str))
            except ValueError:
                pass
        
        # Sprawdź czy główne kwoty z costs są w dokumencie
        if costs:
            total_gross = costs.get('total_gross', 0)
            if total_gross > 0 and not self._amount_in_document(total_gross, found_amounts):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    message=f"Suma całkowita {total_gross} nie znaleziona w dokumencie"
                ))
        
        return issues
    
    def _amount_in_document(self, target: float, found_amounts: set, tolerance: float = 1.0) -> bool:
        """Sprawdź czy kwota jest w dokumencie (z tolerancją)"""
        return any(abs(target - amount) < tolerance for amount in found_amounts)
    
    def _check_personnel_allocations(self, costs: dict) -> List[ValidationIssue]:
        issues = []
        
        if not costs:
            return issues
        
        personnel = costs.get('personnel', [])
        
        for person in personnel:
            allocation = person.get('br_allocation_percent', 0)
            if allocation > 100:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message=f"Alokacja {person.get('name', 'N/A')} przekracza 100%: {allocation}%",
                    suggestion="Procent zaangażowania w B+R nie może przekraczać 100%"
                ))
        
        return issues
```

---

## ValidationPipeline

```python
# brgenerator/src/br_doc_generator/validators/pipeline.py

import asyncio
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from structure import StructureValidator
from content import ContentValidator  
from legal import LegalComplianceValidator
from financial import FinancialValidator

@dataclass
class PipelineResult:
    """Wynik całego pipeline'u walidacji"""
    overall_valid: bool
    overall_score: float
    results: List[ValidationResult]
    iterations: int
    corrections_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class ValidationPipeline:
    """Wielopoziomowy pipeline walidacji z iteracyjną poprawą"""
    
    def __init__(self, llm_client=None, config=None, use_llm: bool = True):
        self.llm_client = llm_client
        self.config = config or ValidationConfig()
        self.use_llm = use_llm
        
        # Inicjalizacja walidatorów w kolejności
        self.validators = [
            StructureValidator(),
            ContentValidator(),
            LegalComplianceValidator(),
            FinancialValidator()
        ]
        
        self.logger = structlog.get_logger()
    
    async def validate(
        self, 
        project_input: 'ProjectInput',
        markdown_content: str,
        levels: Optional[List[str]] = None,
        max_iterations: Optional[int] = None
    ) -> PipelineResult:
        """
        Uruchom pełny pipeline walidacji.
        
        Args:
            project_input: Dane wejściowe projektu
            markdown_content: Wygenerowany dokument Markdown
            levels: Opcjonalna lista poziomów do uruchomienia
            max_iterations: Max iteracji poprawy dla każdego poziomu
        
        Returns:
            PipelineResult z wszystkimi wynikami
        """
        max_iterations = max_iterations or self.config.max_iterations
        
        context = ValidationContext(
            content=markdown_content,
            project_input=project_input,
            document_type=project_input.template_id,
            costs=project_input.costs_data,
            llm_client=self.llm_client if self.use_llm else None
        )
        
        all_results = []
        total_iterations = 0
        corrections = []
        current_content = markdown_content
        
        # Filtruj walidatory jeśli podano levels
        validators_to_run = self.validators
        if levels:
            validators_to_run = [v for v in self.validators if v.stage_name in levels]
        
        for validator in validators_to_run:
            self.logger.info("validation_level_start", level=validator.stage_name)
            
            results, iterations, level_corrections = await self._run_validation_level(
                validator, context, max_iterations
            )
            
            all_results.extend(results)
            total_iterations += iterations
            corrections.extend(level_corrections)
            
            # Aktualizuj content jeśli były poprawki
            if level_corrections:
                context.content = current_content  # Zaktualizowany content
        
        # Oblicz wynik końcowy
        overall_valid = all(r.valid for r in all_results)
        overall_score = self._calculate_overall_score(all_results)
        
        return PipelineResult(
            overall_valid=overall_valid,
            overall_score=overall_score,
            results=all_results,
            iterations=total_iterations,
            corrections_applied=corrections
        )
    
    async def _run_validation_level(
        self,
        validator: BaseValidator,
        context: ValidationContext,
        max_iterations: int
    ) -> tuple[List[ValidationResult], int, List[str]]:
        """Uruchom pojedynczy poziom walidacji z iteracjami"""
        
        results = []
        corrections = []
        
        for iteration in range(max_iterations):
            result = await validator.validate(context)
            results.append(result)
            
            if result.valid:
                self.logger.info("validation_passed", 
                    level=validator.stage_name, 
                    iteration=iteration+1
                )
                break
            
            # Próba automatycznej poprawy przez LLM
            if self.llm_client and iteration < max_iterations - 1:
                correction = await self._attempt_correction(validator, context, result)
                if correction:
                    context.content = correction
                    corrections.append(f"{validator.stage_name}:iter{iteration+1}")
            
            self.logger.warning("validation_failed",
                level=validator.stage_name,
                iteration=iteration+1,
                issues=len(result.issues)
            )
        
        return results, len(results), corrections
    
    async def _attempt_correction(
        self,
        validator: BaseValidator,
        context: ValidationContext,
        result: ValidationResult
    ) -> Optional[str]:
        """Próba poprawy dokumentu przez LLM"""
        
        issues_text = "\n".join([f"- {i.message}" for i in result.issues[:5]])
        instructions = validator._get_correction_instructions()
        
        prompt = f"""Popraw poniższy dokument B+R zgodnie z wykrytymi problemami.

PROBLEMY DO POPRAWY:
{issues_text}

INSTRUKCJE:
{instructions}

DOKUMENT:
{context.content}

Zwróć TYLKO poprawiony dokument w formacie Markdown, bez dodatkowych wyjaśnień."""

        try:
            corrected = await self.llm_client.generate(prompt, temperature=0.2)
            return corrected
        except Exception as e:
            self.logger.error("correction_failed", error=str(e))
            return None
    
    def _calculate_overall_score(self, results: List[ValidationResult]) -> float:
        """Oblicz średni wynik ze wszystkich poziomów"""
        if not results:
            return 0.0
        return sum(r.score for r in results) / len(results)
```

---

## Konfiguracja LLM

### LLMClient

```python
# brgenerator/src/br_doc_generator/llm_client.py

import httpx
import os
from typing import Optional

class LLMClient:
    """Klient do komunikacji z OpenRouter API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
        self.base_url = base_url
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        """Generuj odpowiedź z modelu LLM"""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://founder.pl",
            "X-Title": "BR Documentation Generator"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]

def get_llm_client() -> LLMClient:
    """Singleton dla LLM client"""
    return LLMClient()
```

---

## Przykład Użycia

```python
import asyncio
from models import ProjectInput
from validators.pipeline import ValidationPipeline
from llm_client import get_llm_client

async def validate_document():
    # Przygotuj dane
    project = ProjectInput(
        template_id="project_card",
        project_name="System AI dla B+R",
        company_name="Softreck Sp. z o.o.",
        company_nip="1234567890",
        fiscal_year=2025
    )
    
    document = """
    # KARTA PROJEKTOWA B+R
    
    ## 1. IDENTYFIKACJA PROJEKTU
    ...
    """
    
    # Uruchom walidację
    pipeline = ValidationPipeline(
        llm_client=get_llm_client(),
        use_llm=True
    )
    
    result = await pipeline.validate(
        project_input=project,
        markdown_content=document,
        max_iterations=3
    )
    
    print(f"Valid: {result.overall_valid}")
    print(f"Score: {result.overall_score:.2f}")
    
    for r in result.results:
        print(f"  {r.stage}: {'✓' if r.valid else '✗'} (score: {r.score:.2f})")
        for issue in r.issues:
            print(f"    [{issue.severity}] {issue.message}")

if __name__ == "__main__":
    asyncio.run(validate_document())
```

---

## Podsumowanie

System walidacji dokumentów B+R wykorzystuje:

1. **5-poziomowy pipeline** - od struktury po ocenę LLM
2. **Iteracyjną poprawę** - automatyczne korekty przez AI
3. **Walidację prawną** - zgodność z polskimi przepisami
4. **Weryfikację finansową** - poprawność obliczeń Nexus

Model `nvidia/nemotron-3-nano-30b-a3b:free` jest używany z niską temperaturą (0.2-0.3) dla zapewnienia spójnych wyników w dokumentach prawno-finansowych.
