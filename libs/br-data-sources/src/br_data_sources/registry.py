"""
Data source registry with default B+R sources.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .base import DataSource, DataSourceResult
from .sql import SQLDataSource
from .rest import RESTDataSource


class DataSourceRegistry:
    """Registry for all available data sources"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sources: Dict[str, DataSource] = {}
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
                    e.id, e.invoice_number as description, e.gross_amount, e.net_amount, e.currency,
                    e.br_category as category, e.br_qualified, e.vendor_name, e.vendor_nip,
                    e.invoice_number, e.invoice_date, e.br_qualification_reason as justification,
                    d.filename as document_filename, d.id as document_id
                FROM read_models.expenses e
                LEFT JOIN read_models.documents d ON e.document_id = d.id
                WHERE e.project_id = :project_id
                ORDER BY e.invoice_date ASC
            """,
            description="Zestawienie wydatków projektu",
            params_schema={"project_id": "UUID projektu"}
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
                    COUNT(DISTINCT t.work_date) as days_worked
                FROM read_models.timesheet_entries t
                JOIN read_models.workers w ON t.worker_id = w.id
                WHERE t.project_id = :project_id
                GROUP BY w.name, EXTRACT(YEAR FROM t.work_date), EXTRACT(MONTH FROM t.work_date)
                ORDER BY year, month, worker_name
            """,
            description="Zestawienie godzin pracy",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="nexus_calculation",
            query_template="""
                WITH expense_categories AS (
                    SELECT 
                        SUM(CASE WHEN br_category IN ('personnel_employment', 'personnel_civil', 'materials', 'equipment') 
                            THEN gross_amount ELSE 0 END) as a_direct,
                        SUM(CASE WHEN br_category = 'external_services'
                            THEN gross_amount ELSE 0 END) as b_unrelated,
                        SUM(0) as c_related,
                        SUM(CASE WHEN br_category = 'ip_purchase' THEN gross_amount ELSE 0 END) as d_ip
                    FROM read_models.expenses
                    WHERE project_id = :project_id
                      AND br_qualified = true
                )
                SELECT 
                    COALESCE(a_direct, 0) as a_direct, 
                    COALESCE(b_unrelated, 0) as b_unrelated, 
                    COALESCE(c_related, 0) as c_related, 
                    COALESCE(d_ip, 0) as d_ip,
                    CASE 
                        WHEN COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0) = 0 THEN 1
                        ELSE LEAST(1, ((COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0)) * 1.3) / 
                             NULLIF(COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0), 0))
                    END as nexus
                FROM expense_categories
            """,
            description="Obliczenie wskaźnika Nexus dla IP Box",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(SQLDataSource(
            name="revenues",
            query_template="""
                SELECT 
                    id, ip_description as description, gross_amount, currency,
                    ip_qualified, ip_type, invoice_date,
                    document_id, client_name, client_nip, invoice_number
                FROM read_models.revenues
                WHERE project_id = :project_id
                ORDER BY invoice_date ASC
            """,
            description="Przychody z projektu (IP Box)",
            params_schema={"project_id": "UUID projektu"}
        ))
        
        self.register(RESTDataSource(
            name="nbp_exchange_rate",
            url_template="https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/",
            method="GET",
            description="Kurs walut z NBP na dany dzień"
        ))
    
    def register(self, source: DataSource):
        """Register a new data source"""
        self._sources[source.name] = source
    
    def get(self, name: str) -> Optional[DataSource]:
        """Get a data source by name"""
        return self._sources.get(name)
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """List all available data sources with their schemas"""
        return [source.get_schema() for source in self._sources.values()]
    
    async def fetch(
        self,
        source_name: str,
        params: Dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> DataSourceResult:
        """Fetch data from a single source"""
        source = self.get(source_name)
        if not source:
            return DataSourceResult(
                data=None,
                source_type="unknown",
                source_name=source_name,
                query_info=source_name,
                error=f"Source not found: {source_name}"
            )
        
        if isinstance(source, SQLDataSource):
            return await source.fetch(params, db=db)
        return await source.fetch(params)
    
    async def fetch_multiple(
        self,
        source_configs: List[Dict[str, Any]],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, DataSourceResult]:
        """Fetch data from multiple sources"""
        results = {}
        for config in source_configs:
            name = config.get("source")
            params = config.get("params", {})
            results[name] = await self.fetch(name, params, db)
        return results


_registry_instance: Optional[DataSourceRegistry] = None


def get_data_registry() -> DataSourceRegistry:
    """Get singleton instance of data source registry"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DataSourceRegistry()
    return _registry_instance
