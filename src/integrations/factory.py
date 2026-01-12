"""
Integration Client Factory - Creates appropriate clients based on provider
"""
from typing import Dict, Any, Optional, Union

from .config.database import (
    ConfigDatabase, IntegrationProvider, IntegrationType, 
    get_config_db
)
from .accounting.base import BaseAccountingClient
from .accounting.ifirma import IFirmaClient
from .accounting.fakturownia import FakturowniaClient
from .accounting.wfirma_infakt import WFirmaClient, InFaktClient
from .cloud.base import BaseCloudStorageClient
from .cloud.nextcloud import NextcloudClient
from .cloud.google_s3 import GoogleDriveClient, S3Client
from .cloud.dropbox_onedrive import DropboxClient, OneDriveClient

import structlog

logger = structlog.get_logger()


# Accounting client mapping
ACCOUNTING_CLIENTS = {
    IntegrationProvider.IFIRMA: IFirmaClient,
    IntegrationProvider.FAKTUROWNIA: FakturowniaClient,
    IntegrationProvider.WFIRMA: WFirmaClient,
    IntegrationProvider.INFAKT: InFaktClient,
}

# Cloud storage client mapping
CLOUD_CLIENTS = {
    IntegrationProvider.NEXTCLOUD: NextcloudClient,
    IntegrationProvider.GOOGLE_DRIVE: GoogleDriveClient,
    IntegrationProvider.AWS_S3: S3Client,
    IntegrationProvider.MINIO: S3Client,  # MinIO uses S3 protocol
    IntegrationProvider.DROPBOX: DropboxClient,
    IntegrationProvider.ONEDRIVE: OneDriveClient,
}


def get_accounting_client(
    provider: IntegrationProvider,
    credentials: Dict[str, Any],
    settings: Dict[str, Any] = None
) -> Optional[BaseAccountingClient]:
    """
    Create accounting client for specified provider.
    
    Args:
        provider: Accounting provider (ifirma, fakturownia, etc.)
        credentials: API credentials
        settings: Additional settings
    
    Returns:
        Accounting client instance
    """
    client_class = ACCOUNTING_CLIENTS.get(provider)
    
    if not client_class:
        logger.error("Unknown accounting provider", provider=provider)
        return None
    
    return client_class(credentials=credentials, settings=settings)


def get_cloud_client(
    provider: IntegrationProvider,
    credentials: Dict[str, Any],
    settings: Dict[str, Any] = None
) -> Optional[BaseCloudStorageClient]:
    """
    Create cloud storage client for specified provider.
    
    Args:
        provider: Cloud provider (nextcloud, google_drive, etc.)
        credentials: API credentials
        settings: Additional settings
    
    Returns:
        Cloud storage client instance
    """
    client_class = CLOUD_CLIENTS.get(provider)
    
    if not client_class:
        logger.error("Unknown cloud provider", provider=provider)
        return None
    
    return client_class(credentials=credentials, settings=settings)


def get_client_from_config(
    integration_id: str,
    config_db: ConfigDatabase = None
) -> Optional[Union[BaseAccountingClient, BaseCloudStorageClient]]:
    """
    Create client from stored configuration.
    
    Args:
        integration_id: Integration ID in config database
        config_db: Config database instance (uses default if not provided)
    
    Returns:
        Client instance (accounting or cloud)
    """
    if config_db is None:
        config_db = get_config_db()
    
    config = config_db.get_integration(integration_id)
    
    if not config:
        logger.error("Integration not found", id=integration_id)
        return None
    
    provider = IntegrationProvider(config["provider"])
    credentials = config.get("credentials", {})
    settings = config.get("settings", {})
    
    # Add base_url to settings if present
    if config.get("base_url"):
        credentials["url"] = config["base_url"]
    
    if config["integration_type"] == IntegrationType.ACCOUNTING.value:
        return get_accounting_client(provider, credentials, settings)
    elif config["integration_type"] == IntegrationType.CLOUD_STORAGE.value:
        return get_cloud_client(provider, credentials, settings)
    else:
        logger.error("Unknown integration type", type=config["integration_type"])
        return None


