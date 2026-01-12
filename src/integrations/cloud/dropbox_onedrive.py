"""
Dropbox and OneDrive Cloud Storage Clients
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import httpx
import structlog

from .base import BaseCloudStorageClient, CloudFile, UploadResult

logger = structlog.get_logger()


class DropboxClient(BaseCloudStorageClient):
    """
    Dropbox API client.
    
    Required credentials:
        - access_token: Dropbox OAuth2 access token
        - refresh_token: OAuth2 refresh token (optional)
        - app_key: Dropbox app key (for token refresh)
        - app_secret: Dropbox app secret (for token refresh)
    """
    
    API_URL = "https://api.dropboxapi.com/2"
    CONTENT_URL = "https://content.dropboxapi.com/2"
    
    @property
    def provider_name(self) -> str:
        return "dropbox"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
            "Content-Type": "application/json"
        }
    
    async def verify_connection(self) -> bool:
        """Verify Dropbox connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/users/get_current_account",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error("Connection verification failed", error=str(e))
            return False
    
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in Dropbox folder"""
        files = []
        path = "" if folder_path == "/" else folder_path
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/files/list_folder",
                    headers=self._get_headers(),
                    json={
                        "path": path,
                        "recursive": recursive,
                        "include_deleted": False,
                        "include_has_explicit_shared_members": False,
                        "include_mounted_folders": True
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for entry in data.get("entries", []):
                        is_folder = entry.get(".tag") == "folder"
                        
                        files.append(CloudFile(
                            id=entry.get("id", ""),
                            name=entry.get("name", ""),
                            path=entry.get("path_display", ""),
                            size=entry.get("size", 0) if not is_folder else 0,
                            mime_type="",
                            modified_at=self._parse_datetime(entry.get("server_modified")),
                            is_folder=is_folder
                        ))
        
        except Exception as e:
            self.logger.error("Failed to list files", folder=folder_path, error=str(e))
        
        return files
    
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload file to Dropbox"""
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
        """Upload bytes to Dropbox"""
        import json
        
        # Build full path
        if remote_path.endswith("/"):
            full_path = f"{remote_path}{filename}"
        else:
            full_path = f"{remote_path}/{filename}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.CONTENT_URL}/files/upload",
                    headers={
                        "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
                        "Content-Type": "application/octet-stream",
                        "Dropbox-API-Arg": json.dumps({
                            "path": full_path,
                            "mode": "overwrite" if overwrite else "add",
                            "autorename": not overwrite,
                            "mute": False
                        })
                    },
                    content=content,
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return UploadResult(
                        success=True,
                        file_id=data.get("id"),
                        file_path=data.get("path_display"),
                        raw_response=data
                    )
                else:
                    return UploadResult(
                        success=False,
                        error=f"Upload failed: HTTP {response.status_code}"
                    )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from Dropbox"""
        content = await self.download_bytes(remote_path)
        if content:
            with open(local_path, "wb") as f:
                f.write(content)
            return True
        return False
    
    async def download_bytes(self, remote_path: str) -> Optional[bytes]:
        """Download file content as bytes"""
        import json
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.CONTENT_URL}/files/download",
                    headers={
                        "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
                        "Dropbox-API-Arg": json.dumps({"path": remote_path})
                    },
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Download failed", path=remote_path, error=str(e))
        
        return None
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from Dropbox"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/files/delete_v2",
                    headers=self._get_headers(),
                    json={"path": remote_path},
                    timeout=30.0
                )
                return response.status_code == 200
        except:
            return False
    
    async def create_folder(self, folder_path: str) -> bool:
        """Create folder in Dropbox"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/files/create_folder_v2",
                    headers=self._get_headers(),
                    json={"path": folder_path, "autorename": False},
                    timeout=30.0
                )
                return response.status_code in [200, 409]  # 409 = already exists
        except:
            return False
    
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get file metadata"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/files/get_metadata",
                    headers=self._get_headers(),
                    json={"path": remote_path},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    entry = response.json()
                    is_folder = entry.get(".tag") == "folder"
                    
                    return CloudFile(
                        id=entry.get("id", ""),
                        name=entry.get("name", ""),
                        path=entry.get("path_display", ""),
                        size=entry.get("size", 0) if not is_folder else 0,
                        mime_type="",
                        modified_at=self._parse_datetime(entry.get("server_modified")),
                        is_folder=is_folder
                    )
        except:
            pass
        
        return None
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return None


