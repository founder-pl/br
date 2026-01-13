# BR Documentation Generator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatyczny generator dokumentacji B+R (ulga podatkowa na badania i rozwój) z wielopoziomową walidacją i integracją LLM.

## 🎯 Funkcjonalności

- **Generowanie dokumentacji** - automatyczne tworzenie kompletnej dokumentacji B+R
- **Multi-level walidacja** - 4-etapowy pipeline walidacji (struktura, treść, prawo, finanse)
- **Integracja LLM** - obsługa OpenRouter, Ollama, OpenAI, Anthropic przez LiteLLM
- **Formularze YAML** - interaktywne formularze z komentarzami i przykładami
- **Eksport PDF** - profesjonalne dokumenty z szablonami

## 📋 Wymagania

- Python 3.11+
- Klucz API OpenRouter lub lokalny Ollama

## 🚀 Instalacja

```bash
# Klonowanie
git clone https://github.com/softreck/brgenerator.git
cd brgenerator

# Instalacja
pip install -e .

# Konfiguracja
cp .env.example .env
# Edytuj .env i dodaj klucz API
```

## ⚡ Szybki start

### 1. Wygeneruj formularz

```bash
br-doc form --output projekt.yaml --name "System AI"
```

### 2. Wypełnij formularz

Edytuj `projekt.yaml` - uzupełnij dane firmy, opis projektu, koszty.

### 3. Wygeneruj dokumentację

```bash
br-doc generate --input projekt.yaml --output dokumentacja.md
```

### 4. Waliduj dokumentację

```bash
br-doc validate --input dokumentacja.md --levels all
```

### 5. Renderuj PDF

```bash
br-doc render --input dokumentacja.md --output dokumentacja.pdf
```

## 📖 Użycie programatyczne

```python
import asyncio
from br_doc_generator import (
    DocumentGenerator,
    FormGenerator,
    ValidationPipeline,
    LLMClient
)
from br_doc_generator.config import AppConfig

async def main():
    # Konfiguracja
    config = AppConfig()
    
    # Wygeneruj formularz
    form_gen = FormGenerator(config)
    form_gen.generate_empty_form("System AI", "projekt.yaml")
    
    # Załaduj wypełniony formularz
    project_data = FormGenerator.load_form("projekt.yaml")
    
    # Waliduj dane wejściowe
    errors = FormGenerator.validate_form(project_data)
    if errors:
        print("Błędy formularza:", errors)
        return
    
    # Generuj dokumentację
    llm = LLMClient(config.llm)
    doc_gen = DocumentGenerator(llm, config)
    
    document = await doc_gen.generate(project_data)
    
    # Waliduj dokumentację
    pipeline = ValidationPipeline(config.validation, llm)
    result = await pipeline.validate(document, project_data)
    
    print(f"Jakość: {result.quality_score:.1%}")
    print(f"Status: {result.status}")
    
    # Zapisz
    with open("dokumentacja.md", "w") as f:
        f.write(document)

asyncio.run(main())
```

## 🔧 Konfiguracja

### Zmienne środowiskowe (.env)

```bash
# LLM Provider (openrouter/ollama/openai/anthropic)
LLM_DEFAULT_PROVIDER=openrouter

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free

# Ollama (lokalny)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Walidacja
VALIDATION_LEVELS=structure,content,legal,financial
VALIDATION_MAX_ITERATIONS=3
VALIDATION_MIN_QUALITY_SCORE=0.8

# PDF
PDF_TEMPLATE=professional
```

### Poziomy walidacji

| Poziom | Opis | Waga |
|--------|------|------|
| `structure` | Struktura Markdown, sekcje, nagłówki | 0.2 |
| `content` | Spójność treści, jakość języka (LLM) | 0.3 |
| `legal` | Zgodność z art. 18d CIT, kryteria B+R | 0.3 |
| `financial` | Kalkulacje kosztów, stawki odliczeń | 0.2 |

