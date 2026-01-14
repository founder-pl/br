# BR Variable API

REST API for accessing B+R documentation variables with URL queries.

## Installation

```bash
pip install -e libs/br-variable-api
```

## Features

- **Variable access via URL**: `/api/project/{id}/variable/{source}/{path}`
- **Invoice data access**: `/api/invoice/{id}/variable/{name}`
- **Multiple auth methods**: API Key, Basic Auth, Session Token, SSH Key
- **Nexus calculation**: `/api/project/{id}/nexus`

## Usage

### Setup Router

```python
from fastapi import FastAPI
from br_variable_api import create_variable_router
from br_data_sources import get_data_registry
from your_app.database import get_db

app = FastAPI()

router = create_variable_router(
    get_db=get_db,
    data_registry=get_data_registry(),
)

app.include_router(router)
```

### API Endpoints

#### Project Variables

```bash
# Get variable from data source
curl http://localhost:81/api/project/{project_id}/variable/{source_name}?path={field}

# Examples:
curl http://localhost:81/api/project/uuid/variable/expenses_by_category?path=total_gross
curl http://localhost:81/api/project/uuid/variable/nexus_calculation/nexus
```

#### Invoice Variables

```bash
# Get invoice variable
curl http://localhost:81/api/invoice/{invoice_id}/variable/{variable_name}

# Get full invoice data
curl http://localhost:81/api/invoice/{invoice_id}?format=json
curl http://localhost:81/api/invoice/{invoice_id}?format=ocr
curl http://localhost:81/api/invoice/{invoice_id}?format=plain_text
```

#### Nexus Calculation

```bash
# Get Nexus indicator with verification URLs
curl http://localhost:81/api/project/{project_id}/nexus?year=2025
```

## Authentication

### API Key

```bash
# Header
curl -H "X-API-Key: your-key" http://localhost:81/api/variables

# Query param
curl http://localhost:81/api/variables?api_key=your-key
```

### Basic Auth

```bash
curl -u username:password http://localhost:81/api/variables
```

### Session Token (JWT)

```bash
curl -H "Authorization: Bearer eyJ..." http://localhost:81/api/variables
```

### SSH Key (for CLI)

When using SSH tunnel, the fingerprint is passed automatically.

```bash
# Via SSH tunnel
ssh -L 8081:localhost:81 user@server
curl http://localhost:8081/api/variables
```

## Environment Variables

```bash
# API Key
BR_API_KEY=your-secret-key

# Basic Auth
BR_API_USER=admin
BR_API_PASSWORD=secret

# JWT
JWT_SECRET_KEY=your-jwt-secret
```

## Document Footnotes

Variables are designed to be used as footnotes in generated documents:

```markdown
Koszty kwalifikowane B+R wyniosły **50 000,00 zł**[^1].

---

## Przypisy źródłowe

[^1]: Źródło: [total_gross](http://localhost:81/api/project/uuid/variable/expenses_by_category/total_gross)
```

## License

MIT © Softreck
