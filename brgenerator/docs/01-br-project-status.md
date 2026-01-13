# System B+R - Status Projektu Automatyzacji Dokumentacji Ulgi Badawczo-Rozwojowej

**Data publikacji:** 13 stycznia 2026  
**Autor:** Softreck  
**Kategoria:** Projekty, B+R, Automatyzacja

---

## Wprowadzenie

Projekt B+R to kompleksowy system automatyzacji dokumentacji dla polskiej ulgi badawczo-rozwojowej. System łączy zaawansowane technologie OCR, integracje z polskimi systemami księgowymi oraz klasyfikację kosztów opartą na LLM, aby maksymalnie uprościć proces przygotowania dokumentacji do ulgi B+R.

## Status Techniczny

### Architektura Systemu

Projekt składa się z **54 modułów** napisanych w Pythonie (53) i JavaScript (1), zawierających łącznie **13 637 linii kodu**. System wykorzystuje architekturę mikroserwisową z następującymi komponentami:

| Komponent | Opis | Technologia |
|-----------|------|-------------|
| API Backend | FastAPI REST API | Python 3.11+ |
| OCR Engine | Wielosilnikowe rozpoznawanie dokumentów | PaddleOCR, Tesseract, EasyOCR |
| Integrations | Systemy księgowe i chmura | iFirma, Fakturownia, Nextcloud |
| Frontend | Single Page Application | JavaScript vanilla |
| Infrastructure | Kolejkowanie zadań | Celery + Redis |

### Moduły Kluczowe

#### 1. System OCR (`src/ocr/`)

System rozpoznawania dokumentów obsługuje trzy silniki OCR z automatycznym fallback:

```python
# Wspierane silniki OCR
OCREngine.PADDLEOCR   # Szybki, dobry dla dokumentów biznesowych
OCREngine.TESSERACT   # Uniwersalny, otwarty
OCREngine.EASYOCR     # Dobry dla różnych języków
```

**Funkcjonalności:**
- Automatyczne wykrywanie typu dokumentu (faktura, rachunek, umowa)
- Walidacja NIP i REGON z algorytmami kontrolnymi
- Ekstrakcja strukturalnych danych (kwoty, daty, numery faktur)
- Preprocessing obrazu (deskew, denoise, binaryzacja)

#### 2. Integracje Księgowe (`src/integrations/accounting/`)

System obsługuje **4 główne polskie systemy księgowe**:

| System | Status | Funkcjonalności |
|--------|--------|-----------------|
| iFirma | ✅ Aktywny | Faktury sprzedaży i zakupu, PDF |
| Fakturownia | ✅ Aktywny | Pełna synchronizacja |
| wFirma | ✅ Aktywny | Faktury VAT |
| InFakt | ✅ Aktywny | Podstawowa integracja |

#### 3. Integracje Chmurowe (`src/integrations/cloud/`)

**6 wspieranych platform przechowywania:**
- Nextcloud (WebDAV)
- Google Drive (OAuth2)
- Dropbox
- OneDrive
- AWS S3
- MinIO

#### 4. System Klasyfikacji B+R (`src/api/routers/expenses.py`)

Automatyczna klasyfikacja wydatków do kategorii B+R:

```python
BR_CATEGORIES = [
    "personnel_employment",      # Wynagrodzenia pracowników
    "personnel_civil",           # Umowy cywilnoprawne  
    "materials",                 # Materiały i surowce
    "equipment",                 # Sprzęt specjalistyczny
    "depreciation",              # Amortyzacja
    "expertise",                 # Ekspertyzy i opinie
    "external_research",         # Usługi jednostek naukowych
    "ip_costs"                   # Koszty ochrony własności
]
```

### Pokrycie Testami

System posiada **kompleksowy zestaw testów** na trzech poziomach:

| Typ Testów | Liczba Plików | Zakres |
|------------|---------------|--------|
| Unit | 3 | Extractory, walidatory, integracje |
| Integration | 4 | API endpoints, SQL queries |
| E2E | 3 | Pełne scenariusze biznesowe |

**Przykładowe scenariusze E2E:**
- Pełny workflow przetwarzania dokumentu
- Generowanie raportów miesięcznych
- Workflow pytań wyjaśniających
- Kompletny miesięczny workflow B+R z integracjami

## Zgodność z Wymaganiami Ulgi B+R

### Kryteria Kwalifikacji

System implementuje walidację zgodną z oficjalnymi wytycznymi:

1. **Systematyczność** - Projekty realizowane zgodnie z harmonogramem
2. **Twórczość** - Projekty kreatywne z elementem ryzyka
3. **Nowatorstwo** - Innowacja minimum w skali przedsiębiorstwa

### Kategorie Kosztów Kwalifikowanych

System automatycznie kategoryzuje koszty według ustawy o CIT:

| Kategoria | Stawka Odliczenia | Automatyczna Detekcja |
|-----------|-------------------|----------------------|
| Koszty osobowe | 200% | ✅ Po NIP i opisie |
| Materiały i surowce | 100% | ✅ Po kategorii VAT |
| Sprzęt specjalistyczny | 100% | ✅ Po opisie faktury |
| Ekspertyzy naukowe | 100% | ✅ Po kontrahencie |
| Amortyzacja | 100% | ✅ Po środku trwałym |

## Planowany Rozwój

### Nowy Komponent: Generator Dokumentacji LLM

W następnej fazie projektu planowane jest dodanie modułu automatycznego generowania dokumentacji B+R z wykorzystaniem LLM:

**Funkcjonalności:**
- Wielopoziomowa walidacja generowanej dokumentacji
- Integracja z LiteLLM i OpenRouter
- Automatyczne wypełnianie formularzy na podstawie danych projektu
- Renderowanie Markdown do PDF
- Walidacja zgodności z wymaganiami US

### Roadmap

| Faza | Zakres | Status |
|------|--------|--------|
| Faza 1 | Podstawowy system OCR i API | ✅ Ukończona |
| Faza 2 | Integracje księgowe | ✅ Ukończona |
| Faza 3 | Integracje chmurowe | ✅ Ukończona |
| Faza 4 | Klasyfikacja LLM | 🔄 W trakcie |
| Faza 5 | Generator dokumentacji | 📋 Planowana |

## Podsumowanie

Projekt B+R stanowi kompleksowe rozwiązanie do automatyzacji procesu dokumentacji ulgi badawczo-rozwojowej. Dzięki integracji z polskimi systemami księgowymi, zaawansowanemu OCR i planowanej klasyfikacji LLM, system znacząco redukuje nakład pracy związany z przygotowaniem dokumentacji do ulgi B+R.

---

**Linki:**
- [Ustawa o CIT - Ulga B+R](https://www.podatki.gov.pl/ulgi/ulga-badawczo-rozwojowa-pit/)
- [Ayming - Przygotowanie dokumentacji B+R](https://www.ayming.pl/najnowsze-publikacje/aktualnosci/przygotowanie-dokumentacji-do-ulgi-br-poradnik/)
- [Dokumentacja Ulgi B+R](https://akademialtca.pl/blog/dokumentacja-ulgi-br)

**Tagi:** #BR #UlgaPodatkowa #Automatyzacja #OCR #Python #FastAPI
