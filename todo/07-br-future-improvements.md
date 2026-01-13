# Projekt BR – Propozycje Dalszych Ulepszeń

**Data publikacji:** 2026-01-13  
**Kategoria:** Roadmap  
**Priorytet:** Średni-Niski  

## Przegląd

Po ukończeniu krytycznych modułów P0-P1, projekt BR wymaga dalszego rozwoju w obszarach: automatyzacji, monitoringu, UX i skalowalności.

## 1. Automatyzacja Pipeline'u

### 1.1 Pre-generation Hook

**Problem:** Użytkownik musi ręcznie uruchamiać walidację, kategoryzację i generowanie uzasadnień.

**Rozwiązanie:**

```python
# src/api/services/doc_generator.py

class DocumentGeneratorService:
    """Zintegrowany generator z auto-przetwarzaniem."""
    
    def __init__(
        self,
        expense_service: ExpenseService,
        categorizer: ExpenseCategorizer,
        justification_gen: JustificationGenerator,
        currency_conv: CurrencyConverter,
        validator: ExpensePipeline
    ):
        self.expense_service = expense_service
        self.categorizer = categorizer
        self.justification_gen = justification_gen
        self.currency_conv = currency_conv
        self.validator = validator
    
    async def generate_with_preprocessing(
        self,
        project_id: int,
        options: GenerationOptions
    ) -> GenerationResult:
        """Generuje raport z automatycznym przetworzeniem danych."""
        
        preprocessing_results = []
        
        # Step 1: Walidacja wszystkich wydatków
        if options.validate:
            validation = await self.validator.validate_all(project_id)
            preprocessing_results.append(("validation", validation))
        
        # Step 2: Konwersja walut
        if options.convert_currencies:
            conversions = await self.currency_conv.convert_all(project_id)
            preprocessing_results.append(("currency", conversions))
        
        # Step 3: Auto-kategoryzacja
        if options.categorize:
            categories = await self.categorizer.categorize_all(project_id)
            preprocessing_results.append(("categorization", categories))
        
        # Step 4: Generowanie uzasadnień
        if options.generate_justifications:
            justifications = await self.justification_gen.generate_all(project_id)
            preprocessing_results.append(("justifications", justifications))
        
        # Step 5: Generowanie raportu
        report = await self._generate_markdown(project_id)
        
        return GenerationResult(
            report=report,
            preprocessing=preprocessing_results,
            quality_score=self._calculate_quality(preprocessing_results)
        )
```

### 1.2 Scheduled Processing (Celery)

**Automatyczne przetwarzanie nowych wydatków w tle:**

```python
# src/infrastructure/tasks.py

from celery import shared_task
from celery.schedules import crontab

@shared_task
def process_pending_expenses():
    """Przetwarza wydatki oczekujące na klasyfikację."""
    pending = ExpenseService.get_pending()
    
    for expense in pending:
        try:
            # Kategoryzacja
            category = ExpenseCategorizer.categorize(expense)
            expense.category = category
            
            # Uzasadnienie
            justification = JustificationGenerator.generate(expense)
            expense.justification = justification
            
            # Konwersja waluty
            if expense.currency != "PLN":
                expense.amount_pln = CurrencyConverter.convert(
                    expense.amount, expense.currency, expense.date
                )
            
            expense.status = "classified"
            expense.save()
            
        except Exception as e:
            expense.status = "error"
            expense.error_message = str(e)
            expense.save()

# Harmonogram - co godzinę
app.conf.beat_schedule = {
    'process-pending-expenses': {
        'task': 'tasks.process_pending_expenses',
        'schedule': crontab(minute=0),  # Co godzinę
    },
}
```

## 2. Monitoring i Alerting

### 2.1 Quality Metrics Dashboard

**Metryki do śledzenia:**

