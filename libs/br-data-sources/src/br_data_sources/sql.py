"""
SQL-based data source for PostgreSQL queries.
"""
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from .base import DataSource, DataSourceResult

logger = structlog.get_logger()


class SQLDataSource(DataSource):
    """SQL-based data source for PostgreSQL queries"""
    
    def __init__(
        self,
        name: str,
        query_template: str,
        description: str = "",
        params_schema: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, description)
        self.query_template = query_template
        self.params_schema = params_schema or {}
    
    async def fetch(
        self,
        params: Dict[str, Any],
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> DataSourceResult:
        """
        Fetch data from PostgreSQL.
        
        Args:
            params: Query parameters
            db: AsyncSession for database connection
            
        Returns:
            DataSourceResult with fetched data
        """
        if db is None:
            return DataSourceResult(
                data=[],
                source_type="sql",
                source_name=self.name,
                query_info=self.name,
                error="Database session not provided"
            )
        
        try:
            result = await db.execute(text(self.query_template), params)
            rows = result.fetchall()
            columns = result.keys()
            
            data = [dict(zip(columns, row)) for row in rows]
            
            # Extract key variables for tracking
            variables = self._extract_variables(data)
            
            return DataSourceResult(
                data=data,
                source_type="sql",
                source_name=self.name,
                query_info=f"{self.name}: {len(data)} rows",
                variables=variables,
            )
        except Exception as e:
            logger.error("sql_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=[],
                source_type="sql",
                source_name=self.name,
                query_info=self.name,
                error=str(e)
            )
    
    def _extract_variables(self, data: list) -> Dict[str, Any]:
        """Extract key variables from data for tracking"""
        variables = {}
        
        if not data:
            return variables
        
        # Extract totals if present
        if len(data) == 1:
            row = data[0]
            for key in ['total_gross', 'total_net', 'nexus', 'total_hours']:
                if key in row and row[key] is not None:
                    variables[key] = row[key]
        
        # For lists, calculate aggregates
        if len(data) > 1:
            numeric_keys = ['gross_amount', 'net_amount', 'hours', 'total_hours']
            for key in numeric_keys:
                values = [row.get(key) for row in data if row.get(key) is not None]
                if values:
                    variables[f"sum_{key}"] = sum(float(v) for v in values)
                    variables[f"count_{key}"] = len(values)
        
        return variables
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema description"""
        return {
            "name": self.name,
            "type": "sql",
            "description": self.description,
            "params": self.params_schema,
            "query_preview": self.query_template[:200] + "..." 
                if len(self.query_template) > 200 else self.query_template
        }
