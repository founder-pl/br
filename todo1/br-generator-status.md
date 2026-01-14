# BR Documentation Generator - Status Projektu

## Przegląd

**Projekt**: BR Documentation Generator  
**Organizacja**: Founder.pl / Softreck  
**Repozytorium**: `founder-pl/br`  
**Wersja**: 1.0 (w rozwoju)  
**Ostatnia aktualizacja**: 14 stycznia 2026

---

## Cel Projektu

BR Documentation Generator to zaawansowany system automatyzacji tworzenia dokumentacji dla polskiej ulgi badawczo-rozwojowej (B+R) oraz preferencji IP Box. Projekt adresuje kluczowy problem polskich przedsiębiorstw innowacyjnych - czasochłonne i skomplikowane przygotowywanie dokumentacji podatkowej wymaganej do skorzystania z ulg.

### Główne Funkcjonalności

- **Automatyczne generowanie dokumentów B+R** - karty projektowe, ewidencje czasu pracy, rejestry wydatków
- **Obliczanie wskaźnika Nexus** - kluczowy element IP Box
- **Walidacja zgodności prawnej** - automatyczne sprawdzanie dokumentów pod kątem wymogów ustawowych
- **Integracja z systemami księgowymi** - Fakturownia, iFirma, wFirma, InFakt
- **Eksport do wielu formatów** - Markdown, PDF, DOCX

---

## Statystyki Kodu

| Metryka | Wartość |
|---------|---------|
| Liczba plików | 114 |
| Linie kodu | 37 259 |
| Języki | Python (99%), JavaScript (1%) |
| Testy | ~2 500 linii |
| Pokrycie testami | ~65% |

### Struktura Modułów

```
br/
├── src/                          # Główna aplikacja
│   ├── api/                      # FastAPI endpoints
│   │   ├── routers/              # Kontrolery REST
│   │   ├── services/             # Logika biznesowa
│   │   ├── validators/           # Walidatory
│   │   └── integrations/         # KSeF, JPK
│   ├── doc_generator/            # Silnik generowania
│   ├── ocr/                      # Rozpoznawanie faktur
│   └── integrations/             # Integracje zewnętrzne
├── brgenerator/                  # Moduł CLI/Web
│   └── src/br_doc_generator/
│       ├── generators/           # Generatory dokumentów
│       ├── validators/           # Pipeline walidacji
│       └── llm_client.py         # Klient OpenRouter
├── tests/                        # Testy
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── web/                          # Frontend
    └── static/js/
```

---

## Architektura Techniczna

### Stack Technologiczny

| Warstwa | Technologia |
|---------|-------------|
| Backend | Python 3.11+, FastAPI |
| Baza danych | PostgreSQL + SQLAlchemy |
| LLM | OpenRouter (nvidia/nemotron) |
| OCR | Tesseract / EasyOCR |
| PDF | WeasyPrint |
| Frontend | Vanilla JS + Markdown renderer |
| Kolejki | Celery + Redis |

### Wzorce Projektowe

- **CQRS** - Command Query Responsibility Segregation dla operacji na danych
- **Event Sourcing** - Historia zmian dokumentów
- **Domain-Driven Design** - Modelowanie domeny B+R
- **Singleton** - Registry szablonów i źródeł danych

---

## Kluczowe Moduły

### 1. Document Generator Engine

Centralny silnik odpowiedzialny za generowanie dokumentów na podstawie szablonów Jinja2 i danych z bazy.

**Plik**: `src/doc_generator/engine.py` (476 linii)

**Funkcje**:
- Renderowanie szablonów z danymi
- Obsługa filtrów formatowania (daty, waluty)
- Zarządzanie kontekstem generowania

### 2. Template Registry

Rejestr wszystkich dostępnych szablonów dokumentów B+R.

**Plik**: `src/doc_generator/templates.py` (681 linii)

**Dostępne szablony**:
- `project_card` - Karta Projektowa B+R
- `timesheet_monthly` - Miesięczny Rejestr Czasu Pracy
- `expense_registry` - Ewidencja Wydatków B+R
- `nexus_calculation` - Obliczenie Wskaźnika Nexus
- `br_annual_summary` - Roczne Podsumowanie B+R
- `ipbox_procedure` - Procedura Wewnętrzna IP Box
- `tax_interpretation_request` - Wniosek o Interpretację

### 3. Validation Pipeline

Wielopoziomowy system walidacji generowanych dokumentów.

**Katalog**: `brgenerator/src/br_doc_generator/validators/`

