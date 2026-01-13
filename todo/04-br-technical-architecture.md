# Architektura Projektu BR – Przegląd Techniczny i Propozycje Ulepszeń

**Data publikacji:** 2026-01-13  
**Projekt:** BR Documentation Generator  
**Wersja analizy:** 1.0  

## Przegląd Architektury

System BR to modułowa aplikacja Python do automatycznego generowania dokumentacji ulgi B+R. Architektura oparta jest o wzorzec warstwowy z wyraźnym podziałem odpowiedzialności.

### Struktura Projektu

```
br/
├── src/
│   ├── api/                    # REST API (FastAPI)
│   │   ├── routers/           # Endpointy HTTP
│   │   ├── services/          # Logika biznesowa
│   │   └── cqrs/              # Command/Query segregation
│   ├── ocr/                   # Ekstrakcja danych z faktur
│   ├── integrations/          # Systemy zewnętrzne
│   │   ├── accounting/        # Fakturownia, wFirma, iFirma
│   │   ├── cloud/             # Dropbox, Google Drive, S3
│   │   └── config/            # Konfiguracja integracji
│   └── infrastructure/        # Celery, zadania w tle
├── brgenerator/               # Generator dokumentacji
│   └── src/br_doc_generator/
│       ├── generators/        # Generatory dokumentów
│       ├── validators/        # Pipeline walidacji
│       ├── models.py          # Modele danych
│       └── llm_client.py      # Integracja LLM
├── web/                       # Frontend (JS/HTML)
└── tests/                     # Testy (unit, integration, e2e)
```

### Statystyki Kodu

| Komponent | Pliki | Linie | % całości |
|-----------|-------|-------|-----------|
| API (routers) | 12 | 4,248 | 15.1% |
| API (services) | 1 | 695 | 2.5% |
| OCR | 6 | 968 | 3.4% |
| Integracje | 12 | 2,888 | 10.2% |
| BR Generator | 13 | 4,084 | 14.5% |
| Testy | 18 | 3,237 | 11.5% |
| Frontend JS | 2 | 2,891 | 10.3% |
| Inne | 26 | 9,165 | 32.5% |
| **RAZEM** | **90** | **28,176** | **100%** |

## Analiza Komponentów

### 1. REST API (`src/api/`)

**Router wydatków** (`expenses.py` – 1,090 linii) jest największym plikiem w projekcie. Zawiera:
- CRUD dla wydatków
- Import z CSV
- Klasyfikacja kategorii B+R
- Walidacja NIP

**Problem:** Nadmierna złożoność jednego pliku. Rekomendacja: podział na mniejsze moduły.

**Proponowana struktura:**
```
src/api/routers/expenses/
├── __init__.py
├── crud.py           # Podstawowe operacje
├── import_csv.py     # Import z plików
├── classification.py # Klasyfikacja B+R
├── validation.py     # Walidacja danych
└── reports.py        # Raporty wydatków
```

### 2. Pipeline Walidacji (`brgenerator/validators/`)

**Obecna architektura:**
```
BaseValidator (abstract)
    ├── StructureValidator    # Walidacja struktury dokumentu
    ├── ContentValidator      # Walidacja treści
    ├── LegalComplianceValidator  # Zgodność prawna
    └── FinancialValidator    # Walidacja finansowa

ValidationPipeline → orchestruje walidatory
```

**Mocne strony:**
- Czysta separacja odpowiedzialności
- Łatwe dodawanie nowych walidatorów
- Iteracyjne poprawki z LLM

**Słabości zidentyfikowane:**
- Brak walidacji unikalności uzasadnień wydatków
- Niewystarczająca walidacja sekcji niepewności
- Brak integracji z zewnętrznymi źródłami (np. API NBP dla kursów walut)

### 3. Generator Dokumentów (`brgenerator/generators/`)

**Komponenty:**
- `DocumentGenerator` – generowanie Markdown z LLM
- `FormGenerator` – szablony YAML do wypełnienia
- `PDFRenderer` – konwersja do PDF (WeasyPrint)

**Problem w `DocumentGenerator`:**
```python
# Obecny kod - wszystkie wydatki mają identyczny prompt
def _build_costs_prompt(self, project_input: ProjectInput) -> str:
    # Brak indywidualizacji per wydatek
    return f"""
    Wygeneruj sekcję kosztów dla projektu {project_input.name}
    Wydatki: {self._format_expenses(project_input.expenses)}
    """
```

