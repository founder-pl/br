# TODO - System B+R

## Priorytet: Krytyczny P0 🔴 (Tydzień 1-2)

### Jakość Dokumentacji B+R
- [x] **Walidacja numerów faktur** ✅
  - Moduł `src/api/validators/invoice_validator.py`
  - Wykrywanie generycznych numerów ("faktury", "sprzedazy")
  - Endpoint `/expenses/validate-invoice`
  - 37 testów jednostkowych
- [x] **Konwersja walut USD→PLN** ✅
  - Moduł `src/api/validators/currency_converter.py`
  - API NBP z fallback na poprzednie dni
  - Endpoint `/expenses/convert-currency`
- [x] **Walidacja zbiorcza wydatków** ✅
  - Endpoint `/expenses/validate-all`
  - Sprawdza: faktury, dostawców, waluty
- [x] **Indywidualizacja uzasadnień wydatków** ✅
  - Moduł `src/api/services/justification_generator.py`
  - Endpoint `/expenses/{id}/generate-justification`
  - LLM-based z template fallback
- [x] **Uzupełnienie brakujących danych dostawców** ✅
  - Endpoint `/expenses/{id}/vendor`
  - Walidacja NIP przy aktualizacji

### Frontend
- [x] **Filtrowanie wydatków po miesiącach** ✅
- [x] **Szczegóły miesiąca z raportów** ✅
- [x] **Git Timesheet - wybór pracownika** ✅
- [x] **Fix TypeError na stronie upload** ✅

### Backend  
- [x] **Testy git-timesheet** ✅ (8 passed)
- [x] **Fix git-timesheet work_date** ✅ (string→date)
- [x] **Fix usuwania wydatków** ✅ (db.commit)
- [ ] **Walidacja ścieżek** w git-timesheet

## Priorytet: Wysoki P1 🟠 (Tydzień 3-4)

### Struktura Dokumentacji
- [x] **Sekcja niepewności technologicznej** ✅
  - Moduł `src/api/services/uncertainty_generator.py`
  - Endpoint `/projects/{id}/generate-uncertainty`
  - Min. 100 słów, 6+ słów kluczowych
- [x] **Rozbudowa opisu projektu** ✅
  - Model `src/api/models/project_extended.py`
  - TechnicalProblem, ResearchMethodology, RiskAnalysis
  - Domyślne szablony dla szybkiego startu
- [x] **Dzienny rejestr czasu pracy** ✅
  - Model `src/api/models/daily_time_entry.py`
  - Endpoint `/timesheet/entries/validated`
  - Walidacja: min. 50 znaków, słowa kluczowe B+R
- [x] **Integracja Git z ewidencją** ✅
  - Model GitCommitLink do powiązania commitów
  - Walidacja obecności dowodów (warnings)

## Priorytet: Średni 🟡

### Refaktoryzacja ✅
- [x] **Modularyzacja expenses.py (1702 LOC)** ✅
  - Package `src/api/routers/expenses/`
  - 6 modułów: models, crud, validation, classification, revenues, documentation
- [x] **Modularyzacja documents.py (1087 LOC)** ✅
  - Package `src/api/routers/documents/`
  - 5 modułów: models, upload, crud, notes, extraction
- [x] **Modularyzacja templates.py (1001 LOC)** ✅
  - Package `src/doc_generator/templates/`
  - 6 modułów: base, registry, project, financial, tax, legal
- [x] **Modularyzacja app.js (4072 LOC)** ✅
  - Directory `web/static/js/modules/`
  - 8 modułów: core, dashboard, projects, reports, upload, doc-generator, config, logs
- [x] **Modularyzacja doc_generator.py (996 LOC)** ✅
  - Package `src/api/services/doc_generator/`
  - 6 modułów: version_control, prompts, llm, templates, generator, __init__

### CQRS/Event Sourcing
- [x] **Pipeline walidacji wydatków** ✅
  - Moduł `src/api/validators/expense_pipeline.py`
  - Endpoint `/expenses/validate-pipeline`
  - Quality score 0-100, kategorie błędów
- [x] **Automatyczna kategoryzacja wydatków** ✅
  - Moduł `src/api/services/expense_categorizer.py`
  - Endpoint `/expenses/categorize`
  - Keyword matching + LLM fallback
- [x] **Event sourcing audit trail** ✅
  - Moduł `src/api/services/audit_trail.py`
  - Śledzenie zmian dla kontroli skarbowej
- [ ] **Saga pattern** dla złożonych operacji
  - Transakcje rozproszone
  - Kompensacje przy błędach
- [ ] **Projekcje asynchroniczne**
  - Background workers
  - Event handlers

### Integracje
- [x] **KSeF integration** ✅
  - Moduł `src/api/integrations/ksef_client.py`
  - Endpoint `/integrations/ksef/import`
  - Pobieranie faktur zakupowych i sprzedażowych
- [x] **JPK_V7M export** ✅
  - Moduł `src/api/integrations/jpk_export.py`
  - Endpoint `/integrations/jpk/generate`
  - Endpoint `/integrations/jpk/download`
  - Walidacja zgodności ze schematem MF

