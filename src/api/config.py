"""
API Configuration
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment"""
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://br_admin:br_secret_2025@localhost:5432/br_system"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # External services
    OCR_SERVICE_URL: str = "http://localhost:8001"
    LLM_SERVICE_URL: str = "http://localhost:4000"
    
    # Company info
    COMPANY_NAME: str = "Tomasz Sapletta"
    COMPANY_NIP: str = "5881918662"
    COMPANY_REGON: str = "220665410"
    COMPANY_PKD: str = "72.10.Z"
    
    # Project info
    PROJECT_NAME: str = "Prototypowy system modularny"
    FISCAL_YEAR: int = 2025
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost", "http://localhost:80", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
