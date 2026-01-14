"""
REST API data source.
"""
from typing import Any, Dict, Optional
import httpx
import structlog

from .base import DataSource, DataSourceResult

logger = structlog.get_logger()


class RESTDataSource(DataSource):
    """REST API data source"""
    
    def __init__(
        self,
        name: str,
        url_template: str,
        method: str = "GET",
        description: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        super().__init__(name, description)
        self.url_template = url_template
        self.method = method.upper()
        self.headers = headers or {}
        self.timeout = timeout
    
    async def fetch(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> DataSourceResult:
        """
        Fetch data from REST API.
        
        Args:
            params: URL parameters and body data
            
        Returns:
            DataSourceResult with fetched data
        """
        try:
            url = self.url_template
            query_params = {}
            
            # Replace path parameters
            for key, value in params.items():
                if f"{{{key}}}" in url:
                    url = url.replace(f"{{{key}}}", str(value))
                else:
                    query_params[key] = value
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "GET":
                    response = await client.get(
                        url, 
                        params=query_params, 
                        headers=self.headers
                    )
                elif self.method == "POST":
                    response = await client.post(
                        url, 
                        json=query_params, 
                        headers=self.headers
                    )
                else:
                    raise ValueError(f"Unsupported method: {self.method}")
                
                response.raise_for_status()
                data = response.json()
            
            return DataSourceResult(
                data=data,
                source_type="rest",
                source_name=self.name,
                query_info=f"{self.name}: {url}",
            )
        except Exception as e:
            logger.error("rest_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=None,
                source_type="rest",
                source_name=self.name,
                query_info=self.name,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema description"""
        return {
            "name": self.name,
            "type": "rest",
            "description": self.description,
            "method": self.method,
            "url_template": self.url_template
        }
    
    def get_api_url(self, params: Dict[str, Any], base_url: str = "") -> str:
        """Get actual API URL with parameters"""
        url = self.url_template
        for key, value in params.items():
            url = url.replace(f"{{{key}}}", str(value))
        return url