### Dokumentacja
- [x] **Dokumentacja API** (OpenAPI/Swagger) ✅
  - Rozszerzona dokumentacja w `/docs` i `/redoc`
  - Tagi dla wszystkich modułów
  - Opisy endpointów P0-P3
- [ ] **Instrukcja użytkownika**
- [ ] **Diagramy architektury** (C4, sequence)

## Priorytet: Niski 🟢

### UI/UX
- [ ] **Dark mode toggle**
- [ ] **Drag & drop** dla modułów dashboard
- [x] **Eksport do Excel** ✅
  - Moduł `src/api/services/excel_exporter.py`
  - Endpoint `/reports/export/expenses`
  - Endpoint `/reports/export/monthly`
- [ ] **Powiadomienia push** (WebSocket)

### Performance
- [ ] **Caching** (Redis dla read models)
- [ ] **Pagination** w listach
- [ ] **Lazy loading** dla dużych zestawów

### DevOps
- [x] **CI/CD pipeline** (GitHub Actions) ✅
  - Plik `.github/workflows/ci.yml`
  - Lint, test, build, deploy stages
  - Docker image push to GHCR
- [ ] **Staging environment**
- [ ] **Monitoring** (Prometheus/Grafana)
- [ ] **Log aggregation** (ELK stack)

## Zakończone ✅

### 2026-01-14
- [x] Refaktoryzacja expenses.py → 6 modułów (1702→1580 LOC)
- [x] Refaktoryzacja documents.py → 5 modułów (1087→878 LOC)
- [x] Refaktoryzacja templates.py → 6 modułów (1001→926 LOC)
- [x] Refaktoryzacja app.js → 8 modułów (4072→~1423 LOC)
- [x] Refaktoryzacja doc_generator.py → 6 modułów (996→1088 LOC)
- [x] Aktualizacja importów w main.py
- [x] Testy API: 126 endpointów OK
- [x] Testy templates: 8 szablonów loaded
- [x] Fix import detect_invoice_type (backward compatibility)
- [x] Fix OCR text hint detection dla faktur sprzedaży
- [x] **185 passed, 17 skipped** (pytest)

### 2026-01-13
- [x] Modularny dashboard 4x4
- [x] Edycja danych OCR
- [x] Tworzenie wydatków z dokumentów
- [x] Kopiowanie/pobieranie dokumentacji B+R
- [x] Fix SQL bug (COUNT → SUM)
- [x] Fix git-timesheet path mapping
- [x] Fix expenses API limit
- [x] Filtrowanie wydatków po roku/miesiącu
- [x] Przycisk szczegółów miesiąca z raportów
- [x] Testy git-timesheet (8 testów)
- [x] Select pracownika na stronie git-timesheet
- [x] Checkbox "zaznacz wszystkie" dla projektów
- [x] Fix usuwania wydatków (db.commit)
- [x] Fix dashboard null check (clarification-badge)
- [x] Zwiększone logowanie console.log
- [x] Fix git-timesheet work_date (string→date)
- [x] Kopiowanie/pobieranie logów do pliku
- [x] Fix TypeError upload page (loadRecentDocuments)
- [x] Moduł walidacji faktur (InvoiceValidator)
- [x] Moduł konwersji walut NBP (CurrencyConverter)
- [x] Endpoint /expenses/validate-all
- [x] 37 testów walidatorów
- [x] Generator uzasadnień wydatków (justification_generator.py)
- [x] Endpoint /expenses/{id}/generate-justification
- [x] Endpoint /expenses/{id}/vendor
- [x] Model rozszerzonego projektu (project_extended.py)
- [x] Generator sekcji niepewności (uncertainty_generator.py)
- [x] Endpoint /projects/{id}/generate-uncertainty
- [x] 166 testów jednostkowych passed
- [x] Optymalizacja startu br-ocr (start_period: 90s)
- [x] Fix git-timesheet (worker_id opcjonalny)
- [x] Model DailyTimeEntry z walidacją B+R
- [x] Endpoint /timesheet/entries/validated
- [x] Pipeline walidacji wydatków (expense_pipeline.py)
- [x] Automatyczna kategoryzacja B+R (expense_categorizer.py)
- [x] Audit trail service (audit_trail.py)
- [x] Endpoint /expenses/validate-pipeline
- [x] Endpoint /expenses/categorize
- [x] KSeF client (ksef_client.py)
- [x] JPK_V7M exporter (jpk_export.py)
- [x] Endpoint /integrations/ksef/import
- [x] Endpoint /integrations/jpk/generate
- [x] Endpoint /integrations/jpk/download
- [x] Dokumentacja API (OpenAPI tags, opisy)
- [x] ExpenseService (expense_service.py) - wydzielenie logiki biznesowej
- [x] Excel exporter (excel_exporter.py)
- [x] Endpoint /reports/export/expenses
- [x] Endpoint /reports/export/monthly
- [x] CI/CD pipeline (.github/workflows/ci.yml)

### 2026-01-12
- [x] URL state management
- [x] Globalny overlay logów
- [x] Cache-busting
- [x] Lazy loading listeners

### 2026-01-11
- [x] CQRS architecture
- [x] Event store
- [x] Read models schema
- [x] Timesheet module

---

Ostatnia aktualizacja: 2026-01-14
