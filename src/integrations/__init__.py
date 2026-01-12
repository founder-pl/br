"""
Integrations Module - Accounting and Cloud Storage Integrations

This module provides integrations with:

Accounting Systems:
- iFirma (ifirma.pl)
- Fakturownia (fakturownia.pl)  
- wFirma (wfirma.pl)
- InFakt (infakt.pl)

Cloud Storage:
- Nextcloud (WebDAV)
- Google Drive
- AWS S3 / MinIO
- Dropbox (planned)
- OneDrive (planned)

Configuration is stored in SQLite by default with support for PostgreSQL/MySQL.
Credentials are encrypted using Fernet symmetric encryption.
"""
from .config.database import (
    ConfigDatabase,
    IntegrationProvider,
    IntegrationType,
    IntegrationConfig,
    SyncLog,
    OAuthToken,
    get_config_db
)

from .factory import (
    get_accounting_client,
    get_cloud_client,
    get_client_from_config,
    verify_integration,
    IntegrationManager
)

from .accounting.base import (
    BaseAccountingClient,
    Invoice,
    InvoiceItem,
    InvoiceType,
    InvoiceStatus,
    AccountingDocument
)

from .cloud.base import (
    BaseCloudStorageClient,
    CloudFile,
    UploadResult
)

__all__ = [
    # Config
    'ConfigDatabase',
    'IntegrationProvider',
    'IntegrationType',
    'get_config_db',
    
    # Factory
    'get_accounting_client',
    'get_cloud_client',
    'get_client_from_config',
    'verify_integration',
    'IntegrationManager',
    
    # Accounting
    'BaseAccountingClient',
    'Invoice',
    'InvoiceItem',
    'InvoiceType',
    'InvoiceStatus',
    
    # Cloud
    'BaseCloudStorageClient',
    'CloudFile',
    'UploadResult',
]
