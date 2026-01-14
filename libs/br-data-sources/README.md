# BR Data Sources

Data source DSL for B+R documentation - unified interface for SQL, REST, and external sources.

## Installation

```bash
pip install -e libs/br-data-sources
```

## Features

- **SQLDataSource**: PostgreSQL queries with parameter binding
- **RESTDataSource**: HTTP API calls
- **CurlDataSource**: External command execution
- **VariableTracker**: Track variables with source URLs for verification

## Usage

### Basic Usage

```python
from br_data_sources import get_data_registry, VariableTracker

# Get registry
registry = get_data_registry()

# Fetch data
result = await registry.fetch(
    "expenses_by_category",
    {"project_id": "uuid-here"},
    db=session
)

print(result.data)
```

### Variable Tracking

Track all variables with their source URLs for document verification:

```python
from br_data_sources import VariableTracker

tracker = VariableTracker(
    base_url="http://localhost:81",
    project_id="project-uuid"
)

# Track a variable
var = tracker.track(
    name="total_costs",
    value=50000.00,
    source_name="expenses_by_category",
    path="total_gross"
)

print(var.source_url)
# http://localhost:81/api/project/project-uuid/variable/expenses_by_category/total_gross

# Track invoice variable
invoice_var = tracker.track_invoice(
    invoice_id="inv-123",
    variable_name="gross_amount",
    value=1234.56
)

print(invoice_var.source_url)
# http://localhost:81/api/invoice/inv-123/variable/gross_amount

# Generate footnotes
print(tracker.get_footnotes_markdown())
```

### Custom Data Sources

```python
from br_data_sources import SQLDataSource, RESTDataSource

# Custom SQL source
custom_sql = SQLDataSource(
    name="custom_query",
    query_template="SELECT * FROM table WHERE id = :id",
    description="Custom query",
    params_schema={"id": "Record ID"}
)

# Custom REST source
custom_rest = RESTDataSource(
    name="external_api",
    url_template="https://api.example.com/data/{id}",
    method="GET",
    description="External API"
)

registry.register(custom_sql)
registry.register(custom_rest)
```

## API URLs

All variables can be accessed via:
- Project variables: `/api/project/{project_id}/variable/{source_name}/{path}`
- Invoice variables: `/api/invoice/{invoice_id}/variable/{variable_name}`

## License

MIT © Softreck
