"""
cURL-based data source for external commands.
"""
import asyncio
import json
from typing import Any, Dict
import structlog

from .base import DataSource, DataSourceResult

logger = structlog.get_logger()


class CurlDataSource(DataSource):
    """Execute curl commands for external data fetching"""
    
    def __init__(
        self,
        name: str,
        curl_template: str,
        description: str = "",
        parse_json: bool = True,
        timeout: float = 30.0,
    ):
        super().__init__(name, description)
        self.curl_template = curl_template
        self.parse_json = parse_json
        self.timeout = timeout
    
    async def fetch(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> DataSourceResult:
        """
        Fetch data by executing curl command.
        
        Args:
            params: Template parameters
            
        Returns:
            DataSourceResult with fetched data
        """
        try:
            cmd = self.curl_template
            for key, value in params.items():
                cmd = cmd.replace(f"{{{key}}}", str(value))
            
            # Run curl asynchronously
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"curl timeout after {self.timeout}s")
            
            if process.returncode != 0:
                raise Exception(f"curl failed: {stderr.decode()}")
            
            output = stdout.decode()
            data = json.loads(output) if self.parse_json else output
            
            return DataSourceResult(
                data=data,
                source_type="curl",
                source_name=self.name,
                query_info=f"{self.name}: {cmd[:50]}...",
            )
        except Exception as e:
            logger.error("curl_source_error", name=self.name, error=str(e))
            return DataSourceResult(
                data=None,
                source_type="curl",
                source_name=self.name,
                query_info=self.name,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema description"""
        return {
            "name": self.name,
            "type": "curl",
            "description": self.description,
            "curl_template": self.curl_template
        }
