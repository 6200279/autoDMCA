import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger('alembic.env')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    return settings.SQLALCHEMY_DATABASE_URI


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with enhanced configuration."""
    
    # Configure migration context with performance optimizations
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,  # Compare column types
        compare_server_default=True,  # Compare server defaults
        render_as_batch=True,  # Use batch operations for better compatibility
        transaction_per_migration=True,  # Each migration in its own transaction
        # Custom naming convention for constraints
        render_item=lambda type_, obj, autogen_context: (
            f"uq_{obj.table.name}_{obj.columns.keys()[0]}" 
            if type_ == "unique_constraint" 
            else None
        ) if hasattr(obj, 'table') and hasattr(obj, 'columns') else None
    )
    
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode with enhanced error handling and performance optimizations."""
    
    try:
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = str(get_url())
        
        # Enhanced engine configuration for migrations
        engine_config = {
            "pool_timeout": 60,  # Longer timeout for migrations
            "pool_pre_ping": True,  # Validate connections
            "connect_args": {
                "command_timeout": 300,  # 5 minute timeout for long migrations
                "server_settings": {
                    "application_name": "alembic_migration",
                    "jit": "off",  # Disable JIT during migrations
                }
            }
        }
        
        # Add engine config to configuration
        for key, value in engine_config.items():
            if key == "connect_args":
                # Handle connect_args specially as it's a nested dict
                configuration[f"sqlalchemy.{key}"] = str(value)
            else:
                configuration[f"sqlalchemy.{key}"] = str(value)
        
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,  # Use NullPool to avoid connection issues during migrations
        )
        
        logger.info("Starting database migration...")
        
        async with connectable.connect() as connection:
            # Set migration-specific settings
            await connection.execute(text("SET statement_timeout = '300s'"))
            await connection.execute(text("SET lock_timeout = '60s'"))
            
            await connection.run_sync(do_run_migrations)
            
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        try:
            await connectable.dispose()
        except Exception as e:
            logger.warning(f"Error disposing engine: {e}")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()