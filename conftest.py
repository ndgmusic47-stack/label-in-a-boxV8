"""
Pytest configuration and fixtures for testing
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database import Base

# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture
async def test_db():
    """
    Fixture that provides an isolated, in-memory SQLite database connection for each test.
    
    This fixture:
    - Creates all tables before the test runs
    - Yields a clean AsyncSession for the test
    - Drops all tables after the test completes
    """
    # Create all tables
    async with test_engine.begin() as conn:
        # Import models to ensure they're registered with Base
        from models import User  # noqa: F401
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a session for the test
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

