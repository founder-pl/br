"""
Google Drive and S3/MinIO Cloud Storage Clients
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import mimetypes

import httpx
import structlog

from .base import BaseCloudStorageClient, CloudFile, UploadResult

logger = structlog.get_logger()


class GoogleDriveClient(BaseCloudStorageClient):
    """
    Google Drive API client.
    
    Required credentials:
        - access_token: OAuth2 access token
        - refresh_token: OAuth2 refresh token
        - client_id: OAuth2 client ID
        - client_secret: OAuth2 client secret
        
    Optional settings:
        - default_folder_id: Default folder ID for uploads
    """
    
    API_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"
    
    @property
    def provider_name(self) -> str:
        return "google_drive"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
            "Content-Type": "application/json"
        }
    
    async def _refresh_token_if_needed(self):
        """Refresh access token if expired"""
        # This would be called before API requests
        # Implementation depends on token management strategy
        pass
    
    async def verify_connection(self) -> bool:
        """Verify Google Drive connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/about",
                    headers=self._get_headers(),
                    params={"fields": "user"},
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
        """List files in Google Drive folder"""
        files = []
        
        # If folder_path is "/", use root
        folder_id = self.settings.get("default_folder_id", "root")
        if folder_path != "/" and folder_path:
            # Need to resolve path to folder ID
            folder_id = await self._resolve_path_to_id(folder_path) or folder_id
        
        query = f"'{folder_id}' in parents and trashed = false"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/files",
                    headers=self._get_headers(),
                    params={
                        "q": query,
                        "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)",
                        "pageSize": 1000
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("files", []):
                        files.append(CloudFile(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            path=f"/{item.get('name', '')}",
                            size=int(item.get("size", 0)),
                            mime_type=item.get("mimeType", ""),
                            created_at=self._parse_datetime(item.get("createdTime")),
                            modified_at=self._parse_datetime(item.get("modifiedTime")),
                            is_folder=item.get("mimeType") == "application/vnd.google-apps.folder",
                            parent_id=item.get("parents", [None])[0],
                            web_url=item.get("webViewLink")
                        ))
        
        except Exception as e:
            self.logger.error("Failed to list files", error=str(e))
        
        return files
    
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload file to Google Drive"""
        try:
            with open(local_path, "rb") as f:
                content = f.read()
            
            filename = Path(local_path).name
            mime_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
            
            return await self.upload_bytes(
                content=content,
                remote_path=remote_path,
                filename=filename,
                mime_type=mime_type,
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
        """Upload bytes to Google Drive"""
        try:
            # Get or create parent folder
            parent_id = await self._ensure_folder_path(remote_path)
            
            # Check if file exists
            if overwrite:
                existing = await self._find_file_by_name(filename, parent_id)
                if existing:
                    # Update existing file
                    return await self._update_file(existing, content, mime_type)
            
            # Create new file
            metadata = {
                "name": filename,
                "parents": [parent_id]
            }
            
            async with httpx.AsyncClient() as client:
                # Multipart upload
                boundary = "boundary12345"
                
                body = (
                    f"--{boundary}\r\n"
                    f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
                    f'{json.dumps(metadata)}\r\n'
                    f"--{boundary}\r\n"
                    f"Content-Type: {mime_type}\r\n\r\n"
                ).encode() + content + f"\r\n--{boundary}--".encode()
                
                response = await client.post(
                    f"{self.UPLOAD_URL}/files",
                    params={"uploadType": "multipart"},
                    headers={
                        "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
                        "Content-Type": f"multipart/related; boundary={boundary}"
                    },
                    content=body,
                    timeout=120.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return UploadResult(
                        success=True,
                        file_id=data.get("id"),
                        file_path=f"{remote_path}/{filename}",
                        file_url=f"https://drive.google.com/file/d/{data.get('id')}/view",
                        raw_response=data
                    )
                else:
                    return UploadResult(
                        success=False,
                        error=f"Upload failed: HTTP {response.status_code} - {response.text}"
                    )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        content = await self.download_bytes(remote_path)
        if content:
            with open(local_path, "wb") as f:
                f.write(content)
            return True
        return False
    
    async def download_bytes(self, remote_path: str) -> Optional[bytes]:
        """Download file by ID or path"""
        # If it looks like an ID, use directly
        file_id = remote_path if len(remote_path) > 20 and "/" not in remote_path else None
        
        if not file_id:
            file_id = await self._resolve_path_to_id(remote_path)
        
        if not file_id:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/files/{file_id}",
                    headers=self._get_headers(),
                    params={"alt": "media"},
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Download failed", error=str(e))
        
        return None
    
    async def delete_file(self, remote_path: str) -> bool:
        file_id = await self._resolve_path_to_id(remote_path)
        if not file_id:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.API_URL}/files/{file_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                return response.status_code == 204
        except:
            return False
    
    async def create_folder(self, folder_path: str) -> bool:
        try:
            await self._ensure_folder_path(folder_path)
            return True
        except:
            return False
    
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        file_id = await self._resolve_path_to_id(remote_path)
        if not file_id:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/files/{file_id}",
                    headers=self._get_headers(),
                    params={"fields": "id,name,mimeType,size,createdTime,modifiedTime,webViewLink"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    item = response.json()
                    return CloudFile(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        path=remote_path,
                        size=int(item.get("size", 0)),
                        mime_type=item.get("mimeType", ""),
                        created_at=self._parse_datetime(item.get("createdTime")),
                        modified_at=self._parse_datetime(item.get("modifiedTime")),
                        is_folder=item.get("mimeType") == "application/vnd.google-apps.folder",
                        web_url=item.get("webViewLink")
                    )
        except:
            pass
        
        return None
    
    async def _resolve_path_to_id(self, path: str) -> Optional[str]:
        """Resolve path like /folder/subfolder/file to Google Drive ID"""
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return "root"
        
        current_id = "root"
        
        for part in parts:
            found = await self._find_file_by_name(part, current_id)
            if found:
                current_id = found
            else:
                return None
        
        return current_id
    
    async def _find_file_by_name(self, name: str, parent_id: str) -> Optional[str]:
        """Find file ID by name in parent folder"""
        query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/files",
                    headers=self._get_headers(),
                    params={"q": query, "fields": "files(id)"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    files = response.json().get("files", [])
                    if files:
                        return files[0].get("id")
        except:
            pass
        
        return None
    
    async def _ensure_folder_path(self, path: str) -> str:
        """Ensure folder path exists, create if needed, return final folder ID"""
        parts = [p for p in path.strip("/").split("/") if p]
        
        current_id = "root"
        
        for part in parts:
            existing = await self._find_file_by_name(part, current_id)
            if existing:
                current_id = existing
            else:
                # Create folder
                current_id = await self._create_folder(part, current_id)
        
        return current_id
    
    async def _create_folder(self, name: str, parent_id: str) -> str:
        """Create a folder and return its ID"""
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/files",
                headers=self._get_headers(),
                json=metadata,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                return response.json().get("id")
        
        raise Exception(f"Failed to create folder: {name}")
    
    async def _update_file(self, file_id: str, content: bytes, mime_type: str) -> UploadResult:
        """Update existing file content"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.UPLOAD_URL}/files/{file_id}",
                    params={"uploadType": "media"},
                    headers={
                        "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
                        "Content-Type": mime_type
                    },
                    content=content,
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return UploadResult(
                        success=True,
                        file_id=file_id,
                        file_url=f"https://drive.google.com/file/d/{file_id}/view",
                        raw_response=data
                    )
        except Exception as e:
            return UploadResult(success=False, error=str(e))
        
        return UploadResult(success=False, error="Update failed")
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return None


class S3Client(BaseCloudStorageClient):
    """
    AWS S3 / MinIO compatible client.
    
    Required credentials:
        - access_key_id: AWS access key ID
        - secret_access_key: AWS secret access key
        - bucket: S3 bucket name
        
    Optional settings:
        - endpoint_url: Custom endpoint for MinIO/S3-compatible storage
        - region: AWS region (default: us-east-1)
    """
    
    @property
    def provider_name(self) -> str:
        return "aws_s3" if not self.settings.get("endpoint_url") else "minio"
    
    def _get_client(self):
        """Get boto3 S3 client"""
        import boto3
        
        kwargs = {
            "aws_access_key_id": self.credentials.get("access_key_id"),
            "aws_secret_access_key": self.credentials.get("secret_access_key"),
            "region_name": self.settings.get("region", "us-east-1"),
        }
        
        if self.settings.get("endpoint_url"):
            kwargs["endpoint_url"] = self.settings["endpoint_url"]
        
        return boto3.client("s3", **kwargs)
    
    async def verify_connection(self) -> bool:
        """Verify S3 connection"""
        try:
            client = self._get_client()
            client.head_bucket(Bucket=self.credentials.get("bucket"))
            return True
        except Exception as e:
            self.logger.error("Connection verification failed", error=str(e))
            return False
    
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in S3 bucket"""
        files = []
        prefix = folder_path.strip("/") + "/" if folder_path != "/" else ""
        
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            
            kwargs = {"Bucket": bucket, "Prefix": prefix}
            if not recursive:
                kwargs["Delimiter"] = "/"
            
            response = client.list_objects_v2(**kwargs)
            
            # Files
            for obj in response.get("Contents", []):
                files.append(CloudFile(
                    id=obj["Key"],
                    name=obj["Key"].split("/")[-1],
                    path=f"/{obj['Key']}",
                    size=obj["Size"],
                    mime_type="",
                    modified_at=obj.get("LastModified"),
                    is_folder=False
                ))
            
            # Folders (common prefixes)
            for prefix_obj in response.get("CommonPrefixes", []):
                files.append(CloudFile(
                    id=prefix_obj["Prefix"],
                    name=prefix_obj["Prefix"].rstrip("/").split("/")[-1],
                    path=f"/{prefix_obj['Prefix']}",
                    size=0,
                    mime_type="",
                    is_folder=True
                ))
        
        except Exception as e:
            self.logger.error("Failed to list files", error=str(e))
        
        return files
    
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        overwrite: bool = True
    ) -> UploadResult:
        """Upload file to S3"""
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            
            key = remote_path.strip("/")
            if not key.endswith(Path(local_path).name):
                key = f"{key}/{Path(local_path).name}"
            
            client.upload_file(local_path, bucket, key)
            
            return UploadResult(
                success=True,
                file_id=key,
                file_path=f"/{key}",
                file_url=f"s3://{bucket}/{key}"
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
        """Upload bytes to S3"""
        try:
            from io import BytesIO
            
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            
            key = f"{remote_path.strip('/')}/{filename}"
            
            client.upload_fileobj(
                BytesIO(content),
                bucket,
                key,
                ExtraArgs={"ContentType": mime_type}
            )
            
            return UploadResult(
                success=True,
                file_id=key,
                file_path=f"/{key}",
                file_url=f"s3://{bucket}/{key}"
            )
        
        except Exception as e:
            return UploadResult(success=False, error=str(e))
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            key = remote_path.strip("/")
            
            client.download_file(bucket, key, local_path)
            return True
        except:
            return False
    
    async def download_bytes(self, remote_path: str) -> Optional[bytes]:
        try:
            from io import BytesIO
            
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            key = remote_path.strip("/")
            
            buffer = BytesIO()
            client.download_fileobj(bucket, key, buffer)
            return buffer.getvalue()
        except:
            return None
    
    async def delete_file(self, remote_path: str) -> bool:
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            key = remote_path.strip("/")
            
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except:
            return False
    
    async def create_folder(self, folder_path: str) -> bool:
        """S3 doesn't have real folders, but we can create a placeholder"""
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            key = folder_path.strip("/") + "/"
            
            client.put_object(Bucket=bucket, Key=key, Body=b"")
            return True
        except:
            return False
    
    async def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        try:
            client = self._get_client()
            bucket = self.credentials.get("bucket")
            key = remote_path.strip("/")
            
            response = client.head_object(Bucket=bucket, Key=key)
            
            return CloudFile(
                id=key,
                name=key.split("/")[-1],
                path=f"/{key}",
                size=response.get("ContentLength", 0),
                mime_type=response.get("ContentType", ""),
                modified_at=response.get("LastModified"),
                is_folder=False
            )
        except:
            return None