async def verify_integration(integration_id: str) -> bool:
    """
    Verify integration connection.
    
    Args:
        integration_id: Integration ID
    
    Returns:
        True if connection successful
    """
    client = get_client_from_config(integration_id)
    
    if not client:
        return False
    
    try:
        result = await client.verify_connection()
        
        # Update verification status in config
        config_db = get_config_db()
        config_db.update_sync_status(
            integration_id,
            is_verified=result,
            last_error=None if result else "Connection verification failed"
        )
        
        return result
    
    except Exception as e:
        logger.error("Verification failed", id=integration_id, error=str(e))
        
        config_db = get_config_db()
        config_db.update_sync_status(
            integration_id,
            is_verified=False,
            last_error=str(e)
        )
        
        return False


class IntegrationManager:
    """
    High-level integration manager for B+R system.
    Coordinates accounting and cloud storage operations.
    """
    
    def __init__(self, config_db: ConfigDatabase = None):
        self.config_db = config_db or get_config_db()
        self.logger = structlog.get_logger()
    
    async def sync_invoices_from_accounting(
        self,
        integration_id: str,
        date_from=None,
        date_to=None,
        project_id: str = None
    ) -> Dict[str, Any]:
        """
        Sync invoices from accounting system to B+R database.
        """
        client = get_client_from_config(integration_id, self.config_db)
        
        if not client or not isinstance(client, BaseAccountingClient):
            return {"error": "Invalid accounting integration"}
        
        try:
            result = await client.sync_invoices_to_br_system(
                date_from=date_from,
                date_to=date_to,
                project_id=project_id
            )
            
            # Log sync
            self.config_db.log_sync(
                integration_id=integration_id,
                sync_type="invoices",
                status="success" if not result.get("errors") else "partial",
                items_processed=result.get("created", 0) + result.get("updated", 0),
                items_failed=len(result.get("errors", [])),
                details=result
            )
            
            return result
        
        except Exception as e:
            self.config_db.log_sync(
                integration_id=integration_id,
                sync_type="invoices",
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    async def upload_report_to_cloud(
        self,
        integration_id: str,
        report_content: bytes,
        report_name: str,
        year: int = None,
        month: int = None
    ) -> Dict[str, Any]:
        """
        Upload B+R report to cloud storage.
        """
        client = get_client_from_config(integration_id, self.config_db)
        
        if not client or not isinstance(client, BaseCloudStorageClient):
            return {"error": "Invalid cloud storage integration"}
        
        try:
            result = await client.upload_report(
                report_content=report_content,
                report_name=report_name,
                year=year,
                month=month
            )
            
            # Log upload
            self.config_db.log_sync(
                integration_id=integration_id,
                sync_type="upload",
                status="success" if result.success else "error",
                items_processed=1 if result.success else 0,
                details={
                    "file_path": result.file_path,
                    "file_url": result.file_url
                },
                error_message=result.error
            )
            
            return {
                "success": result.success,
                "file_id": result.file_id,
                "file_path": result.file_path,
                "file_url": result.file_url,
                "error": result.error
            }
        
        except Exception as e:
            self.config_db.log_sync(
                integration_id=integration_id,
                sync_type="upload",
                status="error",
                error_message=str(e)
            )
            return {"error": str(e)}
    
    def get_active_accounting_integrations(self) -> list:
        """Get list of active accounting integrations"""
        return self.config_db.list_integrations(
            integration_type=IntegrationType.ACCOUNTING,
            active_only=True
        )
    
    def get_active_cloud_integrations(self) -> list:
        """Get list of active cloud storage integrations"""
        return self.config_db.list_integrations(
            integration_type=IntegrationType.CLOUD_STORAGE,
            active_only=True
        )
