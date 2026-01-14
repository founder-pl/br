# BR Documentation Generator - Lista TODO dla LLM

## Status Projektu: `br` (Founder.pl)

**Model LLM**: `nvidia/nemotron-3-nano-30b-a3b:free` (OpenRouter)  
**Struktura**: 114 plików, 37 259 linii kodu  
**Języki**: Python (112 plików), JavaScript (2 pliki)

---

## 1. KRYTYCZNE POPRAWKI GENEROWANIA DOKUMENTÓW

### 1.1 Walidacja Danych Wejściowych

```yaml
TODO:
  - [ ] Dodać walidację NIP (format 10-cyfrowy + suma kontrolna)
  - [ ] Sprawdzać kompletność danych projektu przed generowaniem
  - [ ] Walidować zakres dat (start_date < end_date)
  - [ ] Weryfikować rok fiskalny (nie może być z przyszłości)
  - [ ] Sprawdzać istnienie wymaganych pól w ProjectInput

Lokalizacje do modyfikacji:
  - brgenerator/src/br_doc_generator/models.py (klasa ProjectInput)
  - brgenerator/src/br_doc_generator/validators/base.py (ValidationContext)
```

### 1.2 Zgodność z Prawem Podatkowym

```yaml
TODO:
  - [ ] Aktualizować limity odliczeń B+R na podstawie aktualnych przepisów
  - [ ] Implementować sprawdzanie zmian prawnych od 2026 (danina solidarnościowa)
  - [ ] Dodać walidację wymogu zatrudnienia 3 osób (od 2026)
  - [ ] Weryfikować kategorie kosztów kwalifikowanych wg ustawy

Wymagane referencje prawne:
  - Art. 18d ustawy o CIT (koszty kwalifikowane)
  - Art. 26e ustawy o PIT (ulga B+R)
  - Art. 24d ust. 2 pkt 8 ustawy o CIT (IP Box)
  - Rozporządzenie MF ws. dokumentacji B+R
```

### 1.3 Obliczenia Finansowe

```yaml
TODO:
  - [ ] Naprawić obliczanie wskaźnika Nexus dla przypadków brzegowych
  - [ ] Dodać walidację: Nexus <= 1.0
  - [ ] Implementować przeliczanie walut (kurs NBP z dnia faktury)
  - [ ] Sprawdzać poprawność sum częściowych vs suma całkowita
  - [ ] Weryfikować VAT (23%, 8%, 5%, 0%, ZW, NP)

Pliki do modyfikacji:
  - src/doc_generator/data_sources.py (nexus_calculation query)
  - brgenerator/src/br_doc_generator/validators/financial.py
```

---

## 2. ULEPSZENIA SZABLONÓW DOKUMENTÓW

### 2.1 Karta Projektowa B+R (`project_card`)

```yaml
TODO:
  - [ ] Dodać pole "Podstawa prawna działalności B+R"
  - [ ] Rozszerzyć sekcję hipotezy badawczej o metodologię
  - [ ] Dodać checklistę kryteriów B+R (twórczość, systematyczność, nowość)
  - [ ] Implementować automatyczne generowanie kodu projektu BR-RRRR-NNNN
  - [ ] Dodać sekcję "Związek z kwalifikowanym IP"

Wzorzec dokumentu:
  Nagłówek → Identyfikacja → Opis B+R → Zespół → Koszty → Zatwierdzenie
```

### 2.2 Ewidencja Czasu Pracy (`timesheet_monthly`)

```yaml
TODO:
  - [ ] Dodać podział na godziny B+R vs godziny ogółem
  - [ ] Implementować walidację limitu godzin (max 24h/dzień)
  - [ ] Dodać kolumnę "Procent zaangażowania w B+R"
  - [ ] Generować zestawienie miesięczne z automatycznym podsumowaniem
  - [ ] Dodać miejsce na podpis pracownika i kierownika

Dane wymagane:
  - worker_name, work_date, hours, task_description, project_id
```

### 2.3 Obliczenie Nexus (`nexus_calculation`)

