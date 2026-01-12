"""
Configuration Database - SQLite default with multi-database support
Stores integration tokens, credentials, and settings securely
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
import json

from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger()

# Base for config models
ConfigBase = declarative_base()


class DatabaseType(str, Enum):
    """Supported configuration database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"  # Would need different ORM


class IntegrationType(str, Enum):
    """Types of integrations"""
    ACCOUNTING = "accounting"
    CLOUD_STORAGE = "cloud_storage"
    EMAIL = "email"
    WEBHOOK = "webhook"


class IntegrationProvider(str, Enum):
    """Supported integration providers"""
    # Accounting
    IFIRMA = "ifirma"
    FAKTUROWNIA = "fakturownia"
    WFIRMA = "wfirma"
    INFAKT = "infakt"
    KSEF = "ksef"  # Polish e-invoicing system
    
    # Cloud Storage
    NEXTCLOUD = "nextcloud"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    AWS_S3 = "aws_s3"
    MINIO = "minio"
    
    # Email
    SMTP = "smtp"
    GMAIL = "gmail"


class IntegrationConfig(ConfigBase):
    """Integration configuration storage"""
    __tablename__ = "integration_configs"
    
    id = Column(String(50), primary_key=True)
    provider = Column(String(50), nullable=False, index=True)
    integration_type = Column(String(30), nullable=False, index=True)
    
    # Encrypted credentials
    credentials_encrypted = Column(Text, nullable=True)
    
    # Non-sensitive settings (stored as JSON)
    settings = Column(JSON, default={})
    
    # Connection info
    base_url = Column(String(500), nullable=True)
    api_version = Column(String(20), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<IntegrationConfig({self.id}, {self.provider})>"


class SyncLog(ConfigBase):
    """Synchronization logs"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    integration_id = Column(String(50), nullable=False, index=True)
    sync_type = Column(String(30), nullable=False)  # invoices, documents, upload
    
    status = Column(String(20), nullable=False)  # success, error, partial
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    
    details = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class OAuthToken(ConfigBase):
    """OAuth tokens storage"""
    __tablename__ = "oauth_tokens"
    
    id = Column(String(50), primary_key=True)
    integration_id = Column(String(50), nullable=False, index=True)
    
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_type = Column(String(30), default="Bearer")
    
    expires_at = Column(DateTime, nullable=True)
    scope = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfigDatabase:
    """
    Configuration database manager with encryption support.
    Default: SQLite, supports PostgreSQL, MySQL
    """
    
    def __init__(
        self,
        db_type: DatabaseType = None,
        db_url: str = None,
        encryption_key: str = None
    ):
        """
        Initialize config database.
        
        Args:
            db_type: Database type (default from env or SQLite)
            db_url: Database URL (default from env or sqlite:///config.db)
            encryption_key: Fernet key for encrypting credentials
        """
        # Get settings from environment or use defaults
        self.db_type = db_type or DatabaseType(
            os.getenv("CONFIG_DB_TYPE", "sqlite")
        )
        
        self.db_url = db_url or os.getenv(
            "CONFIG_DB_URL",
            "sqlite:///config.db"
        )
        
        # Encryption key for sensitive data
        key = encryption_key or os.getenv("CONFIG_ENCRYPTION_KEY")
        if key:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            # Generate and log warning
            self.fernet = Fernet(Fernet.generate_key())
            logger.warning("No CONFIG_ENCRYPTION_KEY set, using generated key (not persistent!)")
        
        # Create engine
        if self.db_type == DatabaseType.SQLITE:
            # SQLite specific settings for thread safety
            self.engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
        else:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)
        
        # Create tables
        ConfigBase.metadata.create_all(self.engine)
        
        logger.info("Config database initialized", 
                   db_type=self.db_type.value,
                   db_url=self.db_url.split("@")[-1] if "@" in self.db_url else self.db_url)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    # ==========================================================================
    # Integration Config Methods
    # ==========================================================================
    
    def save_integration(
        self,
        integration_id: str,
        provider: IntegrationProvider,
        integration_type: IntegrationType,
        credentials: Dict[str, Any] = None,
        settings: Dict[str, Any] = None,
        base_url: str = None,
        api_version: str = None
    ) -> IntegrationConfig:
        """Save or update integration configuration"""
        with self.get_session() as session:
            config = session.query(IntegrationConfig).filter_by(id=integration_id).first()
            
            if not config:
                config = IntegrationConfig(
                    id=integration_id,
                    provider=provider.value,
                    integration_type=integration_type.value
                )
                session.add(config)
            
            if credentials:
                config.credentials_encrypted = self.encrypt(json.dumps(credentials))
            
            if settings:
                config.settings = settings
            
            if base_url:
                config.base_url = base_url
            
            if api_version:
                config.api_version = api_version
            
            config.updated_at = datetime.utcnow()
            session.commit()
            
            logger.info("Integration saved", id=integration_id, provider=provider.value)
            return config
    
    def get_integration(self, integration_id: str) -> Optional[Dict[str, Any]]:
        """Get integration configuration with decrypted credentials"""
        with self.get_session() as session:
            config = session.query(IntegrationConfig).filter_by(id=integration_id).first()
            
            if not config:
                return None
            
            result = {
                "id": config.id,
                "provider": config.provider,
                "integration_type": config.integration_type,
                "settings": config.settings or {},
                "base_url": config.base_url,
                "api_version": config.api_version,
                "is_active": config.is_active,
                "is_verified": config.is_verified,
                "last_sync_at": config.last_sync_at,
                "last_error": config.last_error,
            }
            
            if config.credentials_encrypted:
                try:
                    result["credentials"] = json.loads(
                        self.decrypt(config.credentials_encrypted)
                    )
                except Exception as e:
                    logger.error("Failed to decrypt credentials", id=integration_id, error=str(e))
                    result["credentials"] = {}
            
            return result
    
    def list_integrations(
        self,
        integration_type: IntegrationType = None,
        provider: IntegrationProvider = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List integrations with optional filtering"""
        with self.get_session() as session:
            query = session.query(IntegrationConfig)
            
            if integration_type:
                query = query.filter_by(integration_type=integration_type.value)
            
            if provider:
                query = query.filter_by(provider=provider.value)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            configs = query.all()
            
            return [
                {
                    "id": c.id,
                    "provider": c.provider,
                    "integration_type": c.integration_type,
                    "is_active": c.is_active,
                    "is_verified": c.is_verified,
                    "last_sync_at": c.last_sync_at,
                    "settings": c.settings,
                }
                for c in configs
            ]
    
    def delete_integration(self, integration_id: str) -> bool:
        """Delete integration configuration"""
        with self.get_session() as session:
            config = session.query(IntegrationConfig).filter_by(id=integration_id).first()
            if config:
                session.delete(config)
                logger.info("Integration deleted", id=integration_id)
                return True
            return False
    
    def update_sync_status(
        self,
        integration_id: str,
        is_verified: bool = None,
        last_error: str = None
    ):
        """Update integration sync status"""
        with self.get_session() as session:
            config = session.query(IntegrationConfig).filter_by(id=integration_id).first()
            if config:
                config.last_sync_at = datetime.utcnow()
                if is_verified is not None:
                    config.is_verified = is_verified
                if last_error is not None:
                    config.last_error = last_error
    
    # ==========================================================================
    # OAuth Token Methods
    # ==========================================================================
    
    def save_oauth_token(
        self,
        token_id: str,
        integration_id: str,
        access_token: str,
        refresh_token: str = None,
        expires_at: datetime = None,
        scope: str = None
    ):
        """Save OAuth token"""
        with self.get_session() as session:
            token = session.query(OAuthToken).filter_by(id=token_id).first()
            
            if not token:
                token = OAuthToken(id=token_id, integration_id=integration_id)
                session.add(token)
            
            token.access_token_encrypted = self.encrypt(access_token)
            if refresh_token:
                token.refresh_token_encrypted = self.encrypt(refresh_token)
            token.expires_at = expires_at
            token.scope = scope
            token.updated_at = datetime.utcnow()
    
    def get_oauth_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth token with decrypted values"""
        with self.get_session() as session:
            token = session.query(OAuthToken).filter_by(id=token_id).first()
            
            if not token:
                return None
            
            return {
                "id": token.id,
                "integration_id": token.integration_id,
                "access_token": self.decrypt(token.access_token_encrypted),
                "refresh_token": self.decrypt(token.refresh_token_encrypted) if token.refresh_token_encrypted else None,
                "token_type": token.token_type,
                "expires_at": token.expires_at,
                "scope": token.scope,
            }
    
    # ==========================================================================
    # Sync Log Methods
    # ==========================================================================
    
    def log_sync(
        self,
        integration_id: str,
        sync_type: str,
        status: str,
        items_processed: int = 0,
        items_failed: int = 0,
        details: Dict = None,
        error_message: str = None
    ) -> int:
        """Log synchronization activity"""
        with self.get_session() as session:
            log = SyncLog(
                integration_id=integration_id,
                sync_type=sync_type,
                status=status,
                items_processed=items_processed,
                items_failed=items_failed,
                details=details or {},
                error_message=error_message,
                completed_at=datetime.utcnow() if status in ["success", "error"] else None
            )
            session.add(log)
            session.commit()
            return log.id
    
    def get_sync_logs(
        self,
        integration_id: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get sync logs"""
        with self.get_session() as session:
            query = session.query(SyncLog)
            
            if integration_id:
                query = query.filter_by(integration_id=integration_id)
            
            logs = query.order_by(SyncLog.started_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": l.id,
                    "integration_id": l.integration_id,
                    "sync_type": l.sync_type,
                    "status": l.status,
                    "items_processed": l.items_processed,
                    "items_failed": l.items_failed,
                    "details": l.details,
                    "error_message": l.error_message,
                    "started_at": l.started_at,
                    "completed_at": l.completed_at,
                }
                for l in logs
            ]


# Global instance
_config_db: Optional[ConfigDatabase] = None


def get_config_db() -> ConfigDatabase:
    """Get or create config database instance"""
    global _config_db
    if _config_db is None:
        _config_db = ConfigDatabase()
    return _config_db
