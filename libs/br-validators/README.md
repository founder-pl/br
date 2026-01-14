# BR Validators

Multi-level validation pipeline for B+R documentation.

## Installation

```bash
pip install -e libs/br-validators
```

## Features

- **StructureValidator**: Document structure, required sections, formatting
- **LegalValidator**: Legal compliance (NIP, B+R categories, art. 18d CIT)
- **FinancialValidator**: Financial calculations, amounts, Nexus indicator
- **ValidationPipeline**: Orchestration of all validators

## Usage

### Quick Validation

```python
from br_validators import create_default_pipeline

pipeline = create_default_pipeline()

result = await pipeline.validate(
    content=document_markdown,
    document_type="project_card",
    project_id="uuid-here",
    year=2025,
)

print(f"Valid: {result['valid']}")
print(f"Score: {result['overall_score']}")
print(f"Errors: {result['error_count']}")
print(f"Warnings: {result['warning_count']}")
```

### Individual Validators

```python
from br_validators import StructureValidator, ValidationContext

validator = StructureValidator()
context = ValidationContext(
    document_type="expense_registry",
    content=document_markdown,
)

result = await validator.validate(context)

for issue in result.issues:
    print(f"[{issue.severity.value}] {issue.message}")
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")
```

### Custom Pipeline

```python
from br_validators import (
    ValidationPipeline,
    StructureValidator,
    FinancialValidator,
)

# Only structure and financial validation
pipeline = ValidationPipeline(
    validators=[
        StructureValidator(),
        FinancialValidator(),
    ],
    stop_on_error=True,  # Stop on first error
)

result = await pipeline.validate(content, "nexus_calculation")
```

## Validation Stages

### 1. Structure Validation

Checks:
- Document has title and required sections
- Required fields present (NIP, year, etc.)
- Table formatting
- Empty sections

### 2. Legal Validation

Checks:
- NIP checksum validation
- B+R category references
- Legal references (art. 18d CIT)
- Expense qualification justifications
- Date consistency with fiscal year
- Related party disclosures

### 3. Financial Validation

Checks:
- No negative amounts
- No suspiciously large amounts
- Nexus indicator (0 ≤ nexus ≤ 1)
- Nexus component calculations
- Total/sum consistency
- Currency consistency
- VAT information
- Percentage values ≤ 100%

## Validation Result

```python
{
    "valid": True,
    "overall_score": 0.95,
    "error_count": 0,
    "warning_count": 2,
    "stages": {
        "structure": {"valid": True, "score": 1.0, "issues": [...]},
        "legal": {"valid": True, "score": 0.9, "issues": [...]},
        "financial": {"valid": True, "score": 0.95, "issues": [...]},
    },
    "all_issues": [
        {"severity": "warning", "message": "...", "code": "...", "suggestion": "..."}
    ],
    "document_type": "project_card",
    "content_length": 2500,
}
```

## Issue Codes

### Structure
- `DOC_TOO_SHORT` - Document under 100 characters
- `MISSING_TITLE` - No main heading
- `MISSING_SECTION` - Required section missing
- `MISSING_FIELD` - Required field missing
- `INVALID_TABLE_FORMAT` - Malformed table

### Legal
- `INVALID_NIP` - NIP checksum failure
- `MISSING_BR_CATEGORY` - No B+R category reference
- `MISSING_LEGAL_REFERENCE` - No legal citation
- `MISSING_QUALIFICATION_JUSTIFICATION` - No expense justification
- `INCONSISTENT_DATES` - Dates outside fiscal year
- `RELATED_PARTY_DISCLOSURE` - Missing transfer pricing info

### Financial
- `NEGATIVE_AMOUNT` - Amount < 0
- `SUSPICIOUS_AMOUNT` - Amount > 10M PLN
- `NEXUS_NEGATIVE` - Nexus < 0
- `NEXUS_EXCEEDS_ONE` - Nexus > 1
- `NEXUS_LOW` - Nexus < 0.5 (warning)
- `NEXUS_MISMATCH` - Calculated ≠ stated
- `NEXUS_MISSING` - No Nexus in nexus document
- `TOTAL_MISMATCH` - Sum doesn't match total
- `INVALID_PERCENTAGE` - Percentage > 100%
- `MIXED_CURRENCIES` - Multiple currencies without PLN

## License

MIT © Softreck
