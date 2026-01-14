# BR Libraries - Modular Python Packages

This directory contains modular Python libraries extracted from the BR Documentation Generator system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Application Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   FastAPI App   │  │    CLI Tools    │  │      Web Interface          │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘ │
└───────────┼─────────────────────┼────────────────────────┼──────────────────┘
            │                     │                        │
            ▼                     ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        br-variable-api                                   ││
│  │  REST endpoints for variable access, authentication, Nexus calculation  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│  ┌─────────────────────────────────┼───────────────────────────────────────┐│
│  │                                 ▼                                        ││
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐ ││
│  │  │  br-data-sources  │  │    md-render      │  │   br-validators      │ ││
│  │  │                   │  │                   │  │   (planned)          │ ││
│  │  │ • SQLDataSource   │  │ • md2html         │  │ • StructureValidator │ ││
│  │  │ • RESTDataSource  │  │ • html2pdf        │  │ • LegalValidator     │ ││
│  │  │ • CurlDataSource  │  │ • md2pdf          │  │ • FinancialValidator │ ││
│  │  │ • VariableTracker │  │ • StylePresets    │  │ • LLMReviewValidator │ ││
│  │  └─────────┬─────────┘  └───────────────────┘  └──────────────────────┘ ││
│  └────────────┼─────────────────────────────────────────────────────────────┘│
└───────────────┼──────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Core Layer                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                             br-core                                      ││
│  │  • Types: Result, Success, Failure, ValidationIssue, ValidationResult   ││
│  │  • Enums: DocumentCategory, TimeScope, BRCategory, ExpenseType          ││
│  │  • Formatters: format_currency, format_date, format_nip, format_percent ││
│  │  • Validators: validate_nip, validate_date_range, validate_fiscal_year  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Libraries

| Library | Description | Dependencies |
|---------|-------------|--------------|
| **br-core** | Core types, enums, formatters, validators | pydantic, structlog |
| **md-render** | Markdown → HTML → PDF conversion | markdown, weasyprint, jinja2 |
| **br-data-sources** | Data extraction DSL (SQL, REST, curl) | br-core, httpx, sqlalchemy |
| **br-validators** | Multi-level validation pipeline | br-core, pydantic |
| **br-llm-client** | LLM client with fallback | httpx, structlog |
| **br-variable-api** | Variable API with authentication | br-core, br-data-sources, fastapi |

## Installation

### Install All Libraries (Development)

```bash
cd /home/tom/github/founder-pl/br

# Install all libraries in development mode
pip install -e libs/br-core
pip install -e libs/md-render
pip install -e libs/br-data-sources
pip install -e libs/br-variable-api
```

### Install Individual Library

```bash
pip install -e libs/br-core
```

## Quick Start

### 1. Format Currency and Validate NIP

```python
from br_core import format_currency, validate_nip, BRCategory

# Format Polish currency
print(format_currency(12345.67))  # "12 345,67 zł"

# Validate NIP
valid, error = validate_nip("5881918662")
print(valid)  # True

# Use B+R category
category = BRCategory.PERSONNEL_EMPLOYMENT
print(category.nexus_component)  # "a"
```

### 2. Convert Markdown to PDF

```python
from md_render import md2pdf, get_br_document_css

markdown = """
# Raport B+R 2025

## Podsumowanie kosztów

| Kategoria | Kwota |
|-----------|-------|
| Wynagrodzenia | 50 000 zł |
| Materiały | 10 000 zł |
"""

pdf_bytes = md2pdf(
    markdown,
    output_path="raport.pdf",
    title="Raport B+R 2025",
    css=get_br_document_css()
)
```

### 3. Fetch Data and Track Variables

```python
from br_data_sources import get_data_registry, VariableTracker

# Get data registry
registry = get_data_registry()

# Fetch data
result = await registry.fetch(
    "expenses_by_category",
    {"project_id": "uuid-here"},
    db=session
)

# Track variables with source URLs
tracker = VariableTracker(
    base_url="http://localhost:81",
    project_id="uuid-here"
)

var = tracker.track(
    name="total_costs",
    value=result.data[0]["total_gross"],
    source_name="expenses_by_category",
    path="total_gross"
)

print(var.source_url)
# http://localhost:81/api/project/uuid-here/variable/expenses_by_category/total_gross

# Generate footnotes for document
print(tracker.get_footnotes_markdown())
```

### 4. Setup Variable API

```python
from fastapi import FastAPI
from br_variable_api import create_variable_router
from br_data_sources import get_data_registry

app = FastAPI()

router = create_variable_router(
    get_db=get_db,  # Your DB dependency
    data_registry=get_data_registry(),
)

app.include_router(router)

# Now you can access:
# GET /api/project/{id}/variable/{source}/{path}
# GET /api/invoice/{id}/variable/{name}
# GET /api/project/{id}/nexus
```

## API Endpoints

### Variable Access

```bash
# Project variable
curl http://localhost:81/api/project/{project_id}/variable/expenses_by_category/total_gross

# Invoice variable
curl http://localhost:81/api/invoice/{invoice_id}/variable/gross_amount

# Invoice data (JSON, plain text, or OCR)
curl http://localhost:81/api/invoice/{invoice_id}?format=json
curl http://localhost:81/api/invoice/{invoice_id}?format=ocr

# Nexus calculation with verification URLs
curl http://localhost:81/api/project/{project_id}/nexus?year=2025
```

### Authentication

```bash
# API Key
curl -H "X-API-Key: your-key" http://localhost:81/api/variables

# Basic Auth
curl -u username:password http://localhost:81/api/variables

# Bearer Token
curl -H "Authorization: Bearer eyJ..." http://localhost:81/api/variables
```

## Document Footnotes

Generated documents include verification URLs as footnotes:

```markdown
Koszty kwalifikowane B+R wyniosły **50 000,00 zł**[^1].
Wskaźnik Nexus: **0.8765**[^2].

---

## Przypisy źródłowe

[^1]: Źródło: [total_gross](http://localhost:81/api/project/uuid/variable/expenses_by_category/total_gross)
[^2]: Źródło: [nexus](http://localhost:81/api/project/uuid/variable/nexus_calculation/nexus)
```

## Testing

```bash
# Run all library tests
pytest libs/br-core/tests -v
pytest libs/md-render/tests -v
pytest libs/br-data-sources/tests -v
pytest libs/br-variable-api/tests -v

# Run E2E tests for doc-generator
pytest tests/e2e/test_doc_generator_e2e.py -v
```

## Environment Variables

```bash
# API Authentication
BR_API_KEY=your-secret-key
BR_API_USER=admin
BR_API_PASSWORD=secret
JWT_SECRET_KEY=your-jwt-secret

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/br_system

# LLM (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_API_BASE=http://localhost:11434
```

## License

MIT © Softreck
