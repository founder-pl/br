# Document Generator Module

Autonomiczny moduł do generowania dokumentacji B+R i IP Box.

## Architektura

```
src/doc_generator/
├── __init__.py          # Eksporty modułu
├── data_sources.py      # DSL do ekstrakcji danych (SQL, REST, curl)
├── templates.py         # Rejestr szablonów dokumentów
├── engine.py            # Silnik generowania dokumentów
├── router.py            # Endpointy API FastAPI
└── README.md            # Dokumentacja
```

## Komponenty

### 1. Data Sources (DSL)

System umożliwia pobieranie danych z różnych źródeł:

- **SQLDataSource** - zapytania SQL do bazy PostgreSQL
- **RESTDataSource** - wywołania REST API
- **CurlDataSource** - komendy curl do zewnętrznych źródeł

```python
from src.doc_generator import DataSourceRegistry

registry = DataSourceRegistry()

# Dostępne źródła danych:
sources = registry.list_sources()
# - project_info
# - expenses_summary
# - expenses_by_category
# - timesheet_summary
# - timesheet_monthly_breakdown
# - revenues
# - contractors
# - documents_list
# - nexus_calculation
# - nbp_exchange_rate
```

### 2. Templates

Szablony dokumentów z metadanymi i wymaganiami danych:

```python
from src.doc_generator import TemplateRegistry

registry = TemplateRegistry()

# Dostępne szablony:
templates = registry.list_templates()
# - project_card (Karta Projektowa B+R)
# - timesheet_monthly (Miesięczny Rejestr Czasu Pracy)
# - expense_registry (Ewidencja Wydatków B+R)
# - nexus_calculation (Obliczenie Wskaźnika Nexus)
# - br_annual_summary (Roczne Podsumowanie B+R)
# - br_contract (Umowa o Świadczenie Usług B+R)
# - ip_box_procedure (Procedura Wewnętrzna IP Box)
# - tax_interpretation_request (Wniosek o Interpretację)
```

### 3. Engine

Silnik łączy źródła danych z szablonami:

```python
from src.doc_generator import DocumentEngine

engine = DocumentEngine(llm_base_url="http://localhost:11434")

# Generowanie dokumentu
result = await engine.generate_document(
    template_id="project_card",
    params={"project_id": "...", "year": 2025},
    db=session,
    use_llm=False  # True dla wzbogacenia LLM
)
```

## API Endpoints

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/doc-generator/templates` | GET | Lista szablonów |
| `/doc-generator/templates/{id}` | GET | Szczegóły szablonu |
| `/doc-generator/data-sources` | GET | Lista źródeł danych |
| `/doc-generator/preview-data` | POST | Podgląd danych |
| `/doc-generator/generate` | POST | Generowanie dokumentu |
| `/doc-generator/demo/{id}` | GET | Wersja demo |
| `/doc-generator/categories` | GET | Kategorie dokumentów |
| `/doc-generator/filter-options` | GET | Opcje filtrów |

## Kategorie dokumentów

| ID | Nazwa | Opis |
|----|-------|------|
| `project` | Projekty | Dokumenty projektowe B+R |
| `financial` | Finansowe | Ewidencje wydatków |
| `timesheet` | Czas pracy | Rejestry czasu pracy |
| `legal` | Prawne | Umowy i dokumenty prawne |
| `tax` | Podatkowe | Dokumenty podatkowe |
| `report` | Raporty | Raporty i podsumowania |

## Zakresy czasowe

| ID | Opis |
|----|------|
| `none` | Bez zakresu czasowego |
| `monthly` | Miesięczny |
| `quarterly` | Kwartalny |
| `yearly` | Roczny |
| `project` | Cały projekt |
| `custom` | Własny zakres |

## Dodawanie nowych szablonów

```python
from src.doc_generator.templates import (
    DocumentTemplate, DocumentCategory, TimeScope,
    TemplateDataRequirement, get_template_registry
)

registry = get_template_registry()

registry.register(DocumentTemplate(
    id="custom_template",
    name="Mój szablon",
    description="Opis szablonu",
    category=DocumentCategory.REPORT,
    time_scope=TimeScope.MONTHLY,
    data_requirements=[
        TemplateDataRequirement(
            source_name="expenses_summary",
            required_params=["project_id"],
            optional_params=["year", "month"],
            description="Lista wydatków"
        )
    ],
    template_content="""# {{project.name}}
    
## Wydatki
{% for exp in expenses %}
- {{exp.description}}: {{exp.gross_amount|format_currency}}
{% endfor %}
""",
    llm_prompt="Wygeneruj raport na podstawie danych..."
))
```

## Dodawanie nowych źródeł danych

```python
from src.doc_generator.data_sources import (
    SQLDataSource, RESTDataSource, get_data_registry
)

registry = get_data_registry()

# SQL source
registry.register(SQLDataSource(
    name="custom_query",
    query_template="SELECT * FROM table WHERE id = :id",
    description="Moje zapytanie",
    params_schema={"id": "ID rekordu"}
))

# REST source
registry.register(RESTDataSource(
    name="external_api",
    url_template="https://api.example.com/data/{id}",
    method="GET",
    description="Zewnętrzne API"
))
```

## Składnia szablonów

Silnik obsługuje uproszczoną składnię Jinja2:

### Zmienne
```
{{variable}}
{{object.property}}
{{value|filter}}
{{amount|format_currency}}
{{date|format_date}}
{{number|round(2)}}
```

### Pętle
```
{% for item in items %}
{{item.name}}
{% endfor %}
```

### Warunki
```
{% if condition %}
treść
{% else %}
alternatywa
{% endif %}
```

## Integracja z LLM

Szablony mogą być wzbogacane przez LLM (Ollama):

```python
result = await engine.generate_document(
    template_id="project_card",
    params={"project_id": "..."},
    db=session,
    use_llm=True,
    llm_model="llama3.2"
)
```

LLM otrzymuje:
- Prompt z szablonu (`llm_prompt`)
- Podsumowanie dostępnych danych
- Bazowy szablon dokumentu

## Wymagania

- Python 3.11+
- SQLAlchemy (async)
- FastAPI
- httpx
- structlog
- Ollama (opcjonalnie, dla LLM)
