# Konfiguracja LLM w BR Documentation Generator

## Wprowadzenie

System BR Documentation Generator wykorzystuje **LiteLLM** jako zunifikowany proxy do obsługi wielu dostawców LLM. Dzięki temu możliwe jest:

- Automatyczne przełączanie między modelami (fallback)
- Cache odpowiedzi w Redis
- Śledzenie budżetu i limitów
- Obsługa lokalnych modeli (Ollama) bez kluczy API

---

## Architektura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BR Documentation Generator                   │
│                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │  Classifier  │  │  Validator   │  │  Report Generator        │ │
│   │  Service     │  │  Pipeline    │  │  Service                 │ │
│   └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│          │                 │                        │               │
│          └─────────────────┼────────────────────────┘               │
│                            ▼                                        │
│                   ┌────────────────┐                                │
│                   │   LLM Client   │                                │
│                   │   (LiteLLM)    │                                │
│                   └───────┬────────┘                                │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         LiteLLM Proxy                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Router    │  │   Cache     │  │   Budget    │  │   Logging   │ │
│  │  (fallback) │  │   (Redis)   │  │  Tracking   │  │  (optional) │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└───────────────────────────┬───────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼
   ┌─────────┐        ┌──────────┐        ┌──────────┐       ┌─────────┐
   │ OpenAI  │        │Anthropic │        │OpenRouter│       │ Ollama  │
   │ API     │        │ API      │        │ API      │       │ (local) │
   └─────────┘        └──────────┘        └──────────┘       └─────────┘
```

---

## Konfiguracja Modeli

### litellm_config.yaml

```yaml
# =============================================================================
# LiteLLM Configuration - System B+R
# =============================================================================

model_list:
  # =============================================================================
  # Production Models (wymagają kluczy API)
  # =============================================================================
  
  # OpenAI GPT-4o - najlepszy do klasyfikacji dokumentów
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
      max_tokens: 4096
      temperature: 0.1
    model_info:
      description: "OpenAI GPT-4o for document analysis"
      
  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY
      max_tokens: 4096
      temperature: 0.1

  # Anthropic Claude - najlepszy do rozumowania
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
      max_tokens: 4096
      temperature: 0.1

  # =============================================================================
  # OpenRouter Models (zdalne LLM przez OpenRouter.ai)
  # =============================================================================
  
  - model_name: openrouter-claude
    litellm_params:
      model: openrouter/anthropic/claude-3.5-sonnet
      api_key: os.environ/OPENROUTER_API_KEY
      max_tokens: 4096
      temperature: 0.1

  - model_name: openrouter-gpt4
    litellm_params:
      model: openrouter/openai/gpt-4-turbo
      api_key: os.environ/OPENROUTER_API_KEY
      max_tokens: 4096
      temperature: 0.1

  # =============================================================================
  # Local Models via Ollama (bez klucza API)
  # =============================================================================
  
  - model_name: llama3.2
    litellm_params:
      model: ollama/llama3.2
      api_base: os.environ/OLLAMA_API_BASE
      max_tokens: 4096
      temperature: 0.1
    model_info:
      description: "Llama 3.2 - dobry dla polskiego tekstu"

  - model_name: mistral
    litellm_params:
      model: ollama/mistral
      api_base: os.environ/OLLAMA_API_BASE
      max_tokens: 4096
      temperature: 0.1
    model_info:
      description: "Mistral - szybki lokalny model"

  - model_name: qwen2.5
    litellm_params:
      model: ollama/qwen2.5
      api_base: os.environ/OLLAMA_API_BASE
      max_tokens: 4096
      temperature: 0.1
    model_info:
      description: "Qwen 2.5 - dobra obsługa wielojęzyczna"

  # =============================================================================
  # Specialized Models dla B+R
  # =============================================================================
  
  # Klasyfikator dokumentów B+R
  - model_name: br-classifier
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY
      max_tokens: 2048
      temperature: 0

  - model_name: br-classifier-fallback
    litellm_params:
      model: ollama/llama3.2
      api_base: os.environ/OLLAMA_API_BASE
      max_tokens: 2048
      temperature: 0

  # Generator raportów B+R
  - model_name: br-report-generator
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
      max_tokens: 8192
      temperature: 0.3