## 📊 Pipeline walidacji

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Structure  │────▶│   Content   │────▶│    Legal    │────▶│  Financial  │
│  Validator  │     │  Validator  │     │  Validator  │     │  Validator  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   Markdown            LLM Check          Art. 18d CIT        Kalkulacje
   Hierarchy           Coherence          Keywords            Stawki 200%
   Sections            Accuracy           NIP Checksum        Sumy kosztów
```

## 📁 Struktura projektu

```
brgenerator/
├── src/br_doc_generator/
│   ├── __init__.py          # Eksporty główne
│   ├── cli.py               # Interfejs CLI (Typer)
│   ├── config.py            # Konfiguracja Pydantic
│   ├── llm_client.py        # Klient LiteLLM
│   ├── models.py            # Modele danych
│   ├── generators/
│   │   ├── document.py      # Generator dokumentacji
│   │   ├── form.py          # Generator formularzy YAML
│   │   └── pdf.py           # Renderer PDF (WeasyPrint)
│   └── validators/
│       ├── base.py          # Bazowy walidator
│       ├── structure.py     # Walidacja struktury
│       ├── content.py       # Walidacja treści (LLM)
│       ├── legal.py         # Walidacja prawna B+R
│       ├── financial.py     # Walidacja finansowa
│       └── pipeline.py      # Orkiestracja pipeline
├── tests/                   # Testy jednostkowe
├── config/                  # Przykładowe konfiguracje
├── pyproject.toml
├── .env.example
└── README.md
```

## 🏛️ Kryteria B+R (art. 18d CIT)

Generator automatycznie weryfikuje obecność kluczowych kryteriów:

### Systematyczność
Słowa kluczowe: systematyczny, planowy, metodyczny, harmonogram, etapy, fazy

### Twórczość  
Słowa kluczowe: twórczy, oryginalny, innowacyjny, kreatywny, nowatorski, unikatowy

### Nowatorstwo
Słowa kluczowe: nowatorski, przełomowy, pionierski, innowacja, nowa wiedza, stan techniki

### Niepewność badawcza
Słowa kluczowe: ryzyko, niepewność, wyzwanie, problem badawczy, hipoteza

## 💰 Kategorie kosztów B+R

| Kategoria | Stawka odliczenia |
|-----------|-------------------|
| Wynagrodzenia (umowa o pracę) | 200% |
| Wynagrodzenia (umowy cywilnoprawne) | 200% |
| Materiały i surowce | 100% |
| Sprzęt specjalistyczny | 100% |
| Ekspertyzy i opinie | 100% |
| Usługi badawcze zewnętrzne | 100% |
| Amortyzacja | 100% |

## 🐳 Docker

```bash
# Budowanie
docker build -t brgenerator .

# Uruchomienie z lokalnym Ollama
docker run -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
           -v $(pwd)/output:/app/output \
           brgenerator generate --input /app/input/projekt.yaml
```

## 🧪 Testowanie

```bash
# Wszystkie testy
pytest

# Z coverage
pytest --cov=br_doc_generator --cov-report=html

# Tylko unit testy
pytest tests/unit/

# Tylko integracyjne
pytest tests/integration/
```

## 📝 Przykładowy formularz

```yaml
project:
  name: "System automatycznej analizy dokumentów"
  description: "Innowacyjny system wykorzystujący AI do OCR i NLP"
  
company:
  name: "Softreck Sp. z o.o."
  nip: "1234567890"
  
timeline:
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  
innovation:
  type: product  # product/process/mixed
  scale: company  # company/industry/global
  
costs:
  personnel_employment:
    - name: "Jan Kowalski"
      role: "Lead Developer"
      monthly_salary: 15000
      br_time_percent: 80
      
  materials:
    - description: "Serwery GPU"
      amount: 50000
```

## 🤝 Współpraca

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/nowa-funkcja`)
3. Commit (`git commit -am 'Dodaj nową funkcję'`)
4. Push (`git push origin feature/nowa-funkcja`)
5. Otwórz Pull Request

## 📄 Licencja

MIT License - zobacz [LICENSE](LICENSE)

## 👤 Autor

**Softreck** - [softreck.com](https://softreck.com)

---

*Dokumentacja B+R zgodna z art. 18d ustawy o podatku dochodowym od osób prawnych (CIT)*
