import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event

from app.core.config import settings

logger = logging.getLogger(__name__)

# Enhanced database engine configuration with optimized connection pooling
engine_kwargs = {
    "pool_size": 20,  # Number of connections to maintain in the pool
    "max_overflow": 30,  # Additional connections that can be created on demand
    "pool_timeout": 30,  # Timeout when getting connection from pool
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Validate connections before use
    "echo": settings.DEBUG,  # Log SQL queries in debug mode
    "echo_pool": settings.DEBUG,  # Log connection pool activity in debug mode
    "future": True,  # Use SQLAlchemy 2.0 style
}

# Use QueuePool for production, NullPool for testing to avoid connection issues
if settings.DEBUG:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["poolclass"] = QueuePool

engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI), **engine_kwargs)

# Create async session factory with optimized settings
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Legacy session maker for backward compatibility
SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Database connection event handlers for monitoring and logging
@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log successful database connections."""
    logger.info(f"Database connection established: {connection_record.info}")

@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool."""
    logger.debug("Connection returned to pool")

@event.listens_for(engine.sync_engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    """Log connection invalidations."""
    logger.warning(f"Connection invalidated: {exception}")

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Legacy function name for backward compatibility."""
    async for session in get_async_session():
        yield session