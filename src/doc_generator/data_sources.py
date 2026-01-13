"""
Data Source DSL - Bridge between SQL, REST API, and external sources.

Provides a unified interface for extracting data from various sources
to be used in document generation.
"""
import json
import re
import httpx
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

logger = structlog.get_logger()


@dataclass
class DataSourceResult:
    """Result from a data source query"""
    data: Any
    source_type: str
    query_info: str
    fetched_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    async def fetch(self, params: Dict[str, Any]) -> DataSourceResult:
        """Fetch data from the source"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return schema/description of available data"""
        pass


class SQLDataSource(DataSource):
    """SQL-based data source for PostgreSQL queries"""
    
    def __init__(self, name: str, query_template: str, description: str, 
                 params_schema: Dict[str, str]):
        self.name = name
        self.query_template = query_template
        self.description = description
        self.params_schema = params_schema
    
    async def fetch(self, params: Dict[str, Any], db: AsyncSession) -> DataSourceResult:
        try:
            query = self.query_template
            for key, value in params.items():
                if value is not None:
                    query = query.replace(f":{key}", str(value) if not isinstance(value, str) else f"'{value}'")
            
            result = await db.execute(text(self.query_template), params)
            rows = result.fetchall()
            columns = result.keys()
            
            data = [dict(zip(columns, row)) for row in rows]
            
            return DataSourceResult(
                data=data,
                source_type="sql",
                query_info=f"{self.name}: {len(data)} rows"
            )
        except Exception as e:
            logger.error("sql_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=[],
                source_type="sql",
                query_info=self.name,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": "sql",
            "description": self.description,
            "params": self.params_schema,
            "query_preview": self.query_template[:200] + "..." if len(self.query_template) > 200 else self.query_template
        }


class RESTDataSource(DataSource):
    """REST API data source"""
    
    def __init__(self, name: str, url_template: str, method: str, 
                 description: str, headers: Optional[Dict[str, str]] = None):
        self.name = name
        self.url_template = url_template
        self.method = method.upper()
        self.description = description
        self.headers = headers or {}
    
    async def fetch(self, params: Dict[str, Any]) -> DataSourceResult:
        try:
            url = self.url_template
            query_params = {}
            
            for key, value in params.items():
                if f"{{{key}}}" in url:
                    url = url.replace(f"{{{key}}}", str(value))
                else:
                    query_params[key] = value
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.method == "GET":
                    response = await client.get(url, params=query_params, headers=self.headers)
                elif self.method == "POST":
                    response = await client.post(url, json=query_params, headers=self.headers)
                else:
                    raise ValueError(f"Unsupported method: {self.method}")
                
                response.raise_for_status()
                data = response.json()
            
            return DataSourceResult(
                data=data,
                source_type="rest",
                query_info=f"{self.name}: {url}"
            )
        except Exception as e:
            logger.error("rest_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=None,
                source_type="rest",
                query_info=self.name,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": "rest",
            "description": self.description,
            "method": self.method,
            "url_template": self.url_template
        }


class CurlDataSource(DataSource):
    """Execute curl commands for external data fetching"""
    
    def __init__(self, name: str, curl_template: str, description: str,
                 parse_json: bool = True):
        self.name = name
        self.curl_template = curl_template
        self.description = description
        self.parse_json = parse_json
    
    async def fetch(self, params: Dict[str, Any]) -> DataSourceResult:
        try:
            cmd = self.curl_template
            for key, value in params.items():
                cmd = cmd.replace(f"{{{key}}}", str(value))
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"curl failed: {result.stderr}")
            
            data = json.loads(result.stdout) if self.parse_json else result.stdout
            
            return DataSourceResult(
                data=data,
                source_type="curl",
                query_info=f"{self.name}: {cmd[:50]}..."
            )
        except Exception as e:
            logger.error("curl_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=None,
                source_type="curl",
                query_info=self.name,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": "curl",
            "description": self.description,
            "curl_template": self.curl_template
        }


