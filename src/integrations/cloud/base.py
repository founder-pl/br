"""
Base Cloud Storage Client - Abstract interface for cloud storage integrations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class CloudFile:
    """Cloud file metadata"""
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    
    is_folder: bool = False
    parent_id: Optional[str] = None
    
    download_url: Optional[str] = None
    web_url: Optional[str] = None
    
    checksum: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class UploadResult:
    """Upload operation result"""
    success: bool
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class BaseCloudStorageClient(ABC):
    """
    Abstract base class for cloud storage integrations.
    Implement this for each cloud provider.
    """
    
    def __init__(self, credentials: Dict[str, Any], settings: Dict[str, Any] = None):
        """
        Initialize cloud storage client.
        
        Args:
            credentials: API keys, tokens, OAuth credentials
            settings: Additional settings (default folder, etc.)
        """
        self.credentials = credentials
        self.settings = settings or {}
        self.logger = structlog.get_logger().bind(provider=self.provider_name)
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name identifier"""
        pass
    
    @abstractmethod
    async def verify_connection(self) -> bool:
        """Verify connection is working"""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in a folder"""
        pass
    
    @abstractmethod
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload a file to cloud storage"""
        pass
    
    @abstractmethod
    async def upload_bytes(
        self,
        content: bytes,
        remote_path: str,
        filename: str,
        mime_type: str = "application/octet-stream",
        overwrite: bool = True
    ) -> UploadResult:
        """Upload bytes directly to cloud storage"""
        pass
    
    @abstractmethod
    async def download_file(
        self,
        remote_path: str,
        local_path: str
    ) -> bool:
        """Download a file from cloud storage"""
        pass
    
    @abstractmethod
    async def download_bytes(
        self,
        remote_path: str
    ) -> Optional[bytes]:
        """Download file content as bytes"""
        pass
    
    @abstractmethod
    async def delete_file(self, remote_path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def create_folder(self, folder_path: str) -> bool:
        """Create a folder"""
        pass
    
    @abstractmethod
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get file metadata"""
        pass
    
    async def file_exists(self, remote_path: str) -> bool:
        """Check if file exists"""
        info = await self.get_file_info(remote_path)
        return info is not None
    
    async def ensure_folder_exists(self, folder_path: str) -> bool:
        """Create folder if it doesn't exist"""
        if await self.file_exists(folder_path):
            return True
        return await self.create_folder(folder_path)
    
    async def upload_report(
        self,
        report_content: bytes,
        report_name: str,
        report_folder: str = "/BR-Reports",
        year: int = None,
        month: int = None
    ) -> UploadResult:
        """
        Upload B+R report to cloud storage with organized structure.
        
        Folder structure:
        /BR-Reports/
            /2025/
                /01/
                    raport-br-2025-01.pdf
                /02/
                    raport-br-2025-02.pdf
        """
        from datetime import datetime
        
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        # Build path
        folder_path = f"{report_folder}/{year}/{month:02d}"
        
        # Ensure folder exists
        await self.ensure_folder_exists(report_folder)
        await self.ensure_folder_exists(f"{report_folder}/{year}")
        await self.ensure_folder_exists(folder_path)
        
        # Upload report
        remote_path = f"{folder_path}/{report_name}"
        
        # Determine mime type from filename
        if report_name.endswith(".pdf"):
            mime_type = "application/pdf"
        elif report_name.endswith(".xlsx"):
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif report_name.endswith(".json"):
            mime_type = "application/json"
        else:
            mime_type = "application/octet-stream"
        
        result = await self.upload_bytes(
            content=report_content,
            remote_path=folder_path,
            filename=report_name,
            mime_type=mime_type
        )
        
        if result.success:
            self.logger.info(
                "Report uploaded to cloud",
                provider=self.provider_name,
                path=remote_path
            )
        else:
            self.logger.error(
                "Report upload failed",
                provider=self.provider_name,
                error=result.error
            )
        
        return result
    
    async def sync_invoices_folder(
        self,
        local_folder: str,
        remote_folder: str = "/BR-Invoices"
    ) -> Dict[str, Any]:
        """
        Sync local invoices folder to cloud.
        
        Returns:
            Dict with sync results
        """
        results = {
            "uploaded": 0,
            "skipped": 0,
            "errors": []
        }
        
        local_path = Path(local_folder)
        if not local_path.exists():
            results["errors"].append(f"Local folder not found: {local_folder}")
            return results
        
        # Ensure remote folder exists
        await self.ensure_folder_exists(remote_folder)
        
        # Upload files
        for file_path in local_path.glob("**/*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path)
                remote_path = f"{remote_folder}/{relative_path}"
                
                try:
                    # Check if exists
                    if await self.file_exists(remote_path):
                        results["skipped"] += 1
                        continue
                    
                    # Upload
                    result = await self.upload_file(
                        local_path=str(file_path),
                        remote_path=remote_path
                    )
                    
                    if result.success:
                        results["uploaded"] += 1
                    else:
                        results["errors"].append({
                            "file": str(relative_path),
                            "error": result.error
                        })
                
                except Exception as e:
                    results["errors"].append({
                        "file": str(relative_path),
                        "error": str(e)
                    })
        
        return results
