from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase

# Create base class for declarative models
Base = declarative_base()

# Import all models to ensure they are registered with SQLAlchemy
# Note: Import these models in your application's startup script, not here
# to avoid circular imports