class DataSourceRegistry:
    """Registry for all available data sources"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sources = {}
            cls._instance._initialize_default_sources()
        return cls._instance
    
    def _initialize_default_sources(self):
        """Initialize default SQL data sources for B+R documentation"""
        
        self.register(SQLDataSource(
            name="project_info",
            query_template="""
                SELECT id, name, description, start_date, end_date, 
                       status, fiscal_year, metadata
                FROM read_models.projects
                WHERE id = :project_id
                ORDER BY created_at DESC
                LIMIT 1
            """,
            description="Informacje o projektach B+R",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="expenses_summary",
            query_template="""
                SELECT 
                    e.id, e.description, e.gross_amount, e.net_amount, e.currency,
                    e.br_category as category, e.br_qualified, e.vendor_name, e.vendor_nip,
                    e.invoice_number, e.invoice_date, e.justification,
                    d.filename as document_filename, d.id as document_id
                FROM read_models.expenses e
                LEFT JOIN read_models.documents d ON e.document_id = d.id
                WHERE e.project_id = :project_id
                ORDER BY e.invoice_date ASC
            """,
            description="Zestawienie wydatków projektu",
            params_schema={
                "project_id": "UUID projektu"
            }
        ))
        
        self.register(SQLDataSource(
            name="expenses_by_category",
            query_template="""
                SELECT 
                    br_category as category,
                    COUNT(*) as count,
                    SUM(gross_amount) as total_gross,
                    SUM(net_amount) as total_net,
                    SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END) as qualified_amount
                FROM read_models.expenses
                WHERE project_id = :project_id
                GROUP BY br_category
                ORDER BY total_gross DESC
            """,
            description="Wydatki pogrupowane według kategorii",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="timesheet_summary",
            query_template="""
                SELECT 
                    w.name as worker_name, 
                    EXTRACT(YEAR FROM t.work_date) as year,
                    EXTRACT(MONTH FROM t.work_date) as month,
                    SUM(t.hours) as total_hours,
                    STRING_AGG(DISTINCT t.description, '; ') as tasks
                FROM read_models.timesheet_entries t
                JOIN read_models.workers w ON t.worker_id = w.id
                WHERE t.project_id = :project_id
                GROUP BY w.name, EXTRACT(YEAR FROM t.work_date), EXTRACT(MONTH FROM t.work_date)
                ORDER BY year, month, worker_name
            """,
            description="Zestawienie godzin pracy (miesięczne) dla projektu",
            params_schema={
                "project_id": "UUID projektu"
            }
        ))
        
        self.register(SQLDataSource(
            name="timesheet_monthly_breakdown",
            query_template="""
                SELECT 
                    EXTRACT(YEAR FROM t.work_date) as year,
                    EXTRACT(MONTH FROM t.work_date) as month,
                    w.name as worker_name,
                    SUM(t.hours) as hours,
                    COUNT(DISTINCT t.work_date) as days_worked
                FROM read_models.timesheet_entries t
                JOIN read_models.workers w ON t.worker_id = w.id
                WHERE t.project_id = :project_id
                GROUP BY EXTRACT(YEAR FROM t.work_date), EXTRACT(MONTH FROM t.work_date), w.name
                ORDER BY year, month, worker_name
            """,
            description="Rozbicie godzin pracy na miesiące i pracowników",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="revenues",
            query_template="""
                SELECT 
                    id, description, gross_amount, currency,
                    ip_box_qualified, ip_classification, invoice_date,
                    document_id, client_name, client_nip
                FROM read_models.revenues
                WHERE project_id = :project_id
                ORDER BY invoice_date ASC
            """,
            description="Przychody z projektu (IP Box)",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="workers",
            query_template="""
                SELECT 
                    w.id, w.name, w.role, w.hourly_rate, w.is_active,
                    SUM(t.hours) as total_hours
                FROM read_models.workers w
                LEFT JOIN read_models.timesheet_entries t ON t.worker_id = w.id AND t.project_id = :project_id
                WHERE w.is_active = true
                GROUP BY w.id, w.name, w.role, w.hourly_rate, w.is_active
                HAVING SUM(t.hours) > 0 OR :project_id IS NULL
            """,
            description="Pracownicy projektu",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="documents_list",
            query_template="""
                SELECT 
                    d.id, d.filename, d.document_type, d.ocr_status,
                    d.ocr_confidence, substring(d.ocr_text for 500) as ocr_excerpt,
                    d.extracted_data, d.created_at,
                    n.notes as annotation
                FROM read_models.documents d
                LEFT JOIN read_models.document_notes n ON n.document_id = d.id
                WHERE d.project_id = :project_id
                ORDER BY d.created_at DESC
            """,
            description="Lista dokumentów z adnotacjami",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="document_annotations",
            query_template="""
                SELECT 
                    d.id as document_id,
                    d.filename,
                    d.document_type,
                    substring(d.ocr_text for 1000) as ocr_text,
                    d.extracted_data,
                    n.notes as annotation,
                    n.updated_at as annotation_date
                FROM read_models.documents d
                INNER JOIN read_models.document_notes n ON n.document_id = d.id
                WHERE d.project_id = :project_id
                  AND n.notes IS NOT NULL AND n.notes != ''
                ORDER BY n.updated_at DESC
            """,
            description="Adnotacje dokumentów z kontekstem B+R",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="expenses_with_docs",
            query_template="""
                SELECT 
                    e.id, e.description, e.gross_amount, e.net_amount, e.currency,
                    e.category, e.br_qualified, e.vendor_name, e.vendor_nip,
                    e.invoice_number, e.invoice_date, e.justification,
                    d.id as document_id, d.filename as document_filename,
                    n.notes as document_annotation
                FROM read_models.expenses e
                LEFT JOIN read_models.documents d ON e.document_id = d.id
                LEFT JOIN read_models.document_notes n ON n.document_id = d.id
                WHERE e.project_id = :project_id
                  AND (:year IS NULL OR EXTRACT(YEAR FROM e.invoice_date) = :year)
                ORDER BY e.invoice_date ASC
            """,
            description="Wydatki z dokumentami i adnotacjami",
            params_schema={"project_id": "UUID projektu", "year": "Rok (opcjonalny)"}
        ))
        
        self.register(SQLDataSource(
            name="nexus_calculation",
            query_template="""
                WITH expense_categories AS (
                    SELECT 
                        SUM(CASE WHEN category IN ('personnel', 'materials', 'equipment') 
                            AND vendor_nip NOT IN (SELECT nip FROM read_models.contractors WHERE related_party = true)
                            THEN gross_amount ELSE 0 END) as a_direct,
                        SUM(CASE WHEN category = 'subcontractor' 
                            AND vendor_nip NOT IN (SELECT nip FROM read_models.contractors WHERE related_party = true)
                            THEN gross_amount ELSE 0 END) as b_unrelated,
                        SUM(CASE WHEN category = 'subcontractor' 
                            AND vendor_nip IN (SELECT nip FROM read_models.contractors WHERE related_party = true)
                            THEN gross_amount ELSE 0 END) as c_related,
                        SUM(CASE WHEN category = 'ip_purchase' THEN gross_amount ELSE 0 END) as d_ip
                    FROM read_models.expenses
                    WHERE project_id = :project_id
                      AND br_qualified = true
                      AND (:year IS NULL OR EXTRACT(YEAR FROM invoice_date) = :year)
                )
                SELECT 
                    a_direct, b_unrelated, c_related, d_ip,
                    CASE 
                        WHEN (a_direct + b_unrelated + c_related + d_ip) = 0 THEN 1
                        ELSE LEAST(1, ((a_direct + b_unrelated) * 1.3) / 
                             NULLIF(a_direct + b_unrelated + c_related + d_ip, 0))
                    END as nexus
                FROM expense_categories
            """,
            description="Obliczenie wskaźnika Nexus dla IP Box",
            params_schema={"project_id": "UUID projektu", "year": "Rok (opcjonalny)"}
        ))
        
        self.register(RESTDataSource(
            name="nbp_exchange_rate",
            url_template="https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/",
            method="GET",
            description="Kurs walut z NBP na dany dzień"
        ))
    
    def register(self, source: DataSource):
        """Register a new data source"""
        if hasattr(source, 'name'):
            self._sources[source.name] = source
    
    def get(self, name: str) -> Optional[DataSource]:
        """Get a data source by name"""
        return self._sources.get(name)
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """List all available data sources with their schemas"""
        return [source.get_schema() for source in self._sources.values()]
    
    async def fetch_multiple(self, source_configs: List[Dict[str, Any]], 
                            db: AsyncSession) -> Dict[str, DataSourceResult]:
        """Fetch data from multiple sources"""
        results = {}
        for config in source_configs:
            name = config.get("source")
            params = config.get("params", {})
            source = self.get(name)
            if source:
                if isinstance(source, SQLDataSource):
                    results[name] = await source.fetch(params, db)
                else:
                    results[name] = await source.fetch(params)
        return results


def get_data_registry() -> DataSourceRegistry:
    """Get singleton instance of data source registry"""
    return DataSourceRegistry()
