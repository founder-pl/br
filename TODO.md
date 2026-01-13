# TODO - System B+R

## Priorytet: Wysoki 🔴

### Frontend
- [ ] **Filtrowanie wydatków po miesiącach** w /expenses
  - Dodać selecty rok/miesiąc w nagłówku
  - Parametry URL: ?year=2026&month=1
  - Widok kosztów vs przychodów (tabs)
- [ ] **Szczegóły miesiąca z raportów**
  - Przycisk "Zobacz szczegóły" przy każdym miesiącu
  - Link do /expenses?year=X&month=Y
  - Przypisane rachunki kosztowe i przychodowe
- [ ] **Naprawić generowanie miesięcy** w /reports
  - Weryfikacja API endpoint
  - Obsługa błędów

### Backend
- [ ] **Testy dla git-timesheet**
  - Test scan endpoint
  - Test commits endpoint  
  - Test generate-timesheet endpoint
- [ ] **Walidacja ścieżek** w git-timesheet
  - Sprawdzanie uprawnień
  - Obsługa błędów dostępu

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
