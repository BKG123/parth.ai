import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
