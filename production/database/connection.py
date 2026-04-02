# production/database/connection.py
"""
Database connection configuration for PostgreSQL with asyncpg.
"""

import os

# Database URL configuration
# Supports both postgresql:// and postgresql+asyncpg:// formats
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/nexusflow"
)

# Convert sqlalchemy URL format to asyncpg format if needed
def get_asyncpg_url() -> str:
    """Get database URL in asyncpg-compatible format."""
    url = DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url

async def get_db_pool():
    """
    Return database connection pool.
    
    Deprecated: Use database_operations.db_manager.pool instead.
    This is kept for backward compatibility.
    """
    from .database_operations import db_manager
    return db_manager.pool

async def get_db():
    """
    Get database connection for FastAPI dependency injection.
    
    Deprecated: Use get_db_connection from database_operations instead.
    """
    from .database_operations import get_db_connection
    async with get_db_connection() as conn:
        yield conn