```yaml
TODO:
  - [ ] Dodać szczegółowe wyjaśnienie każdego składnika (a, b, c, d)
  - [ ] Implementować wizualizację wzoru
  - [ ] Dodać przykład liczbowy z danymi projektu
  - [ ] Sprawdzać zgodność z interpretacjami KIS
  - [ ] Ostrzegać gdy Nexus < 0.5 (ryzyko kontroli)

Wzór: Nexus = ((a + b) × 1.3) / (a + b + c + d)
  a = koszty B+R bezpośrednie
  b = koszty B+R od niepowiązanych
  c = koszty B+R od powiązanych
  d = koszty zakupu gotowego IP
```

### 2.4 Wniosek o Interpretację (`tax_interpretation_request`)

```yaml
TODO:
  - [ ] Aktualizować formularz wg wzoru ORD-IN
  - [ ] Dodać automatyczne wypełnianie danych podatnika
  - [ ] Generować uzasadnienie stanowiska na podstawie danych projektu
  - [ ] Dodać checklistę wymaganych załączników
  - [ ] Implementować walidację pytań (muszą dotyczyć zdarzenia przyszłego)
```

---

## 3. WALIDACJA PO WYGENEROWANIU

### 3.1 Pipeline Walidacji (5 poziomów)

```yaml
POZIOMY_WALIDACJI:
  1_structure:
    - [ ] Sprawdzić obecność wymaganych sekcji
    - [ ] Weryfikować format nagłówków Markdown
    - [ ] Walidować strukturę tabel
    
  2_content:
    - [ ] Sprawdzić kompletność danych (brak "N/A", "Brak")
    - [ ] Weryfikować spójność nazw projektu/firmy
    - [ ] Sprawdzać poprawność dat
    
  3_legal:
    - [ ] Walidować NIP (suma kontrolna)
    - [ ] Sprawdzać obecność wymaganych oświadczeń
    - [ ] Weryfikować zgodność z art. ustawy
    
  4_financial:
    - [ ] Sprawdzać sumy częściowe vs całkowite
    - [ ] Walidować format kwot (PLN, separatory)
    - [ ] Weryfikować obliczenia Nexus
    
  5_llm_review:
    - [ ] Sprawdzać logiczność opisu B+R
    - [ ] Weryfikować innowacyjność projektu
    - [ ] Oceniać kompletność dokumentacji
```

### 3.2 Implementacja Walidatorów

```python
# Struktura walidatora (do zaimplementowania)
class DocumentValidator:
    async def validate(self, content: str, context: ValidationContext) -> ValidationResult:
        issues = []
        
        # 1. Sprawdź strukturę
        issues += self._check_structure(content)
        
        # 2. Sprawdź dane prawne
        issues += self._check_legal_compliance(content, context)
        
        # 3. Sprawdź finanse
        issues += self._check_financial_accuracy(content, context)
        
        # 4. Wywołaj LLM do oceny jakości
        llm_issues = await self._llm_quality_check(content)
        issues += llm_issues
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == 'ERROR']) == 0,
            issues=issues,
            score=self._calculate_score(issues)
        )
```

---

## 4. INTEGRACJA Z SYSTEMEM

### 4.1 Źródła Danych (data_sources.py)

```yaml
TODO:
  - [ ] Dodać obsługę NULL/brakujących wartości w SQL
  - [ ] Implementować cache dla kursów NBP
  - [ ] Dodać retry logic dla zewnętrznych API
  - [ ] Walidować odpowiedzi przed przekazaniem do szablonów

Dostępne źródła:
  - project_info: informacje o projekcie
  - expenses_summary: lista wydatków
  - expenses_by_category: wydatki wg kategorii
  - timesheet_summary: godziny pracy
  - revenues: przychody z IP
  - workers: pracownicy projektu
  - nexus_calculation: obliczenie Nexus
  - nbp_exchange_rate: kursy walut (REST API)
```

### 4.2 Konfiguracja LLM (LiteLLM)

