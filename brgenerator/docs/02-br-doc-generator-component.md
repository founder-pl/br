# brgenerator - Nowy Komponent Automatycznego Generowania Dokumentacji B+R

**Data publikacji:** 13 stycznia 2026  
**Autor:** Softreck  
**Kategoria:** Projekty, B+R, LLM, AI

---

## Wprowadzenie

**brgenerator** to nowa biblioteka Python stanowiąca rozszerzenie systemu B+R o możliwość automatycznego generowania kompletnej dokumentacji do ulgi badawczo-rozwojowej z wykorzystaniem modeli językowych (LLM).

## Architektura Rozwiązania

### Wielopoziomowa Walidacja

Kluczową innowacją jest **pipeline wielopoziomowej walidacji**, który zapewnia wysoką jakość generowanej dokumentacji poprzez iteracyjne sprawdzanie i poprawianie treści.

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT (YAML/JSON)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 1: Initial Generation                    │
│              ─────────────────────────────                  │
│              LLM generuje pierwszą wersję dokumentu         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 2: Structure Validation                  │
│              ─────────────────────────────                  │
│              Walidacja struktury markdown i sekcji          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 3: Content Validation                    │
│              ─────────────────────────────                  │
│              LLM sprawdza spójność merytoryczną             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 4: Legal Compliance                      │
│              ────────────────────────────                   │
│              Weryfikacja zgodności z wymogami prawnymi      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 5: Financial Validation                  │
│              ─────────────────────────────                  │
│              Walidacja kalkulacji kosztów kwalifikowanych   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 6: Iterative Refinement                  │
│              ─────────────────────────────                  │
│              LLM poprawia wykryte problemy                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 7: Final Validation                      │
│              ────────────────────────────                   │
│              Ostateczna weryfikacja i generowanie PDF       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT: PDF + YAML Report                │
└─────────────────────────────────────────────────────────────┘
```

### Struktura Walidacji

Każdy etap walidacji generuje raport w formacie YAML/JSON:

```yaml
validation_stage: content_validation
timestamp: "2026-01-13T10:30:00Z"
status: passed|failed|warning
score: 0.85
issues:
  - type: missing_section
    severity: critical
    location: "section:methodology"
    message: "Brak opisu metodologii badawczej"
    suggestion: "Dodaj sekcję opisującą metody badawcze"
  - type: inconsistent_data
    severity: warning
    location: "section:costs:personnel"
    message: "Suma kosztów osobowych nie zgadza się z kalkulacją"
corrections_applied:
  - location: "section:timeline"
    original: "Projekt rozpoczęty w Q1"
    corrected: "Projekt rozpoczęty w Q1 2025"
next_stage: legal_compliance
```

## Integracja z LiteLLM

Biblioteka wykorzystuje **LiteLLM** jako abstrakcyjną warstwę dostępu do różnych modeli LLM:

```python
from br_doc_generator import DocumentGenerator
from br_doc_generator.config import LLMConfig

config = LLMConfig(
    provider="openrouter",
    model="nvidia/nemotron-3-nano-30b-a3b:free",
    api_base="https://openrouter.ai/api/v1",
    temperature=0.3,  # Niższa temperatura dla precyzji
    max_tokens=4096
)

generator = DocumentGenerator(config)
```

### Wspierane Modele

| Provider | Model | Zastosowanie |
|----------|-------|--------------|
| OpenRouter | nemotron-3-nano | Generowanie dokumentacji |
| Ollama (local) | llama3.2 | Walidacja offline |
| Anthropic | claude-3 | Premium walidacja |
| OpenAI | gpt-4 | Backup provider |

## Formularz Wejściowy

System generuje interaktywny formularz YAML do szybkiego wypełnienia przez użytkownika:

```yaml
# BR Documentation Generator - Project Input Form
# Generated: 2026-01-13T10:00:00Z

project:
  name: "System automatyzacji procesów B+R"
  code: "BR-2025-001"
  fiscal_year: 2025
  company:
    name: "Softreck Sp. z o.o."
    nip: "1234567890"
    regon: "123456789"

timeline:
  start_date: "2025-01-01"
  end_date: "2025-12-31"
  milestones:
    - date: "2025-03-31"
      name: "Faza 1: Analiza"
      deliverables:
        - "Dokumentacja wymagań"
        - "Specyfikacja techniczna"
    - date: "2025-06-30"
      name: "Faza 2: Prototyp"
      deliverables:
        - "Działający prototyp"
        - "Testy jednostkowe"

innovation:
  type: "product"  # product|process|mixed
  scale: "company" # company|industry|global
  description: |
    Projekt dotyczy opracowania innowacyjnego systemu
    automatyzacji dokumentacji do ulgi B+R...
  novelty_aspects:
    - "Wykorzystanie wielosilnikowego OCR"
    - "Automatyczna klasyfikacja kosztów LLM"
    - "Integracja z polskimi systemami księgowymi"

methodology:
  systematic: true
  creative: true
  innovative: true
  risk_factors:
    - "Niepewność co do skuteczności OCR dla polskich dokumentów"
    - "Ryzyko niedostatecznej dokładności klasyfikacji LLM"
  research_methods:
    - "Eksperymenty porównawcze silników OCR"
    - "Testy A/B algorytmów klasyfikacji"

