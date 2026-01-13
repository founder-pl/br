# BR Documentation Generator - Project Structure

## Overview

```
br-doc-generator/
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
├── Dockerfile                # Docker container definition
├── LICENSE                   # MIT License
├── Makefile                  # Build automation
├── README.md                 # Project documentation
├── STRUCTURE.md              # This file
├── docker-compose.yml        # Docker orchestration
├── pyproject.toml            # Python package configuration
│
├── config/                   # Configuration files
│   └── example_form.yaml     # Example YAML form
│
├── src/br_doc_generator/     # Main package
│   ├── __init__.py           # Package exports & BRDocumentationPipeline
│   ├── cli.py                # Typer CLI interface
│   ├── config.py             # Pydantic configuration models
│   ├── llm_client.py         # LiteLLM integration
│   ├── models.py             # Data models
│   │
│   ├── generators/           # Document generation
│   │   ├── __init__.py
│   │   ├── document.py       # Markdown documentation generator
│   │   ├── form.py           # YAML form generator
│   │   └── pdf.py            # PDF renderer (WeasyPrint)
│   │
│   └── validators/           # Validation pipeline
│       ├── __init__.py
│       ├── base.py           # Abstract validator base
│       ├── structure.py      # Markdown structure validation
│       ├── content.py        # Content quality validation (LLM)
│       ├── legal.py          # Legal compliance (art. 18d CIT)
│       ├── financial.py      # Cost calculations validation
│       └── pipeline.py       # Validation orchestration
│
└── tests/                    # Test suite
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures
    └── test_validators.py    # Validator tests
```

## Module Descriptions

### Core Modules

| Module | Lines | Description |
|--------|-------|-------------|
| `__init__.py` | ~400 | Main exports, BRDocumentationPipeline class |
| `config.py` | ~200 | Pydantic settings (LLM, validation, PDF config) |
| `models.py` | ~350 | Data models (ProjectInput, costs, validation results) |
| `llm_client.py` | ~250 | LiteLLM async client with retry logic |
| `cli.py` | ~180 | Typer CLI commands |

### Validators

| Module | Lines | Description |
|--------|-------|-------------|
| `base.py` | ~80 | Abstract BaseValidator, ValidationContext |
| `structure.py` | ~150 | Markdown structure, sections, heading hierarchy |
| `content.py` | ~120 | LLM-based content quality check |
| `legal.py` | ~200 | B+R keywords, NIP checksum, legal terms |
| `financial.py` | ~180 | Cost calculations, deduction rates |
| `pipeline.py` | ~150 | Multi-stage orchestration |

### Generators

| Module | Lines | Description |
|--------|-------|-------------|
| `document.py` | ~300 | Full documentation generation via LLM |
| `form.py` | ~200 | YAML form templates with comments |
| `pdf.py` | ~150 | Markdown to PDF with WeasyPrint |

## Key Classes

### BRDocumentationPipeline
Main entry point for generating documentation.

```python
from br_doc_generator import BRDocumentationPipeline

pipeline = BRDocumentationPipeline.from_env()
result = await pipeline.generate(
    form_path="projekt.yaml",
    output_format="pdf"
)
```

### Validation Pipeline
Multi-stage validation with iterative refinement.

```python
from br_doc_generator import ValidationPipeline, LLMClient

llm = LLMClient(config.llm)
pipeline = ValidationPipeline(llm, config.validation)

result = await pipeline.run(
    document="# Documentation...",
    project_input=project,
    levels=["structure", "content", "legal", "financial"],
    max_iterations=3
)
```

### FormGenerator
YAML form generation and validation.

```python
from br_doc_generator import FormGenerator

form_gen = FormGenerator()
form_gen.generate_empty_form("AI Project", "form.yaml")

# Later...
data = FormGenerator.load_form("form.yaml")
errors = FormGenerator.validate_form(data)
```

## Configuration

### Environment Variables

```bash
# LLM Provider
LLM_DEFAULT_PROVIDER=openrouter|ollama|openai|anthropic

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Validation
VALIDATION_LEVELS=structure,content,legal,financial
VALIDATION_MAX_ITERATIONS=3
VALIDATION_MIN_QUALITY_SCORE=0.8

# PDF
PDF_TEMPLATE=professional|minimal|detailed
```

## Validation Stages

| Stage | Weight | Checks |
|-------|--------|--------|
| Structure | 0.20 | Sections, headings, markdown syntax |
| Content | 0.30 | Coherence, accuracy, language (LLM) |
| Legal | 0.30 | B+R keywords, NIP, cost categories |
| Financial | 0.20 | Cost totals, deduction rates |

## Cost Categories (art. 18d CIT)

| Category | Deduction Rate |
|----------|----------------|
| Personnel (employment) | 200% |
| Personnel (civil contracts) | 200% |
| Materials | 100% |
| Equipment | 100% |
| Expertise | 100% |
| External services | 100% |
| Depreciation | 100% |

## B+R Keywords (Polish)

| Criterion | Required Count | Keywords |
|-----------|----------------|----------|
| Systematyczność | 2+ | systematyczny, planowy, metodyczny, harmonogram |
| Twórczość | 2+ | twórczy, oryginalny, innowacyjny, kreatywny |
| Nowatorstwo | 3+ | nowatorski, przełomowy, pionierski, innowacja |
| Niepewność | 2+ | ryzyko, niepewność, wyzwanie, hipoteza |

## Dependencies

```toml
[project.dependencies]
litellm>=1.40.0      # Multi-provider LLM
pydantic>=2.5.0      # Data validation
pydantic-settings>=2.0.0
weasyprint>=60.0     # PDF rendering
structlog>=24.1.0    # Structured logging
typer>=0.9.0         # CLI framework
pyyaml>=6.0          # YAML parsing
httpx>=0.25.0        # Async HTTP
tenacity>=8.2.0      # Retry logic
markdown>=3.5.0      # Markdown processing
```

## Commands

```bash
# Install
pip install -e .

# Generate form
br-doc form --output projekt.yaml --name "AI System"

# Generate documentation  
br-doc generate --input projekt.yaml --output docs/

# Validate
br-doc validate --input docs/documentation.md --levels all

# Render PDF
br-doc render --input docs/documentation.md --output docs/documentation.pdf
```

## Docker Usage

```bash
# Build
docker build -t br-doc-generator .

# Run with OpenRouter
docker run -e OPENROUTER_API_KEY=sk-or-xxx \
           -v $(pwd)/output:/app/output \
           br-doc-generator generate --input /app/input/form.yaml

# Run with local Ollama
docker run -e LLM_DEFAULT_PROVIDER=ollama \
           -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
           -v $(pwd)/output:/app/output \
           br-doc-generator generate --input /app/input/form.yaml
```