```yaml
# Projekt używa LiteLLM jako proxy z wieloma modelami
# Konfiguracja: litellm_config.yaml

DOSTĘPNE_MODELE:
  production:
    - gpt-4o: OpenAI GPT-4o (klasyfikacja dokumentów)
    - gpt-4o-mini: OpenAI GPT-4o-mini (szybka klasyfikacja)
    - claude-sonnet: Anthropic Claude Sonnet (reasoning)
  
  openrouter:
    - openrouter-claude: Claude 3.5 Sonnet via OpenRouter
    - openrouter-gpt4: GPT-4 Turbo via OpenRouter
  
  local_ollama:
    - llama3.2: Llama 3.2 (dobry dla polskiego tekstu)
    - mistral: Mistral (szybki lokalny model)
    - qwen2.5: Qwen 2.5 (dobra obsługa wielojęzyczna)
  
  specialized:
    - br-classifier: Klasyfikator dokumentów B+R (GPT-4o-mini)
    - br-classifier-fallback: Fallback lokalny (Llama 3.2)
    - br-report-generator: Generator raportów (Claude Sonnet)

FALLBACK_CHAIN:
  br-classifier: [br-classifier-fallback, openrouter-claude]
  gpt-4o: [claude-sonnet, openrouter-claude, llama3.2]
  claude-sonnet: [gpt-4o, openrouter-gpt4, llama3.2]

TODO:
  - [x] Fallback models - ZAIMPLEMENTOWANE w litellm_config.yaml
  - [x] Rate limiting - ZAIMPLEMENTOWANE (max_budget: 100 USD/month)
  - [ ] Włączyć langfuse logging (wymaga instalacji)
  - [ ] Dodać metryki per model type
  - [ ] Konfigurować temperature per document type

# .env - klucze API (opcjonalne - można używać lokalnych modeli)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
OLLAMA_API_BASE=http://host.docker.internal:11434
LITELLM_MASTER_KEY=sk-br-llm-2025
```

### 4.3 Wybór Modelu per Zadanie

```yaml
REKOMENDACJE:
  klasyfikacja_dokumentów:
    primary: br-classifier (gpt-4o-mini)
    fallback: llama3.2
    temperature: 0.0
    max_tokens: 2048
    
  generowanie_raportów:
    primary: br-report-generator (claude-sonnet)
    fallback: gpt-4o
    temperature: 0.3
    max_tokens: 8192
    
  walidacja_prawna:
    primary: claude-sonnet
    fallback: gpt-4o
    temperature: 0.1
    max_tokens: 4096
    
  szybkie_zadania:
    primary: gpt-4o-mini
    fallback: mistral
    temperature: 0.1
    max_tokens: 2048
```

---

## 5. NOWE FUNKCJONALNOŚCI

### 5.1 Automatyczna Kategoryzacja Wydatków

```yaml
TODO:
  - [ ] Implementować AI-based kategoryzację faktur
  - [ ] Mapować opisy na kategorie B+R:
      - personnel_employment: wynagrodzenia UoP
      - personnel_civil: wynagrodzenia B2B/zlecenia
      - materials: materiały i surowce
      - equipment: sprzęt i wyposażenie
      - external_services: usługi zewnętrzne
      - ip_purchase: zakup gotowego IP
  - [ ] Dodać confidence score dla kategoryzacji
  - [ ] Generować uzasadnienie kwalifikacji B+R
```

### 5.2 Generowanie Uzasadnień

```yaml
TODO:
  - [ ] Automatycznie generować uzasadnienie dla każdego wydatku
  - [ ] Łączyć z adnotacjami dokumentów
  - [ ] Tworzyć spójną narrację B+R
  - [ ] Sprawdzać zgodność uzasadnienia z opisem projektu

Struktura uzasadnienia:
  1. Identyfikacja wydatku
  2. Związek z działalnością B+R
  3. Podstawa prawna kwalifikacji
  4. Dowody (faktury, umowy)
```

### 5.3 Eksport do Formatów