costs:
  personnel:
    employment:
      - name: "Jan Kowalski"
        role: "Lead Developer"
        percentage: 80  # % czasu na B+R
        gross_salary: 15000
        months: 12
    civil_contracts:
      - name: "Anna Nowak"
        role: "ML Engineer"
        contract_type: "UoD"
        amount: 50000
        
  materials:
    - name: "Serwery GPU"
      category: "equipment"
      amount: 25000
      description: "Sprzęt do trenowania modeli"
      
  external_services:
    - name: "Konsultacje naukowe"
      provider: "Politechnika Warszawska"
      amount: 15000
      description: "Ekspertyzy dot. algorytmów NLP"

documentation:
  existing_files:
    - path: "/docs/specification.md"
    - path: "/docs/research_notes.md"
  generate_sections:
    - "executive_summary"
    - "project_description"
    - "methodology"
    - "innovation_analysis"
    - "cost_calculation"
    - "timeline"
    - "risk_assessment"
    - "conclusions"
```

## Generowanie Dokumentacji

### Struktura Wyjściowa

System generuje kompletną dokumentację w formacie Markdown:

```markdown
# Dokumentacja Projektu B+R: [Nazwa Projektu]

## Streszczenie Wykonawcze
[Automatycznie wygenerowane na podstawie formularza]

## 1. Opis Projektu
### 1.1 Cel projektu
### 1.2 Zakres prac
### 1.3 Innowacyjność rozwiązania

## 2. Metodologia Badawcza
### 2.1 Systematyczność
### 2.2 Twórczość
### 2.3 Nowatorstwo

## 3. Harmonogram Realizacji
### 3.1 Kamienie milowe
### 3.2 Rezultaty poszczególnych etapów

## 4. Kalkulacja Kosztów Kwalifikowanych
### 4.1 Koszty osobowe
### 4.2 Materiały i surowce
### 4.3 Sprzęt specjalistyczny
### 4.4 Usługi zewnętrzne

## 5. Analiza Ryzyka
### 5.1 Zidentyfikowane ryzyka
### 5.2 Działania mitygujące

## 6. Podsumowanie
### 6.1 Wnioski
### 6.2 Rekomendacje

## Załączniki
- Załącznik A: Ewidencja czasu pracy
- Załącznik B: Zestawienie kosztów
- Załącznik C: Dokumentacja techniczna
```

### Konwersja do PDF

```python
from br_doc_generator import PDFRenderer

renderer = PDFRenderer(
    template="professional",
    company_logo="/path/to/logo.png",
    header="Dokumentacja B+R 2025",
    footer="Confidential - {company_name}"
)

pdf_path = renderer.render(
    markdown_content=documentation,
    output_path="/output/br_documentation_2025.pdf",
    metadata={
        "title": "Dokumentacja B+R",
        "author": "Softreck Sp. z o.o.",
        "keywords": ["B+R", "ulga podatkowa", "2025"]
    }
)
```

## Konfiguracja Docker

System zaprojektowany do pracy z lokalnym LLM bez dodawania Ollama do kontenera:

```yaml
# docker-compose.yml
version: '3.8'

services:
  brgenerator:
    build: .
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
      - LLM_LOCAL_URL=http://host.docker.internal:11434
    volumes:
      - ./output:/app/output
      - ./templates:/app/templates
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Użycie CLI

```bash
# Generowanie formularza wejściowego
br-doc generate-form --output project_form.yaml

# Generowanie dokumentacji z formularza
br-doc generate --input project_form.yaml --output docs/

# Walidacja istniejącej dokumentacji
br-doc validate --input existing_docs.md --report validation.yaml

# Renderowanie do PDF
br-doc render --input docs/documentation.md --output final.pdf
```

## Przykład Kompletnego Workflow

```python
from br_doc_generator import BRDocumentationPipeline
from br_doc_generator.config import load_config

# Załaduj konfigurację
config = load_config(".env")

# Inicjalizuj pipeline
pipeline = BRDocumentationPipeline(config)

# Załaduj formularz projektu
project_data = pipeline.load_form("project_form.yaml")

# Uruchom generowanie z walidacją
result = await pipeline.generate(
    project_data,
    validation_levels=["structure", "content", "legal", "financial"],
    max_iterations=3,  # Max poprawek per etap
    output_format="pdf"
)

# Sprawdź wyniki
print(f"Status: {result.status}")
print(f"Quality Score: {result.quality_score:.2%}")
print(f"Output: {result.output_path}")

# Zapisz raport walidacji
result.save_validation_report("validation_report.yaml")
```

## Podsumowanie

**brgenerator** stanowi znaczące rozszerzenie systemu B+R o możliwość automatycznego generowania dokumentacji zgodnej z wymaganiami polskiej ulgi badawczo-rozwojowej. Wielopoziomowa walidacja zapewnia wysoką jakość i spójność dokumentów, a integracja z LiteLLM umożliwia elastyczny wybór modeli LLM.

---

**Technologie:**
- Python 3.11+
- LiteLLM
- OpenRouter
- WeasyPrint (PDF)
- Pydantic (walidacja)
- asyncio (asynchroniczność)

**Licencja:** Proprietary - Softreck

**Tagi:** #BR #LLM #DocumentGeneration #Python #Automation #TaxRelief
