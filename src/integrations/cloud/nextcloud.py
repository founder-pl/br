"""
Nextcloud WebDAV Client
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx
import structlog

from .base import BaseCloudStorageClient, CloudFile, UploadResult

logger = structlog.get_logger()


class NextcloudClient(BaseCloudStorageClient):
    """
    Nextcloud client using WebDAV protocol.
    
    Required credentials:
        - url: Nextcloud server URL (e.g., https://cloud.example.com)
        - username: Nextcloud username
        - password: Nextcloud password or app password
        
    Optional settings:
        - default_folder: Default upload folder
    """
    
    @property
    def provider_name(self) -> str:
        return "nextcloud"
    
    @property
    def webdav_url(self) -> str:
        base_url = self.credentials.get("url", "").rstrip("/")
        username = self.credentials.get("username", "")
        return f"{base_url}/remote.php/dav/files/{username}"
    
    def _get_auth(self) -> tuple:
        return (
            self.credentials.get("username", ""),
            self.credentials.get("password", "")
        )
    
    async def verify_connection(self) -> bool:
        """Verify Nextcloud connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "PROPFIND",
                    self.webdav_url,
                    auth=self._get_auth(),
                    headers={"Depth": "0"},
                    timeout=30.0
                )
                return response.status_code in [200, 207]
        except Exception as e:
            self.logger.error("Connection verification failed", error=str(e))
            return False
    
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files using PROPFIND"""
        files = []
        
        url = f"{self.webdav_url}{folder_path}".rstrip("/")
        
        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
            <d:prop>
                <d:resourcetype/>
                <d:getcontentlength/>
                <d:getcontenttype/>
                <d:getlastmodified/>
                <oc:fileid/>
            </d:prop>
        </d:propfind>"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "PROPFIND",
                    url,
                    auth=self._get_auth(),
                    headers={
                        "Depth": "infinity" if recursive else "1",
                        "Content-Type": "application/xml"
                    },
                    content=propfind_body,
                    timeout=60.0
                )
                
                if response.status_code == 207:
                    files = self._parse_propfind_response(response.text, folder_path)
        
        except Exception as e:
            self.logger.error("Failed to list files", folder=folder_path, error=str(e))
        
        return files
    
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload file to Nextcloud"""
        try:
            with open(local_path, "rb") as f:
                content = f.read()
            
            filename = Path(local_path).name
            return await self.upload_bytes(
                content=content,
                remote_path=remote_path,
                filename=filename,
                overwrite=overwrite
            )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def upload_bytes(
        self,
        content: bytes,
        remote_path: str,
        filename: str,
        mime_type: str = "application/octet-stream",
        overwrite: bool = True
    ) -> UploadResult:
        """Upload bytes to Nextcloud"""
        # Build full path
        if remote_path.endswith("/"):
            full_path = f"{remote_path}{filename}"
        else:
            full_path = f"{remote_path}/{filename}"
        
        url = f"{self.webdav_url}{full_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    auth=self._get_auth(),
                    content=content,
                    headers={"Content-Type": mime_type},
                    timeout=120.0
                )
                
                if response.status_code in [200, 201, 204]:
                    # Get file info
                    file_info = await self.get_file_info(full_path)
                    
                    return UploadResult(
                        success=True,
                        file_id=file_info.id if file_info else None,
                        file_path=full_path,
                        file_url=f"{self.credentials.get('url')}/index.php/f/{file_info.id}" if file_info else None
                    )
                else:
                    return UploadResult(
                        success=False,
                        error=f"Upload failed: HTTP {response.status_code}"
                    )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def download_file(
        self,
        remote_path: str,
        local_path: str
    ) -> bool:
        """Download file from Nextcloud"""
        content = await self.download_bytes(remote_path)
        if content:
            with open(local_path, "wb") as f:
                f.write(content)
            return True
        return False
    
    async def download_bytes(
        self,
        remote_path: str
    ) -> Optional[bytes]:
        """Download file content as bytes"""
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=self._get_auth(),
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Download failed", path=remote_path, error=str(e))
        
        return None
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from Nextcloud"""
        url = f"{self.webdav_url}{remote_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    auth=self._get_auth(),
                    timeout=30.0
                )
                return response.status_code in [200, 204]
        
        except Exception as e:
            self.logger.error("Delete failed", path=remote_path, error=str(e))
            return False
    
    async def create_folder(self, folder_path: str) -> bool:
        """Create folder in Nextcloud"""
        url = f"{self.webdav_url}{folder_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "MKCOL",
                    url,
                    auth=self._get_auth(),
                    timeout=30.0
                )
                return response.status_code in [200, 201, 405]  # 405 = already exists
        
        except Exception as e:
            self.logger.error("Create folder failed", path=folder_path, error=str(e))
            return False
    
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get file metadata"""
        url = f"{self.webdav_url}{remote_path}"
        
        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
            <d:prop>
                <d:resourcetype/>
                <d:getcontentlength/>
                <d:getcontenttype/>
                <d:getlastmodified/>
                <oc:fileid/>
            </d:prop>
        </d:propfind>"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "PROPFIND",
                    url,
                    auth=self._get_auth(),
                    headers={"Depth": "0", "Content-Type": "application/xml"},
                    content=propfind_body,
                    timeout=30.0
                )
                
                if response.status_code == 207:
                    files = self._parse_propfind_response(response.text, remote_path)
                    if files:
                        return files[0]
        
        except Exception as e:
            self.logger.error("Get file info failed", path=remote_path, error=str(e))
        
        return None
    
    def _parse_propfind_response(self, xml_text: str, base_path: str) -> List[CloudFile]:
        """Parse WebDAV PROPFIND response"""
        files = []
        
        try:
            # Parse XML
            root = ET.fromstring(xml_text)
            
            # Namespaces
            ns = {
                "d": "DAV:",
                "oc": "http://owncloud.org/ns"
            }
            
            for response in root.findall(".//d:response", ns):
                href = response.find("d:href", ns)
                if href is None:
                    continue
                
                path = href.text
                
                # Get properties
                propstat = response.find("d:propstat", ns)
                if propstat is None:
                    continue
                
                prop = propstat.find("d:prop", ns)
                if prop is None:
                    continue
                
                # Check if folder
                resourcetype = prop.find("d:resourcetype", ns)
                is_folder = resourcetype is not None and resourcetype.find("d:collection", ns) is not None
                
                # Get other properties
                size_elem = prop.find("d:getcontentlength", ns)
                size = int(size_elem.text) if size_elem is not None and size_elem.text else 0
                
                mime_elem = prop.find("d:getcontenttype", ns)
                mime_type = mime_elem.text if mime_elem is not None else ""
                
                modified_elem = prop.find("d:getlastmodified", ns)
                modified_at = None
                if modified_elem is not None and modified_elem.text:
                    try:
                        from email.utils import parsedate_to_datetime
                        modified_at = parsedate_to_datetime(modified_elem.text)
                    except:
                        pass
                
                fileid_elem = prop.find("oc:fileid", ns)
                file_id = fileid_elem.text if fileid_elem is not None else ""
                
                # Extract filename from path
                name = path.rstrip("/").split("/")[-1]
                
                files.append(CloudFile(
                    id=file_id,
                    name=name,
                    path=path,
                    size=size,
                    mime_type=mime_type,
                    modified_at=modified_at,
                    is_folder=is_folder
                ))
        
        except Exception as e:
            self.logger.error("Failed to parse PROPFIND response", error=str(e))
        
        return files
