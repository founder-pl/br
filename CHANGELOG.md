# Changelog

Wszystkie istotne zmiany w projekcie System B+R.

## [2026-01-13] - Modularny Dashboard i Naprawy API

### Dodane
- **Modularny Dashboard** z konfiguracją 4x4 grid
  - 16 różnych modułów (statystyki, listy, wykresy, akcje)
  - Konfiguracja zapisywana w localStorage
  - Możliwość dodawania/usuwania modułów przez selectlist
  - Różne rozmiary modułów: 1x1, 2x1, 1x2, 2x2
- **Edycja danych OCR** w modalu dokumentu
  - Edytowalne pola: nr faktury, data, kwoty, sprzedawca
  - Przycisk zapisywania zmian (PATCH /documents/{id})
- **Tworzenie wydatków z dokumentów** - przycisk "Utwórz wydatek"
- **Kopiowanie/pobieranie dokumentacji B+R** (markdown)
- **Kopiowanie logów** na stronie /logs

### Naprawione
- **SQL bug w dashboard**: COUNT(*) → SUM(gross_amount) dla total_expenses
- **Git-timesheet path mapping**: /home/tom/github → /repos w kontenerze
- **Expenses API limit**: 100 → 1000 dla raportów rocznych
- **Test regex**: Art. → [Aa]rt. dla legal_compliance
- **TypeError w uploadFile**: lazy initialization event listeners
- **UnboundLocalError w logs.py**: inicjalizacja process = None

### Zmienione
- Refaktoryzacja loadDashboard() na system modułowy
- Ulepszony UI dla modalu dokumentu z sekcją edycji

## [2026-01-12] - URL State Management i Logi

### Dodane
- **URL state management** (?page=, ?doc=, ?logs=)
- **Globalny overlay logów** z SSE streaming
- **Cache-busting** dla plików statycznych
- **Lazy loading** event listenerów

### Naprawione
- Menu navigation nie aktualizowało URL
- Błędy DOM przy ładowaniu strony

## [2026-01-11] - CQRS Event Sourcing

### Dodane
- Architektura **CQRS z Event Sourcing**
- Read models w osobnym schemacie PostgreSQL
- Event store dla śledzenia zmian
- Timesheet module z pracownikami i wpisami

### Zmienione
- Migracja z ORM na raw SQL dla read models
- Separacja write/read operations

## [2026-01-10] - Podstawowa funkcjonalność

### Dodane
- Upload dokumentów z OCR (Tesseract/PaddleOCR/EasyOCR)
- Klasyfikacja wydatków B+R przez LLM
- Generowanie raportów miesięcznych
- System wyjaśnień (clarifications)
- Integracje z systemami księgowymi (iFirma, wFirma)
- Integracje cloud storage (Nextcloud, S3)
- Panel konfiguracji AI

---

Format bazowany na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/)