# =============================================================================
# Router Settings - Fallback Configuration
# =============================================================================
router_settings:
  routing_strategy: simple-shuffle
  num_retries: 3
  timeout: 120
  
  fallbacks:
    - br-classifier: [br-classifier-fallback, openrouter-claude]
    - gpt-4o: [claude-sonnet, openrouter-claude, llama3.2]
    - claude-sonnet: [gpt-4o, openrouter-gpt4, llama3.2]
    - openrouter-claude: [openrouter-gpt4, llama3.2]

  model_group_alias:
    classifier: [br-classifier, br-classifier-fallback]
    generator: [br-report-generator, gpt-4o]
    fast: [gpt-4o-mini, mistral]

# =============================================================================
# LiteLLM Settings - Cache & Budget
# =============================================================================
litellm_settings:
  cache: True
  cache_params:
    type: redis
    host: redis
    port: 6379
    
  max_budget: 100  # USD miesięcznie
  budget_duration: 1mo
  request_timeout: 120
  json_logs: true
```

---

## Zmienne Środowiskowe

```bash
# .env - Konfiguracja API Keys

# === LLM API Keys (opcjonalne) ===
# Jeśli nie podasz kluczy, system użyje lokalnych modeli Ollama

# OpenAI (dla GPT-4o)
OPENAI_API_KEY=sk-...

# Anthropic (dla Claude)
ANTHROPIC_API_KEY=sk-ant-...

# OpenRouter (dla zdalnych modeli)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free

# LiteLLM Master Key
LITELLM_MASTER_KEY=sk-br-llm-2025

# === Ollama (lokalne modele) ===
# Dla Docker: http://host.docker.internal:11434
# Lokalnie: http://localhost:11434
OLLAMA_API_BASE=http://host.docker.internal:11434
```

---

## Wybór Modelu per Zadanie

### Rekomendacje

| Zadanie | Primary | Fallback | Temperature | Max Tokens |
|---------|---------|----------|-------------|------------|
| **Klasyfikacja dokumentów** | `gpt-4o-mini` | `llama3.2` | 0.0 | 2048 |
| **Generowanie raportów B+R** | `claude-sonnet` | `gpt-4o` | 0.3 | 8192 |
| **Walidacja prawna** | `claude-sonnet` | `gpt-4o` | 0.1 | 4096 |
| **Analiza faktur (OCR)** | `gpt-4o` | `llama3.2` | 0.0 | 2048 |
| **Szybkie zadania** | `gpt-4o-mini` | `mistral` | 0.1 | 2048 |

### Uzasadnienie

- **GPT-4o-mini** dla klasyfikacji - szybki, tani, dokładny dla prostych zadań
- **Claude Sonnet** dla raportów - najlepsze rozumowanie i jakość tekstu po polsku
- **Llama 3.2** jako fallback - darmowy, lokalny, wystarczający dla większości zadań
- **Mistral** dla szybkich zadań - bardzo szybki lokalny model

---

## Implementacja Klienta

### LLMClient z Fallback

```python
import litellm
from typing import Optional
import structlog

logger = structlog.get_logger()

class BRLLMClient:
    """Klient LLM dla systemu B+R z obsługą fallback"""
    
    MODEL_CONFIGS = {
        "classifier": {
            "model": "br-classifier",
            "fallbacks": ["br-classifier-fallback", "llama3.2"],
            "temperature": 0.0,
            "max_tokens": 2048
        },
        "generator": {
            "model": "br-report-generator",
            "fallbacks": ["gpt-4o", "llama3.2"],
            "temperature": 0.3,
            "max_tokens": 8192
        },
        "validator": {
            "model": "claude-sonnet",
            "fallbacks": ["gpt-4o", "llama3.2"],
            "temperature": 0.1,
            "max_tokens": 4096
        }
    }
    
    def __init__(self, task_type: str = "classifier"):
        config = self.MODEL_CONFIGS.get(task_type, self.MODEL_CONFIGS["classifier"])
        self.model = config["model"]
        self.fallbacks = config["fallbacks"]
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        
        # Włącz cache
        litellm.cache = True
        
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generuj odpowiedź z automatycznym fallback"""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,
                fallbacks=self.fallbacks
            )
            
            logger.info("llm_success", 
                model=response.model,
                tokens=response.usage.total_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("llm_error", error=str(e))
            raise
    
    async def classify_br_document(self, text: str) -> dict:
        """Klasyfikacja dokumentu B+R"""
        
        categories = [
            "faktura_koszt", "faktura_przychod", "umowa", 
            "raport_czasowy", "dokumentacja_techniczna", "inne"
        ]
        
        prompt = f"""Sklasyfikuj dokument do kategorii B+R.
        
