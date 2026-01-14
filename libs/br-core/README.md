# BR Core

Core utilities and base classes for B+R documentation system.

## Installation

```bash
pip install -e libs/br-core
```

## Features

- **Types**: Result types (Success/Failure), ValidationIssue, ValidationResult
- **Enums**: DocumentCategory, TimeScope, BRCategory, ExpenseType
- **Formatters**: format_currency, format_date, format_nip, format_percent
- **Validators**: validate_nip, validate_date_range, validate_fiscal_year

## Usage

```python
from br_core import (
    format_currency,
    format_nip,
    validate_nip,
    BRCategory,
    ValidationSeverity,
)

# Format currency
print(format_currency(1234.56))  # "1 234,56 zł"

# Validate NIP
valid, error = validate_nip("5881918662")
if not valid:
    print(f"Error: {error}")

# Use B+R category
category = BRCategory.PERSONNEL_EMPLOYMENT
print(category.nexus_component)  # "a"
```

## Variable References

Track variables with source URLs for document verification:

```python
from br_core.types import DocumentContext

ctx = DocumentContext(project_id="uuid", year=2025, base_url="http://localhost:81")
ref = ctx.add_variable("total_costs", 50000, "expenses/total")

print(ref.source_url)  # http://localhost:81/api/project/uuid/variable/expenses/total
print(ctx.get_footnotes())  # Markdown footnotes
```

## License

MIT © Softreck
