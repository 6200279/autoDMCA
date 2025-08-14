"""
Database startup and management utilities.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.db.utils import initialize_database, get_database_health, wait_for_database
from app.db.session import engine

logger = logging.getLogger(__name__)


async def check_database_connection(retry_count: int = 5) -> bool:
    """
    Check if database is available and healthy.
    
    Args:
        retry_count: Number of connection attempts
        
    Returns:
        True if database is healthy, False otherwise
    """
    logger.info("Checking database connection...")
    
    for attempt in range(retry_count):
        try:
            health_info = await get_database_health()
            if health_info["healthy"]:
                logger.info(f"Database connection successful (attempt {attempt + 1})")
                logger.info(f"Database version: {health_info.get('version', 'unknown')}")
                logger.info(f"Response time: {health_info['response_time']:.2f}ms")
                return True
            else:
                logger.warning(f"Database health check failed: {health_info.get('error')}")
                
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
        
        if attempt < retry_count - 1:
            logger.info(f"Waiting {settings.DATABASE_RETRY_DELAY} seconds before next attempt...")
            await asyncio.sleep(settings.DATABASE_RETRY_DELAY)
    
    logger.error("Failed to establish database connection after all attempts")
    return False


def run_migrations(direction: str = "upgrade") -> bool:
    """
    Run database migrations using Alembic.
    
    Args:
        direction: Migration direction ('upgrade' or 'downgrade')
        
    Returns:
        True if migrations completed successfully, False otherwise
    """
    try:
        # Find alembic.ini file
        alembic_cfg_path = Path(__file__).parent.parent.parent / "alembic.ini"
        
        if not alembic_cfg_path.exists():
            logger.error(f"Alembic configuration file not found: {alembic_cfg_path}")
            return False
        
        # Create Alembic config
        alembic_cfg = Config(str(alembic_cfg_path))
        
        # Set the database URL
        alembic_cfg.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))
        
        logger.info(f"Running database migrations ({direction})...")
        
        if direction == "upgrade":
            command.upgrade(alembic_cfg, "head")
        elif direction == "downgrade":
            command.downgrade(alembic_cfg, "-1")  # Downgrade by one revision
        else:
            logger.error(f"Invalid migration direction: {direction}")
            return False
            
        logger.info("Database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


async def initialize_development_database():
    """Initialize database for development environment."""
    logger.info("Initializing development database...")
    
    try:
        # Wait for database to be available
        if not await wait_for_database(timeout=60):
            logger.error("Database is not available")
            return False
        
        # Initialize database connection
        await initialize_database()
        
        # Run migrations
        if not run_migrations("upgrade"):
            logger.error("Failed to run database migrations")
            return False
        
        # Final health check
        health_info = await get_database_health()
        if health_info["healthy"]:
            logger.info("Development database initialization completed successfully")
            return True
        else:
            logger.error(f"Database health check failed: {health_info.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"Development database initialization failed: {e}")
        return False


async def reset_database():
    """Reset database by dropping all tables and re-running migrations."""
    logger.warning("Resetting database - this will delete all data!")
    
    try:
        # Import here to avoid circular imports
        from app.db.base import Base
        
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("All database tables dropped")
        
        # Run migrations to recreate tables
        if run_migrations("upgrade"):
            logger.info("Database reset completed successfully")
            return True
        else:
            logger.error("Failed to recreate database tables")
            return False
            
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


async def create_migration(message: str) -> bool:
    """
    Create a new database migration.
    
    Args:
        message: Migration message/description
        
    Returns:
        True if migration was created successfully, False otherwise
    """
    try:
        # Find alembic.ini file
        alembic_cfg_path = Path(__file__).parent.parent.parent / "alembic.ini"
        
        if not alembic_cfg_path.exists():
            logger.error(f"Alembic configuration file not found: {alembic_cfg_path}")
            return False
        
        # Create Alembic config
        alembic_cfg = Config(str(alembic_cfg_path))
        alembic_cfg.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))
        
        logger.info(f"Creating migration: {message}")
        command.revision(alembic_cfg, message=message, autogenerate=True)
        
        logger.info("Migration created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration creation failed: {e}")
        return False


if __name__ == "__main__":
    """Command line interface for database management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management utilities")
    parser.add_argument(
        "command",
        choices=["check", "init", "migrate", "reset", "create-migration"],
        help="Command to execute"
    )
    parser.add_argument(
        "--message", "-m",
        help="Migration message (for create-migration command)"
    )
    parser.add_argument(
        "--direction",
        choices=["upgrade", "downgrade"],
        default="upgrade",
        help="Migration direction (for migrate command)"
    )
    
    args = parser.parse_args()
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        if args.command == "check":
            success = await check_database_connection()
            sys.exit(0 if success else 1)
            
        elif args.command == "init":
            success = await initialize_development_database()
            sys.exit(0 if success else 1)
            
        elif args.command == "migrate":
            success = run_migrations(args.direction)
            sys.exit(0 if success else 1)
            
        elif args.command == "reset":
            # Ask for confirmation
            response = input("This will delete all data. Are you sure? (yes/no): ")
            if response.lower() == "yes":
                success = await reset_database()
                sys.exit(0 if success else 1)
            else:
                print("Database reset cancelled")
                sys.exit(0)
                
        elif args.command == "create-migration":
            if not args.message:
                print("Error: --message is required for create-migration command")
                sys.exit(1)
            success = await create_migration(args.message)
            sys.exit(0 if success else 1)
    
    asyncio.run(main())