**Poziomy walidacji**:
1. **Structure** - Struktura markdown
2. **Content** - Kompletność danych
3. **Legal** - Zgodność z ustawami
4. **Financial** - Poprawność obliczeń
5. **LLM Review** - Ocena jakościowa AI

### 4. Data Sources DSL

Warstwa abstrakcji dla pobierania danych z różnych źródeł.

**Plik**: `src/doc_generator/data_sources.py` (409 linii)

**Typy źródeł**:
- SQL (PostgreSQL)
- REST API (NBP, zewnętrzne)
- cURL (legacy integrations)

---

## Status Funkcjonalności

### Zaimplementowane ✅

| Funkcja | Status | Uwagi |
|---------|--------|-------|
| Generowanie Karty Projektowej | ✅ | Pełna funkcjonalność |
| Ewidencja Czasu Pracy | ✅ | Wymaga poprawek formatowania |
| Rejestr Wydatków | ✅ | Działa poprawnie |
| Obliczenie Nexus | ✅ | Wymaga walidacji edge cases |
| Walidacja Struktury | ✅ | 5 walidatorów |
| Eksport PDF | ✅ | WeasyPrint |
| OCR Faktur | ✅ | Tesseract integration |
| Integracja LLM | ✅ | OpenRouter |

### W Trakcie Implementacji 🔄

| Funkcja | Status | ETA |
|---------|--------|-----|
| Walidacja NIP | 🔄 | Tydzień 3 |
| Automatyczna kategoryzacja | 🔄 | Tydzień 4 |
| Dashboard raportowy | 🔄 | Tydzień 5 |
| Integracja KSeF | 🔄 | Q1 2026 |

### Planowane 📋

| Funkcja | Priorytet | Planowany termin |
|---------|-----------|------------------|
| Wsparcie zmian 2026 | Wysoki | Q1 2026 |
| Export JPK | Średni | Q2 2026 |
| Multi-tenant | Niski | Q3 2026 |
| Mobile app | Niski | 2027 |

---

## Znane Problemy

### Krytyczne 🔴

1. **Nexus edge cases** - Niepoprawne obliczenia gdy wszystkie składniki = 0
2. **Brak walidacji NIP** - Możliwość wprowadzenia nieprawidłowego NIP

### Ważne 🟠

1. **Formatowanie kwot** - Niespójne separatory tysięcy
2. **Obsługa NULL** - Brak graceful degradation dla brakujących danych
3. **Rate limiting LLM** - Brak obsługi limitów API OpenRouter

### Drobne 🟡

1. **UI/UX** - Brak progress indicators podczas generowania
2. **Dokumentacja** - Niekompletna dokumentacja API
3. **Logi** - Nadmiarowe logowanie w produkcji

---

## Roadmapa

### Q1 2026

```
Styczeń:
  - [x] Refaktoring walidatorów
  - [ ] Walidacja NIP z sumą kontrolną
  - [ ] Poprawki Nexus

Luty:
  - [ ] Pipeline walidacji 5-poziomowej
  - [ ] Integracja LLM review
  - [ ] Testy E2E

Marzec:
  - [ ] Integracja KSeF
  - [ ] Dashboard MVP
  - [ ] Release 1.0
```

### Q2 2026

```
Kwiecień-Czerwiec:
  - [ ] Wsparcie zmian prawnych 2026
  - [ ] Export JPK
  - [ ] Automatyczna kategoryzacja AI
  - [ ] Mobile-friendly web UI
```

---

## Jak Używać

### Instalacja

```bash
git clone https://github.com/founder-pl/br.git
cd br
pip install -e .
```

### Konfiguracja

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/br
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
```

### Generowanie Dokumentu

```bash
# CLI
br generate --template project_card --project-id UUID --year 2025

# API
curl -X POST http://localhost:8000/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"template_id": "project_card", "project_id": "UUID", "year": 2025}'
```

---

## Kontrybutorzy

- **Softreck** - Architektura, rozwój główny
- **Founder.pl** - Wymagania biznesowe, testy użytkowników

---

## Licencja

Projekt jest własnością Softreck. Kod źródłowy jest dostępny dla klientów Founder.pl.

---

## Linki

- [Dokumentacja B+R (MF)](https://www.podatki.gov.pl/cit/ulgi-cit/ulga-na-dzialalnosc-b-r/)
- [Objaśnienia IP Box (KIS)](https://www.kis.gov.pl/interpretacje-indywidualne)
- [OpenRouter API](https://openrouter.ai/docs)

---

*Ostatnia aktualizacja: 14 stycznia 2026*