**Propozycja naprawy:**
```python
def _build_expense_justification_prompt(
    self,
    expense: Expense,
    project_context: ProjectInput,
    related_tasks: List[BRTask]
) -> str:
    return f"""
    Wygeneruj UNIKALNE uzasadnienie dla wydatku:
    
    FAKTURA: {expense.invoice_number}
    DOSTAWCA: {expense.supplier_name}
    KWOTA: {expense.amount} {expense.currency}
    OPIS Z FAKTURY: {expense.original_description}
    
    POWIĄZANE ZADANIA B+R:
    {self._format_related_tasks(related_tasks)}
    
    KONTEKST PROJEKTU:
    - Problem techniczny: {project_context.technical_problem}
    - Metodologia: {project_context.methodology}
    
    WYMAGANIA:
    1. Opisz KONKRETNY związek z zadaniem B+R
    2. Użyj specyficznych terminów technicznych
    3. Wskaż jak zakup przyczynił się do postępu
    4. NIE używaj generycznych sformułowań
    5. Min. 80 słów, max. 150 słów
    """
```

### 4. OCR i Ekstrakcja (`src/ocr/`)

**Architektura:**
```
OcrEngine (abstract)
    ├── TesseractEngine
    ├── GoogleVisionEngine
    └── AzureFormRecognizerEngine

InvoiceExtractor
    ├── extract_invoice_number()
    ├── extract_nip()
    ├── extract_amounts()
    └── extract_line_items()
```

**Problem:** Brak walidacji wyekstrahowanych danych przed zapisem.

**Propozycja – dodanie warstwy walidacji:**
```python
class ExtractedDataValidator:
    """Walidacja danych wyekstrahowanych przez OCR."""
    
    def validate_extraction(
        self,
        extracted: ExtractedInvoice
    ) -> ValidationResult:
        issues = []
        
        # Walidacja NIP
        if extracted.supplier_nip:
            if not self._validate_nip_checksum(extracted.supplier_nip):
                issues.append(Issue(
                    field="supplier_nip",
                    message="Nieprawidłowa suma kontrolna NIP",
                    severity="error"
                ))
        
        # Walidacja numeru faktury
        invoice_validation = InvoiceValidator().validate(
            extracted.invoice_number
        )
        issues.extend(invoice_validation.issues)
        
        # Walidacja kwot
        if extracted.total_gross and extracted.total_net:
            expected_vat = extracted.total_gross - extracted.total_net
            if abs(expected_vat - extracted.vat_amount) > 0.01:
                issues.append(Issue(
                    field="amounts",
                    message="Niespójność kwot: VAT nie zgadza się z różnicą brutto-netto",
                    severity="warning"
                ))
        
        return ValidationResult(
            is_valid=not any(i.severity == "error" for i in issues),
            issues=issues
        )
```

### 5. Integracje z Systemami Księgowymi

**Wspierane systemy:**
- Fakturownia (`fakturownia.py` – 232 linie)
- wFirma / InFakt (`wfirma_infakt.py` – 308 linii)
- iFirma (`ifirma.py` – 189 linii)

**Architektura:**
```python
class AccountingIntegration(ABC):
    """Bazowa klasa dla integracji księgowych."""
    
    @abstractmethod
    async def fetch_invoices(
        self,
        date_from: date,
        date_to: date
    ) -> List[Invoice]:
        pass
    
    @abstractmethod
    async def sync_expenses(
        self,
        expenses: List[Expense]
    ) -> SyncResult:
        pass
```

**Propozycja ulepszenia – automatyczna kategoryzacja:**
```python
class SmartAccountingIntegration(AccountingIntegration):
    """Integracja z automatyczną kategoryzacją B+R."""
    
    async def fetch_and_classify(
        self,
        date_from: date,
        date_to: date,
        project_context: ProjectInput
    ) -> List[ClassifiedExpense]:
        invoices = await self.fetch_invoices(date_from, date_to)
        
        classified = []
        for invoice in invoices:
            classification = await self.classifier.classify(
                invoice=invoice,
                project_context=project_context
            )
            classified.append(ClassifiedExpense(
                invoice=invoice,
                br_category=classification.category,
                qualification_score=classification.score,
                suggested_justification=classification.justification
            ))
        
        return classified
```

