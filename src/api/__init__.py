"""
API Backend Module
"""
from .main import app
from .config import settings
from .database import get_db, init_database, close_database

__all__ = ['app', 'settings', 'get_db', 'init_database', 'close_database']