```python
# src/api/services/metrics_collector.py

class QualityMetricsCollector:
    """Kolektor metryk jakości dokumentacji B+R."""
    
    METRICS = {
        "unique_justifications_ratio": "Procent unikalnych uzasadnień",
        "valid_invoices_ratio": "Procent prawidłowych numerów faktur",
        "pln_amounts_ratio": "Procent kwot w PLN",
        "classified_expenses_ratio": "Procent skategoryzowanych wydatków",
        "complete_vendors_ratio": "Procent wydatków z danymi dostawcy",
        "daily_timesheet_coverage": "Pokrycie dzienną ewidencją czasu",
        "uncertainty_section_present": "Obecność sekcji niepewności",
        "avg_justification_length": "Średnia długość uzasadnienia (słowa)",
    }
    
    async def collect(self, project_id: int) -> Dict[str, float]:
        expenses = await self.expense_service.get_all(project_id)
        
        return {
            "unique_justifications_ratio": self._calc_unique_ratio(expenses),
            "valid_invoices_ratio": self._calc_valid_invoices(expenses),
            "pln_amounts_ratio": self._calc_pln_ratio(expenses),
            "classified_expenses_ratio": self._calc_classified(expenses),
            "complete_vendors_ratio": self._calc_vendors(expenses),
            "daily_timesheet_coverage": await self._calc_timesheet_coverage(project_id),
            "uncertainty_section_present": await self._check_uncertainty(project_id),
            "avg_justification_length": self._calc_avg_justification(expenses),
        }
    
    def _calc_unique_ratio(self, expenses: List[Expense]) -> float:
        justifications = [e.justification for e in expenses if e.justification]
        unique = len(set(justifications))
        return unique / len(justifications) if justifications else 0.0
```

### 2.2 Prometheus Metrics

```python
# src/api/metrics.py

from prometheus_client import Counter, Gauge, Histogram

# Countery
expenses_processed = Counter(
    'br_expenses_processed_total',
    'Total number of processed expenses',
    ['status', 'category']
)

# Gauge'e
quality_score = Gauge(
    'br_quality_score',
    'Current quality score of documentation',
    ['project_id']
)

pending_expenses = Gauge(
    'br_pending_expenses',
    'Number of expenses pending classification'
)

# Histogramy
justification_generation_time = Histogram(
    'br_justification_generation_seconds',
    'Time spent generating justifications',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
```

### 2.3 Alerting Rules

```yaml
# prometheus/alerts.yml

groups:
  - name: br_quality
    rules:
      - alert: LowQualityScore
        expr: br_quality_score < 70
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Quality score below threshold"
          description: "Project {{ $labels.project_id }} has quality score {{ $value }}%"
      
      - alert: HighPendingExpenses
        expr: br_pending_expenses > 10
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Many expenses pending classification"
          description: "{{ $value }} expenses awaiting processing"
      
      - alert: DuplicateJustifications
        expr: br_unique_justifications_ratio < 0.9
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Duplicate justifications detected"
          description: "Only {{ $value | humanizePercentage }} unique justifications"
```

## 3. UX Improvements

### 3.1 Bulk Operations UI

```javascript
// web/static/js/bulk-operations.js

class BulkOperationsManager {
    constructor() {
        this.selectedExpenses = new Set();
    }
    
    async processSelected(operation) {
        const ids = Array.from(this.selectedExpenses);
        const progressBar = new ProgressBar(ids.length);
        
        for (const [index, id] of ids.entries()) {
            try {
                switch (operation) {
                    case 'categorize':
                        await fetch(`/expenses/${id}/categorize`, { method: 'POST' });
                        break;
                    case 'justify':
                        await fetch(`/expenses/${id}/generate-justification`, { method: 'POST' });
                        break;
                    case 'validate':
                        await fetch(`/expenses/${id}/validate`, { method: 'POST' });
                        break;
                }
                progressBar.update(index + 1);
            } catch (e) {
                console.error(`Failed to process ${id}:`, e);
            }
        }
        
        progressBar.complete();
        this.refreshTable();
    }
    
    renderBulkActionsToolbar() {
        return `
            <div class="bulk-actions" style="display: ${this.selectedExpenses.size > 0 ? 'flex' : 'none'}">
                <span class="selected-count">${this.selectedExpenses.size} zaznaczonych</span>
                <button onclick="bulkOps.processSelected('categorize')">
                    🏷️ Kategoryzuj
                </button>
                <button onclick="bulkOps.processSelected('justify')">
                    📝 Generuj uzasadnienia
                </button>
                <button onclick="bulkOps.processSelected('validate')">
                    ✓ Waliduj
                </button>
            </div>
        `;
    }
}
```

### 3.2 Quality Score Widget

