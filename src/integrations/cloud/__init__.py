"""Cloud Storage Integration Clients"""
from .base import (
    BaseCloudStorageClient,
    CloudFile,
    UploadResult
)
from .nextcloud import NextcloudClient
from .google_s3 import GoogleDriveClient, S3Client
from .dropbox_onedrive import DropboxClient, OneDriveClient

__all__ = [
    'BaseCloudStorageClient',
    'CloudFile',
    'UploadResult',
    'NextcloudClient',
    'GoogleDriveClient',
    'S3Client',
    'DropboxClient',
    'OneDriveClient',
]
