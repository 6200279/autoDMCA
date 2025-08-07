from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase

# Create base class for declarative models
Base = declarative_base()

# Import all models to ensure they are registered with SQLAlchemy
from app.db.models.user import User  # noqa
from app.db.models.subscription import Subscription  # noqa
from app.db.models.profile import ProtectedProfile  # noqa
from app.db.models.infringement import Infringement  # noqa
from app.db.models.takedown import TakedownRequest  # noqa
from app.db.models.social_media import (  # noqa
    SocialMediaAccount, SocialMediaImpersonation, SocialMediaReport,
    MonitoringSession, PlatformAPICredentials
)