```javascript
// web/static/js/quality-widget.js

async function renderQualityWidget(projectId) {
    const metrics = await fetch(`/projects/${projectId}/quality-metrics`).then(r => r.json());
    
    const overallScore = calculateOverallScore(metrics);
    const color = overallScore >= 80 ? '#22c55e' : overallScore >= 50 ? '#eab308' : '#ef4444';
    
    return `
        <div class="quality-widget">
            <div class="quality-score" style="border-color: ${color}">
                <span class="score-value">${overallScore}%</span>
                <span class="score-label">Jakość dokumentacji</span>
            </div>
            
            <div class="quality-breakdown">
                ${renderMetricBar('Unikalne uzasadnienia', metrics.unique_justifications_ratio)}
                ${renderMetricBar('Prawidłowe faktury', metrics.valid_invoices_ratio)}
                ${renderMetricBar('Kwoty w PLN', metrics.pln_amounts_ratio)}
                ${renderMetricBar('Skategoryzowane', metrics.classified_expenses_ratio)}
                ${renderMetricBar('Dane dostawców', metrics.complete_vendors_ratio)}
            </div>
            
            <button onclick="processAll(${projectId})" class="btn-process">
                🔄 Przetwórz wszystko
            </button>
        </div>
    `;
}
```

## 4. Skalowalność

### 4.1 Redis Caching dla Read Models

```python
# src/api/cache.py

import redis
import json
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, db=0)

def cached(ttl_seconds: int = 300):
    """Decorator dla cachowania wyników."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
            return result
        return wrapper
    return decorator

# Użycie
@cached(ttl_seconds=60)
async def get_project_summary(project_id: int) -> dict:
    """Podsumowanie projektu z cache."""
    return await ProjectService.get_summary(project_id)
```

### 4.2 Pagination dla Dużych List

```python
# src/api/routers/expenses.py

from fastapi import Query
from typing import Optional

class PaginatedResponse(BaseModel):
    items: List[ExpenseResponse]
    total: int
    page: int
    page_size: int
    pages: int

@router.get("/expenses", response_model=PaginatedResponse)
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista wydatków z paginacją i filtrami."""
    
    query = select(Expense)
    
    # Filtry
    if year:
        query = query.filter(extract('year', Expense.date) == year)
    if month:
        query = query.filter(extract('month', Expense.date) == month)
    if status:
        query = query.filter(Expense.status == status)
    if category:
        query = query.filter(Expense.category == category)
    
    # Total count
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    # Paginacja
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PaginatedResponse(
        items=[ExpenseResponse.from_orm(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )
```

## 5. Dokumentacja

### 5.1 Instrukcja Użytkownika (Outline)

```markdown
# System B+R - Instrukcja Użytkownika

## 1. Wprowadzenie
- Cel systemu
- Wymagania prawne ulgi B+R

## 2. Pierwsze kroki
- Logowanie
- Konfiguracja projektu
- Import danych z systemów księgowych

## 3. Zarządzanie wydatkami
- Dodawanie wydatków
- Import faktur (OCR)
- Kategoryzacja B+R
- Generowanie uzasadnień

## 4. Ewidencja czasu pracy
- Dzienny rejestr
- Integracja z Git
- Eksport do raportów

## 5. Generowanie dokumentacji
- Przygotowanie danych
- Walidacja jakości
- Eksport PDF/DOCX

## 6. Integracje
- KSeF
- JPK_V7M
- Systemy księgowe

## 7. Rozwiązywanie problemów
- FAQ
- Typowe błędy
```

### 5.2 Diagramy C4 (Propozycja)

**Context Diagram:**
- Użytkownik (Księgowy/Przedsiębiorca)
- System B+R
- KSeF, JPK, Systemy księgowe
- LLM API (Claude/OpenAI)

**Container Diagram:**
- Frontend (JS SPA)
- API (FastAPI)
- Database (PostgreSQL)
- Cache (Redis)
- Task Queue (Celery)
- OCR Service

**Component Diagram (API):**
- Routers
- Services
- Validators
- Integrations
- CQRS (Commands, Queries, Events)

## Podsumowanie Priorytetów

| Zadanie | Priorytet | Effort | Impact |
|---------|-----------|--------|--------|
| Auto-processing hook | 🔴 Wysoki | 2 dni | Krytyczny |
| Quality metrics dashboard | 🟡 Średni | 3 dni | Wysoki |
| Bulk operations UI | 🟡 Średni | 2 dni | Wysoki |
| Redis caching | 🟢 Niski | 1 dzień | Średni |
| Pagination | 🟢 Niski | 1 dzień | Średni |
| Prometheus metrics | 🟢 Niski | 2 dni | Średni |
| Instrukcja użytkownika | 🟢 Niski | 3 dni | Średni |
| Diagramy C4 | 🟢 Niski | 1 dzień | Niski |

---

*Propozycje ulepszeń dla projektu BR v2.0*
