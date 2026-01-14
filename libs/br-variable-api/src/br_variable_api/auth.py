"""
Authentication methods for Variable API.

Supports:
- API Key (header or query param)
- Basic Auth (username:password)
- Session Token (cookie-based)
- SSH Key (for CLI access)
"""
import os
import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBasic, HTTPBasicCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

logger = structlog.get_logger()


class AuthMethod(str, Enum):
    """Supported authentication methods"""
    API_KEY = "api_key"
    BASIC = "basic"
    SESSION = "session"
    SSH_KEY = "ssh_key"
    ANONYMOUS = "anonymous"


@dataclass
class AuthContext:
    """Authentication context"""
    method: AuthMethod
    user_id: Optional[str] = None
    username: Optional[str] = None
    scopes: List[str] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["read"]
    
    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin" in self.scopes


# Security utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
basic_auth = HTTPBasic(auto_error=False)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class AuthProvider(ABC):
    """Abstract authentication provider"""
    
    @abstractmethod
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """Authenticate request and return context"""
        pass


class APIKeyAuth(AuthProvider):
    """API Key authentication"""
    
    def __init__(self, valid_keys: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize with valid API keys.
        
        Args:
            valid_keys: Dict mapping API key to user info
                       {"key123": {"user_id": "1", "scopes": ["read", "write"]}}
        """
        self.valid_keys = valid_keys or {}
        
        # Load from environment if not provided
        env_key = os.getenv("BR_API_KEY")
        if env_key and env_key not in self.valid_keys:
            self.valid_keys[env_key] = {
                "user_id": "system",
                "username": "api_user",
                "scopes": ["read", "write"]
            }
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        # Try header first
        api_key = request.headers.get("X-API-Key")
        
        # Then try query param
        if not api_key:
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            return None
        
        key_info = self.valid_keys.get(api_key)
        if not key_info:
            return None
        
        return AuthContext(
            method=AuthMethod.API_KEY,
            user_id=key_info.get("user_id"),
            username=key_info.get("username"),
            scopes=key_info.get("scopes", ["read"]),
        )


class BasicAuth(AuthProvider):
    """HTTP Basic authentication"""
    
    def __init__(self, users: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize with users.
        
        Args:
            users: Dict mapping username to user info with hashed password
        """
        self.users = users or {}
        
        # Add default user from environment
        env_user = os.getenv("BR_API_USER")
        env_pass = os.getenv("BR_API_PASSWORD")
        if env_user and env_pass:
            self.users[env_user] = {
                "password_hash": pwd_context.hash(env_pass),
                "scopes": ["read", "write"]
            }
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return None
        
        import base64
        try:
            credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = credentials.split(":", 1)
        except Exception:
            return None
        
        user_info = self.users.get(username)
        if not user_info:
            return None
        
        if not pwd_context.verify(password, user_info.get("password_hash", "")):
            return None
        
        return AuthContext(
            method=AuthMethod.BASIC,
            username=username,
            scopes=user_info.get("scopes", ["read"]),
        )


class SessionAuth(AuthProvider):
    """Session/JWT token authentication"""
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        # Try cookie
        token = request.cookies.get("session_token")
        
        # Try Authorization header
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if not token:
            return None
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return AuthContext(
                method=AuthMethod.SESSION,
                user_id=payload.get("sub"),
                username=payload.get("username"),
                scopes=payload.get("scopes", ["read"]),
                expires_at=datetime.fromtimestamp(payload.get("exp", 0)),
            )
        except JWTError:
            return None


class SSHKeyAuth(AuthProvider):
    """SSH key-based authentication for CLI access"""
    
    def __init__(self, authorized_keys: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize with authorized SSH public keys.
        
        Args:
            authorized_keys: Dict mapping key fingerprint to user info
        """
        self.authorized_keys = authorized_keys or {}
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        # SSH key fingerprint passed in header (set by SSH tunnel/proxy)
        key_fingerprint = request.headers.get("X-SSH-Key-Fingerprint")
        
        if not key_fingerprint:
            return None
        
        key_info = self.authorized_keys.get(key_fingerprint)
        if not key_info:
            return None
        
        return AuthContext(
            method=AuthMethod.SSH_KEY,
            user_id=key_info.get("user_id"),
            username=key_info.get("username"),
            scopes=key_info.get("scopes", ["read", "write"]),
        )


class MultiAuth:
    """Combined authentication supporting multiple methods"""
    
    def __init__(
        self,
        providers: Optional[List[AuthProvider]] = None,
        allow_anonymous: bool = False,
        anonymous_scopes: Optional[List[str]] = None,
    ):
        self.providers = providers or [
            APIKeyAuth(),
            BasicAuth(),
            SessionAuth(),
        ]
        self.allow_anonymous = allow_anonymous
        self.anonymous_scopes = anonymous_scopes or ["read"]
    
    async def __call__(self, request: Request) -> AuthContext:
        # Try each provider
        for provider in self.providers:
            context = await provider.authenticate(request)
            if context:
                logger.info("auth_success", method=context.method.value, user=context.username)
                return context
        
        # Allow anonymous if configured
        if self.allow_anonymous:
            return AuthContext(
                method=AuthMethod.ANONYMOUS,
                scopes=self.anonymous_scopes,
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagana autoryzacja",
            headers={"WWW-Authenticate": "Basic, Bearer, ApiKey"},
        )


def create_access_token(
    user_id: str,
    username: str,
    scopes: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = {
        "sub": user_id,
        "username": username,
        "scopes": scopes,
        "exp": expire,
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Default auth dependency
get_current_auth = MultiAuth(allow_anonymous=False)
get_optional_auth = MultiAuth(allow_anonymous=True, anonymous_scopes=["read"])
