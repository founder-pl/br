# Podsumowanie Refaktoryzacji - BR Documentation Generator

**Data:** 14 stycznia 2026  
**Status:** Zakończono

---

## Wykonane prace

### 1. Wyodrębnione biblioteki Python

Utworzono 6 niezależnych, komplementarnych bibliotek w `libs/`:

| Biblioteka | Opis | Zależności |
|------------|------|------------|
| **br-core** | Typy, enumy, walidatory, formatery | pydantic, structlog |
| **md-render** | Konwersja MD→HTML→PDF | markdown, weasyprint, jinja2 |
| **br-data-sources** | DSL do ekstrakcji danych (SQL, REST, curl) | br-core, httpx, sqlalchemy |
| **br-validators** | Pipeline walidacji wielopoziomowej | br-core, pydantic |
| **br-llm-client** | Klient LLM z fallback | httpx, structlog |
| **br-variable-api** | API zmiennych z autentykacją | br-core, br-data-sources, fastapi |

### 2. Architektura warstwowa

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│   FastAPI App  │  CLI Tools  │  Web Interface                   │
└───────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│   br-variable-api (REST endpoints, auth, Nexus)                 │
│   ┌─────────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│   │ br-data-sources │  │   md-render   │  │  br-validators   │ │
│   └─────────────────┘  └───────────────┘  └──────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Core Layer                                │
│                         br-core                                  │
│   Types • Enums • Formatters • Validators                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Variable API - dostęp do zmiennych z weryfikacją URL

#### Nowe endpointy:

```bash
# Zmienna projektu
GET /api/project/{project_id}/variable/{source_name}/{path}

# Zmienna faktury
GET /api/invoice/{invoice_id}/variable/{variable_name}

# Pełne dane faktury (JSON, OCR, plain text)
GET /api/invoice/{invoice_id}?format=json|ocr|plain_text

# Obliczenie Nexus z URL weryfikacji
GET /api/project/{project_id}/nexus?year=2025

# Lista dostępnych źródeł
GET /api/variables
```

#### Przykład użycia:

```bash
# Pobierz sumę kosztów
curl http://localhost:81/api/project/uuid/variable/expenses_summary/total_gross

# Odpowiedź:
{
  "project_id": "uuid",
  "variable": {
    "name": "total_gross",
    "value": 50000.00,
    "source": "expenses_summary",
    "verification_url": "http://localhost:81/api/project/uuid/variable/expenses_summary/total_gross"
  },
  "footnote": "[total_gross](http://localhost:81/api/project/uuid/variable/expenses_summary/total_gross)"
}
```

### 4. Autentykacja Variable API

Obsługiwane metody:
- **API Key**: Header `X-API-Key` lub query param `?api_key=`
- **Basic Auth**: `Authorization: Basic base64(user:pass)`
- **Session Token**: JWT w cookie lub `Authorization: Bearer`
- **SSH Key**: Fingerprint z proxy SSH dla CLI

### 5. Footnotes w dokumentach

Dokumenty generowane z linkami weryfikacyjnymi:

```markdown
Koszty kwalifikowane B+R wyniosły **50 000,00 zł**[^1].
Wskaźnik Nexus: **0.8765**[^2].

---

## Przypisy źródłowe

[^1]: Źródło: [total_gross](http://localhost:81/api/project/uuid/variable/expenses_summary/total_gross)
[^2]: Źródło: [nexus](http://localhost:81/api/project/uuid/variable/nexus_calculation/nexus)
```

### 6. Moduł md-render

Konwersja Markdown do HTML i PDF:

```python
from md_render import md2html, html2pdf, md2pdf, get_br_document_css

# Markdown → HTML
html = md2html(markdown, title="Raport B+R", css=get_br_document_css())

# HTML → PDF
pdf_bytes = html2pdf(html, output_path="raport.pdf")

# Markdown → PDF (bezpośrednio)
pdf_bytes = md2pdf(markdown, output_path="raport.pdf")
```

### 7. Testy E2E

Utworzono testy E2E w `tests/e2e/test_doc_generator_e2e.py`:

- Walidacja struktury dokumentów
- Walidacja obliczeń finansowych
- Walidacja NIP
- Walidacja Nexus
- Walidacja renderowania HTML
- Testy Variable API

---

## Instalacja bibliotek

```bash
cd /home/tom/github/founder-pl/br

# Instalacja wszystkich bibliotek
pip install -e libs/br-core
pip install -e libs/md-render
pip install -e libs/br-data-sources
pip install -e libs/br-validators
pip install -e libs/br-llm-client
pip install -e libs/br-variable-api
```

## Uruchomienie testów

```bash
# Testy bibliotek
pytest libs/br-core/tests -v
pytest libs/md-render/tests -v
pytest libs/br-validators/tests -v
pytest libs/br-llm-client/tests -v

# Testy E2E
pytest tests/e2e/test_doc_generator_e2e.py -v
```

---

## Pliki utworzone/zmodyfikowane

### Nowe pliki:

```
libs/
├── README.md                              # Dokumentacja architektury
├── br-core/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/br_core/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── enums.py
│   │   ├── formatters.py
│   │   └── validators.py
│   └── tests/
│       ├── __init__.py
│       └── test_validators.py
├── md-render/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/md_render/
│   │   ├── __init__.py
│   │   ├── converter.py
│   │   └── styles.py
│   └── tests/
│       ├── __init__.py
│       └── test_converter.py
├── br-data-sources/
│   ├── pyproject.toml
│   ├── README.md
│   └── src/br_data_sources/
│       ├── __init__.py
│       ├── base.py
│       ├── sql.py
│       ├── rest.py
│       ├── curl.py
│       ├── registry.py
│       └── variable_tracker.py
├── br-validators/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/br_validators/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── structure.py
│   │   ├── legal.py
│   │   ├── financial.py
│   │   └── pipeline.py
│   └── tests/
│       ├── __init__.py
│       └── test_pipeline.py
├── br-llm-client/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/br_llm_client/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── fallback.py
│   │   └── prompts.py
│   └── tests/
│       ├── __init__.py
│       └── test_prompts.py
└── br-variable-api/
    ├── pyproject.toml
    ├── README.md
    └── src/br_variable_api/
        ├── __init__.py
        ├── models.py
        ├── auth.py
        └── router.py

src/api/routers/
└── variable_api.py                        # Integracja Variable API

src/api/services/doc_generator/
└── footnotes.py                           # Generator przypisów

tests/e2e/
└── test_doc_generator_e2e.py              # Testy E2E
```

### Zmodyfikowane pliki:

```
src/api/main.py                            # Dodano variable_api router
```

---

## Następne kroki (opcjonalne)

1. **br-validators** - wyodrębnić walidatory do osobnej biblioteki
2. **br-llm-client** - klient LLM z fallback jako osobna biblioteka
3. **Playwright tests** - testy UI dla strony doc-generator
4. **GraphQL API** - alternatywne API dla złożonych zapytań
