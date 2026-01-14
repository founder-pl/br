# BR LLM Client

LLM client with fallback support for B+R documentation.

## Installation

```bash
pip install -e libs/br-llm-client
```

## Features

- **Multi-provider support**: OpenAI, Anthropic, Ollama, OpenRouter, LiteLLM
- **Automatic fallback**: Chain models with priority-based fallback
- **B+R prompts**: Pre-built templates for expense qualification, document review
- **Async support**: Full async/await interface

## Usage

### Basic Generation

```python
from br_llm_client import LLMClient

# OpenAI
client = LLMClient(provider="openai", model="gpt-4o-mini")

response = await client.generate(
    prompt="Opisz projekt B+R dotyczący automatyzacji",
    system_prompt="Jesteś ekspertem od ulgi B+R.",
    temperature=0.7,
)

print(response.content)
print(f"Tokens: {response.tokens_used}")
```

### Fallback Chain

```python
from br_llm_client import FallbackChain, ModelConfig

chain = FallbackChain([
    ModelConfig(provider="openai", model="gpt-4o-mini", priority=1),
    ModelConfig(provider="anthropic", model="claude-3-haiku-20240307", priority=2),
    ModelConfig(provider="ollama", model="llama3.2", priority=3),
])

# Automatically tries next model on failure
response = await chain.generate("Opisz wydatek B+R")
print(f"Model used: {response.model}")
```

### B+R Prompts

```python
from br_llm_client import PromptBuilder, LLMClient

builder = PromptBuilder()
client = LLMClient(provider="ollama", model="llama3.2")

# Expense qualification
system, user = builder.build_expense_qualification(
    description="Zakup serwera do obliczeń ML",
    amount=15000,
    vendor="Dell Sp. z o.o.",
    category="equipment",
    date="2025-01-10",
)

response = await client.generate(user, system_prompt=system)

# Document review
system, user = builder.build_document_review(
    document_content=document_markdown,
    document_type="project_card",
    year=2025,
)

response = await client.generate(user, system_prompt=system)
```

## Supported Providers

| Provider | Models | Environment Variable |
|----------|--------|---------------------|
| openai | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | `OPENAI_API_KEY` |
| anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku | `ANTHROPIC_API_KEY` |
| ollama | llama3.2, mistral, codellama, etc. | `OLLAMA_API_BASE` |
| openrouter | Any model via OpenRouter | `OPENROUTER_API_KEY` |
| litellm | Any model via LiteLLM proxy | `LITELLM_MASTER_KEY` |

## Environment Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
LITELLM_MASTER_KEY=sk-...

# Base URLs (optional)
OLLAMA_API_BASE=http://localhost:11434
LITELLM_API_BASE=http://localhost:4000
```

## Pre-built Prompts

| Template | Description |
|----------|-------------|
| `expense_qualification` | Qualify expense for B+R deduction |
| `document_review` | Review B+R document for completeness |
| `nexus_explanation` | Explain Nexus calculation for IP Box |
| `project_summary` | Generate project summary |

## Response Object

```python
@dataclass
class LLMResponse:
    content: str           # Generated text
    model: str             # Model used
    provider: str          # Provider used
    tokens_used: int       # Total tokens
    latency_ms: float      # Response time
    metadata: dict         # Provider-specific data
    error: Optional[str]   # Error message if failed
    
    @property
    def success(self) -> bool:
        return self.error is None
```

## License

MIT © Softreck
