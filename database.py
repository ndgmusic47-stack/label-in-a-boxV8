import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

# Default to SQLite with aiosqlite, but allow override via DATABASE_URL env var
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sql_app.db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging during development
    future=True,
)

# Create declarative base for models
Base = declarative_base()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """
    Initialize the database by creating all tables.
    This should be called on application startup.
    """
    async with engine.begin() as conn:
        # Import models here to ensure they're registered with Base
        from models import User  # noqa: F401
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields a database session.
    Use this in FastAPI route dependencies to get a database session.
    
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Use db here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