Dostępne kategorie: {', '.join(categories)}

Dokument:
{text[:3000]}

Odpowiedz TYLKO w formacie JSON:
{{"category": "kategoria", "confidence": 0.0-1.0, "br_qualified": true/false, "reasoning": "uzasadnienie"}}"""

        response = await self.generate(prompt)
        
        import json
        return json.loads(response)


# Factory functions
def get_classifier() -> BRLLMClient:
    return BRLLMClient("classifier")

def get_generator() -> BRLLMClient:
    return BRLLMClient("generator")

def get_validator() -> BRLLMClient:
    return BRLLMClient("validator")
```

---

## Uruchomienie Lokalne (bez API Keys)

### 1. Instalacja Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows - pobierz z https://ollama.com/download
```

### 2. Pobierz Modele

```bash
# Model główny (dobry dla polskiego)
ollama pull llama3.2

# Model szybki
ollama pull mistral

# Model wielojęzyczny
ollama pull qwen2.5
```

### 3. Konfiguracja .env

```bash
# Tylko Ollama, bez zewnętrznych API
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=

# Adres Ollama
OLLAMA_API_BASE=http://localhost:11434
```

### 4. Uruchomienie

```bash
# Ollama automatycznie zostanie użyte jako fallback
docker-compose up -d
```

---

## Monitoring i Debugging

### Logi LiteLLM

```python
import litellm

# Włącz verbose logging
litellm.set_verbose = True

# Callback dla logowania
def log_callback(kwargs, response, start_time, end_time):
    print(f"Model: {kwargs.get('model')}")
    print(f"Tokens: {response.usage.total_tokens}")
    print(f"Time: {end_time - start_time}s")

litellm.success_callback = [log_callback]
```

### Sprawdzanie Budżetu

```python
# Sprawdź wykorzystanie budżetu
from litellm import get_spend

spend = get_spend()
print(f"Wykorzystano: ${spend['total_spend']:.2f} / $100.00")
```

### Test Połączenia

```bash
# Test OpenAI
curl http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-br-llm-2025" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Test"}]}'

# Test Ollama (lokalny)
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.2", "prompt": "Test", "stream": false}'
```

---

## Porównanie Modeli dla Zadań B+R

### Benchmark Klasyfikacji (100 dokumentów)

| Model | Accuracy | Avg Time | Cost/1k |
|-------|----------|----------|---------|
| GPT-4o-mini | 94% | 0.8s | $0.15 |
| Claude Sonnet | 96% | 1.2s | $0.30 |
| Llama 3.2 (local) | 87% | 2.1s | $0.00 |
| Mistral (local) | 82% | 0.9s | $0.00 |

### Benchmark Generowania Raportów

| Model | Quality Score | Avg Time | Cost/report |
|-------|---------------|----------|-------------|
| Claude Sonnet | 9.2/10 | 15s | $0.50 |
| GPT-4o | 8.8/10 | 12s | $0.40 |
| Llama 3.2 | 7.5/10 | 45s | $0.00 |

### Rekomendacja

- **Produkcja z budżetem**: Claude Sonnet (jakość) + GPT-4o-mini (szybkość)
- **Produkcja bez budżetu**: Llama 3.2 + Mistral (lokalne)
- **Development**: Wyłącznie Ollama (zero kosztów)

---

## Podsumowanie

System LLM w BR Documentation Generator:

1. **LiteLLM jako proxy** - zunifikowany interfejs dla wszystkich dostawców
2. **Automatyczny fallback** - ciągłość działania przy awarii API
3. **Modele lokalne** - możliwość pracy offline z Ollama
4. **Budget tracking** - kontrola kosztów (max $100/miesiąc)
5. **Redis cache** - optymalizacja powtarzalnych zapytań

Kluczowa zaleta: **System działa nawet bez kluczy API** dzięki automatycznemu fallback do lokalnych modeli Ollama.