class OneDriveClient(BaseCloudStorageClient):
    """
    Microsoft OneDrive API client.
    
    Required credentials:
        - access_token: Microsoft OAuth2 access token
        - refresh_token: OAuth2 refresh token
        - client_id: Azure AD application client ID
        - client_secret: Azure AD application client secret
        
    Optional settings:
        - drive_id: Specific drive ID (default: user's default drive)
    """
    
    API_URL = "https://graph.microsoft.com/v1.0"
    
    @property
    def provider_name(self) -> str:
        return "onedrive"
    
    @property
    def drive_path(self) -> str:
        drive_id = self.settings.get("drive_id")
        if drive_id:
            return f"/drives/{drive_id}"
        return "/me/drive"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
            "Content-Type": "application/json"
        }
    
    async def verify_connection(self) -> bool:
        """Verify OneDrive connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}{self.drive_path}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error("Connection verification failed", error=str(e))
            return False
    
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in OneDrive folder"""
        files = []
        
        # Build URL
        if folder_path == "/" or not folder_path:
            url = f"{self.API_URL}{self.drive_path}/root/children"
        else:
            url = f"{self.API_URL}{self.drive_path}/root:{folder_path}:/children"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("value", []):
                        is_folder = "folder" in item
                        
                        files.append(CloudFile(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            path=item.get("parentReference", {}).get("path", "") + "/" + item.get("name", ""),
                            size=item.get("size", 0),
                            mime_type=item.get("file", {}).get("mimeType", ""),
                            created_at=self._parse_datetime(item.get("createdDateTime")),
                            modified_at=self._parse_datetime(item.get("lastModifiedDateTime")),
                            is_folder=is_folder,
                            web_url=item.get("webUrl")
                        ))
        
        except Exception as e:
            self.logger.error("Failed to list files", folder=folder_path, error=str(e))
        
        return files
    
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload file to OneDrive"""
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
        """Upload bytes to OneDrive"""
        # Build path
        if remote_path.endswith("/"):
            full_path = f"{remote_path}{filename}"
        else:
            full_path = f"{remote_path}/{filename}"
        
        # For files <= 4MB use simple upload
        if len(content) <= 4 * 1024 * 1024:
            return await self._simple_upload(full_path, content, overwrite)
        else:
            # For larger files, would need to implement chunked upload
            return UploadResult(success=False, error="File too large, chunked upload not implemented")
    
    async def _simple_upload(
        self,
        path: str,
        content: bytes,
        overwrite: bool
    ) -> UploadResult:
        """Simple upload for files <= 4MB"""
        conflict_behavior = "replace" if overwrite else "rename"
        
        url = f"{self.API_URL}{self.drive_path}/root:{path}:/content?@microsoft.graph.conflictBehavior={conflict_behavior}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
                        "Content-Type": "application/octet-stream"
                    },
                    content=content,
                    timeout=120.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return UploadResult(
                        success=True,
                        file_id=data.get("id"),
                        file_path=path,
                        file_url=data.get("webUrl"),
                        raw_response=data
                    )
                else:
                    return UploadResult(
                        success=False,
                        error=f"Upload failed: HTTP {response.status_code}"
                    )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from OneDrive"""
        content = await self.download_bytes(remote_path)
        if content:
            with open(local_path, "wb") as f:
                f.write(content)
            return True
        return False
    
    async def download_bytes(self, remote_path: str) -> Optional[bytes]:
        """Download file content as bytes"""
        url = f"{self.API_URL}{self.drive_path}/root:{remote_path}:/content"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    follow_redirects=True,
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Download failed", path=remote_path, error=str(e))
        
        return None
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from OneDrive"""
        url = f"{self.API_URL}{self.drive_path}/root:{remote_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                return response.status_code == 204
        except:
            return False
    
    async def create_folder(self, folder_path: str) -> bool:
        """Create folder in OneDrive"""
        # Extract parent path and folder name
        parts = folder_path.rstrip("/").rsplit("/", 1)
        if len(parts) == 2:
            parent_path = parts[0] or "/"
            folder_name = parts[1]
        else:
            parent_path = "/"
            folder_name = parts[0]
        
        # Build URL
        if parent_path == "/":
            url = f"{self.API_URL}{self.drive_path}/root/children"
        else:
            url = f"{self.API_URL}{self.drive_path}/root:{parent_path}:/children"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={
                        "name": folder_name,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": "fail"
                    },
                    timeout=30.0
                )
                return response.status_code in [201, 409]  # 409 = already exists
        except:
            return False
    
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get file metadata"""
        url = f"{self.API_URL}{self.drive_path}/root:{remote_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    item = response.json()
                    is_folder = "folder" in item
                    
                    return CloudFile(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        path=remote_path,
                        size=item.get("size", 0),
                        mime_type=item.get("file", {}).get("mimeType", ""),
                        created_at=self._parse_datetime(item.get("createdDateTime")),
                        modified_at=self._parse_datetime(item.get("lastModifiedDateTime")),
                        is_folder=is_folder,
                        web_url=item.get("webUrl")
                    )
        except:
            pass
        
        return None
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return None