## Propozycje Architektoniczne

### 1. Event Sourcing dla Audit Trail

Dla dokumentacji B+R kluczowa jest możliwość udowodnienia, że ewidencja była prowadzona na bieżąco.

```python
class ExpenseEvent(BaseModel):
    """Event dla historii wydatku."""
    event_id: UUID
    expense_id: UUID
    event_type: str  # "created", "classified", "justified", "validated"
    timestamp: datetime
    user_id: str
    data: dict
    
class ExpenseEventStore:
    """Magazyn zdarzeń dla wydatków."""
    
    async def append(self, event: ExpenseEvent) -> None:
        # Immutable append-only store
        pass
    
    async def get_history(self, expense_id: UUID) -> List[ExpenseEvent]:
        # Pełna historia zmian
        pass
    
    async def reconstruct_state(
        self,
        expense_id: UUID,
        as_of: datetime
    ) -> Expense:
        # Stan wydatku na konkretną datę
        pass
```

### 2. Plugin Architecture dla Walidatorów

Umożliwienie łatwego dodawania custom walidatorów bez modyfikacji core code.

```python
class ValidatorPlugin(Protocol):
    """Protokół dla pluginów walidacji."""
    
    @property
    def name(self) -> str: ...
    
    @property
    def priority(self) -> int: ...
    
    async def validate(
        self,
        context: ValidationContext
    ) -> ValidationResult: ...

class ValidatorRegistry:
    """Rejestr pluginów walidacji."""
    
    def __init__(self):
        self._plugins: List[ValidatorPlugin] = []
    
    def register(self, plugin: ValidatorPlugin) -> None:
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority)
    
    def discover_plugins(self, package: str) -> None:
        """Auto-discovery pluginów z pakietu."""
        # Skanowanie entry_points lub katalogu
        pass
```

### 3. Separation of Concerns w Generatorze

Obecny `DocumentGenerator` łączy zbyt wiele odpowiedzialności. Propozycja:

```
DocumentGenerationPipeline
    ├── DataCollector          # Zbieranie danych wejściowych
    ├── ContentPlanner         # Planowanie struktury dokumentu
    ├── SectionGenerators/     # Generatory per sekcja
    │   ├── SummaryGenerator
    │   ├── MethodologyGenerator
    │   ├── ExpenseJustificationGenerator
    │   ├── UncertaintyGenerator
    │   └── ConclusionsGenerator
    ├── ContentAssembler       # Składanie dokumentu
    ├── QualityChecker         # Sprawdzanie jakości
    └── FormatRenderer         # Renderowanie do formatu docelowego
```

## Metryki Jakości Kodu

### Obecne problemy:
- Cyklomatyczna złożoność `expenses.py`: ~35 (rekomendowane <10)
- Długość plików: 4 pliki >500 linii (rekomendowane <300)
- Pokrycie testami: nieznane (brak badge'a)

### Cele refaktoryzacji:
- Max. złożoność cyklomatyczna: 10
- Max. długość pliku: 300 linii
- Pokrycie testami: >80%
- Dokumentacja API: 100% publicznych funkcji

## Roadmap Techniczny

| Faza | Cel | Estymacja |
|------|-----|-----------|
| 1 | Podział `expenses.py` na moduły | 2 dni |
| 2 | Event sourcing dla audit trail | 5 dni |
| 3 | Plugin architecture dla walidatorów | 3 dni |
| 4 | Refaktoryzacja `DocumentGenerator` | 5 dni |
| 5 | Walidacja danych OCR | 3 dni |
| 6 | Automatyczna kategoryzacja B+R | 5 dni |
| **RAZEM** | | **23 dni** |

## Podsumowanie

Projekt BR ma solidne fundamenty architektoniczne, ale wymaga refaktoryzacji w obszarach:

1. **Modularyzacja** – podział dużych plików
2. **Audit trail** – event sourcing dla zgodności prawnej
3. **Indywidualizacja** – unikalne uzasadnienia wydatków
4. **Walidacja** – rozszerzenie pipeline'u o brakujące reguły
5. **Automatyzacja** – smart classification i auto-categorization

Implementacja proponowanych zmian znacząco podniesie jakość generowanej dokumentacji i jej zgodność z wymogami kontroli skarbowej.

---

*Analiza techniczna projektu BR v1.0 oparta na pliku project.toon*