```yaml
TODO:
  - [ ] Markdown → PDF (WeasyPrint)
  - [ ] Markdown → DOCX (python-docx)
  - [ ] Markdown → HTML (dla web GUI)
  - [ ] JSON → JPK (dla kontroli skarbowej)

Pliki:
  - brgenerator/src/br_doc_generator/generators/pdf.py
  - src/api/integrations/jpk_export.py
```

---

## 6. TESTY I JAKOŚĆ

### 6.1 Testy Jednostkowe

```yaml
TODO:
  - [ ] Dodać testy dla każdego walidatora
  - [ ] Testować edge cases obliczania Nexus
  - [ ] Mockować wywołania LLM w testach
  - [ ] Testować generowanie wszystkich typów dokumentów

Lokalizacje testów:
  - tests/unit/test_validators.py
  - tests/unit/test_extractors.py
  - brgenerator/tests/test_validators.py
```

### 6.2 Testy E2E

```yaml
TODO:
  - [ ] Testować pełny pipeline: input → generation → validation → output
  - [ ] Porównywać z wzorcowymi dokumentami
  - [ ] Testować integrację z bazą danych
  - [ ] Sprawdzać wydajność generowania

Lokalizacje:
  - tests/e2e/test_scenarios.py
  - tests/e2e/test_integrations_e2e.py
  - brgenerator/tests/test_e2e.py
```

---

## 7. CHECKLIST ZGODNOŚCI PRAWNEJ

### 7.1 Wymagania Ustawowe B+R

```yaml
CHECKLIST_BR:
  - [ ] Działalność twórcza (art. 4a pkt 26 CIT)
  - [ ] Systematyczność prowadzenia prac
  - [ ] Zwiększanie zasobów wiedzy
  - [ ] Wykorzystanie wiedzy do nowych zastosowań
  - [ ] Dokumentacja podejmowanych czynności
  - [ ] Ewidencja kosztów kwalifikowanych
```

### 7.2 Wymagania IP Box

```yaml
CHECKLIST_IPBOX:
  - [ ] Kwalifikowane prawo własności intelektualnej
  - [ ] Wytworzenie/ulepszenie IP w ramach B+R
  - [ ] Ewidencja odrębna dla każdego IP
  - [ ] Obliczenie wskaźnika Nexus
  - [ ] Dochód bezpośrednio związany z IP
  - [ ] (Od 2026) Zatrudnienie min. 3 osób
```

### 7.3 Dokumentacja Archiwalna

```yaml
ARCHIWIZACJA:
  okres: 5 lat od końca roku podatkowego
  dokumenty:
    - [ ] Karty projektowe B+R
    - [ ] Ewidencje czasu pracy
    - [ ] Faktury i umowy
    - [ ] Obliczenia Nexus
    - [ ] Zeznania podatkowe
    - [ ] Interpretacje indywidualne
```

---

## 8. PRIORYTETY IMPLEMENTACJI

### Faza 1: Krytyczne (tydzień 1-2)
1. Walidacja NIP z sumą kontrolną
2. Poprawki obliczania Nexus
3. Podstawowa walidacja struktury dokumentów

### Faza 2: Ważne (tydzień 3-4)
1. Pipeline walidacji 5-poziomowej
2. Integracja z LLM do review
3. Generowanie uzasadnień

### Faza 3: Usprawnienia (tydzień 5-6)
1. Eksport do PDF/DOCX
2. Automatyczna kategoryzacja
3. Testy E2E

### Faza 4: Przyszłość (Q2 2026)
1. Wsparcie zmian prawnych 2026
2. Integracja JPK
3. Dashboard raportowy

---

## Podsumowanie

System BR Documentation Generator wymaga następujących kluczowych usprawnień:

1. **Walidacja prawna** - zgodność z ustawami o CIT/PIT
2. **Obliczenia finansowe** - poprawność Nexus i sum
3. **Struktura dokumentów** - kompletność sekcji
4. **Integracja LLM** - automatyczny review jakości
5. **Testy** - pokrycie edge cases

Model `nvidia/nemotron-3-nano-30b-a3b:free` powinien być używany z niską temperaturą (0.3) dla dokumentów prawnych i finansowych.
