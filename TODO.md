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

### CQRS/Event Sourcing
- [ ] **Event replay mechanism**
  - Odtwarzanie stanu z eventów
  - Snapshots dla wydajności
- [ ] **Saga pattern** dla złożonych operacji
  - Transakcje rozproszone
  - Kompensacje przy błędach
- [ ] **Projekcje asynchroniczne**
  - Background workers
  - Event handlers

### Integracje
- [ ] **KSeF integration**
  - Pobieranie faktur z KSeF
  - Automatyczne przetwarzanie
- [ ] **JPK_V7M export**
  - Generowanie plików JPK
  - Walidacja zgodności

### Dokumentacja
- [ ] **Dokumentacja API** (OpenAPI/Swagger)
- [ ] **Instrukcja użytkownika**
- [ ] **Diagramy architektury** (C4, sequence)

## Priorytet: Niski 🟢

### UI/UX
- [ ] **Dark mode toggle**
- [ ] **Drag & drop** dla modułów dashboard
- [ ] **Eksport do Excel** (wydatki, raporty)
- [ ] **Powiadomienia push** (WebSocket)

### Performance
- [ ] **Caching** (Redis dla read models)
- [ ] **Pagination** w listach
- [ ] **Lazy loading** dla dużych zestawów

### DevOps
- [ ] **CI/CD pipeline** (GitHub Actions)
- [ ] **Staging environment**
- [ ] **Monitoring** (Prometheus/Grafana)
- [ ] **Log aggregation** (ELK stack)

## Zakończone ✅

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

Ostatnia aktualizacja: 2026-01-13
