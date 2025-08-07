import logging
from app.db.session import SessionLocal
from app.db.base import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize database with tables."""
    try:
        # Import all models to ensure they are registered
        from app.db.models import user, subscription, profile, infringement, takedown  # noqa
        
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise