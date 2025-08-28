from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl

# Use a simple configuration approach that works with all Pydantic versions
class Settings:
    """Application configuration settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings with environment variables or defaults."""
        import os
        from pathlib import Path
        
        # Load .env file if it exists
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                print(f"Loaded .env from {env_file}")
            except ImportError:
                # Manually parse .env if python-dotenv not available
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key.strip(), value.strip())
                print(f"Manually loaded .env from {env_file}")
        
        # Load from environment with defaults
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "Content Protection Platform")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION = os.getenv("DESCRIPTION", "AI-powered content protection and DMCA takedown service")
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # CORS
        cors_origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:13000,http://localhost:3000")
        self.BACKEND_CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
        self.ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",")]
        
        # Database
        self.POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "autodmca")
        self.POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        self.POSTGRES_SSL_MODE = os.getenv("POSTGRES_SSL_MODE", "prefer")
        self.POSTGRES_CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "30"))
        self.POSTGRES_COMMAND_TIMEOUT = int(os.getenv("POSTGRES_COMMAND_TIMEOUT", "60"))
        
        # Build database URI - check DATABASE_URL first (docker-compose standard)
        self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
        if not self.SQLALCHEMY_DATABASE_URI:
            # Simple AsyncPG connection for local development
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/"
                f"{self.POSTGRES_DB}"
            )
        
        self.DATABASE_QUERY_LOGGING = os.getenv("DATABASE_QUERY_LOGGING", "false").lower() == "true"
        self.DATABASE_SLOW_QUERY_THRESHOLD = float(os.getenv("DATABASE_SLOW_QUERY_THRESHOLD", "1.0"))
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Celery
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        
        # Email
        self.SMTP_HOST = os.getenv("SMTP_HOST")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
        self.SMTP_USER = os.getenv("SMTP_USER")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        self.EMAILS_FROM_EMAIL = os.getenv("EMAILS_FROM_EMAIL")
        self.EMAILS_FROM_NAME = os.getenv("EMAILS_FROM_NAME")
        
        # File Upload
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
        
        # AI/ML Services
        self.FACE_RECOGNITION_TOLERANCE = float(os.getenv("FACE_RECOGNITION_TOLERANCE", "0.6"))
        self.CONTENT_SIMILARITY_THRESHOLD = float(os.getenv("CONTENT_SIMILARITY_THRESHOLD", "0.8"))
        
        # DMCA
        self.DMCA_EMAIL_TEMPLATE = os.getenv("DMCA_EMAIL_TEMPLATE", "dmca_takedown.html")
        self.DMCA_RESPONSE_DAYS = int(os.getenv("DMCA_RESPONSE_DAYS", "7"))
        
        # Billing/Subscriptions
        self.STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
        self.STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # Logging
        self.SENTRY_DSN = os.getenv("SENTRY_DSN")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Database Health Check
        self.DATABASE_HEALTH_CHECK_INTERVAL = int(os.getenv("DATABASE_HEALTH_CHECK_INTERVAL", "300"))
        self.DATABASE_MAX_RETRIES = int(os.getenv("DATABASE_MAX_RETRIES", "3"))
        self.DATABASE_RETRY_DELAY = int(os.getenv("DATABASE_RETRY_DELAY", "5"))
        
        # SendGrid Configuration
        self.SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
        self.SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
        self.SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME")
        
        # SendGrid Template IDs
        self.SENDGRID_DMCA_TEMPLATE_ID = os.getenv("SENDGRID_DMCA_TEMPLATE_ID")
        self.SENDGRID_ALERT_TEMPLATE_ID = os.getenv("SENDGRID_ALERT_TEMPLATE_ID") 
        self.SENDGRID_WELCOME_TEMPLATE_ID = os.getenv("SENDGRID_WELCOME_TEMPLATE_ID")
        self.SENDGRID_VERIFICATION_TEMPLATE_ID = os.getenv("SENDGRID_VERIFICATION_TEMPLATE_ID")
        self.SENDGRID_PASSWORD_RESET_TEMPLATE_ID = os.getenv("SENDGRID_PASSWORD_RESET_TEMPLATE_ID")
        self.SENDGRID_SUBSCRIPTION_TEMPLATE_ID = os.getenv("SENDGRID_SUBSCRIPTION_TEMPLATE_ID")
        self.SENDGRID_BILLING_REMINDER_TEMPLATE_ID = os.getenv("SENDGRID_BILLING_REMINDER_TEMPLATE_ID")
        
        # Google Vision API Configuration
        self.GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")
        self.GOOGLE_VISION_CREDENTIALS_PATH = os.getenv("GOOGLE_VISION_CREDENTIALS_PATH")
        self.GOOGLE_VISION_CREDENTIALS_JSON = os.getenv("GOOGLE_VISION_CREDENTIALS_JSON")
        
        # PayPal Configuration
        self.PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
        self.PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
        self.PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")
        self.PAYPAL_ENVIRONMENT = os.getenv("PAYPAL_ENVIRONMENT", "sandbox")  # 'sandbox' or 'live'
        
        # Frontend URL for redirects
        self.FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Support Configuration
        self.SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@autodmca.com")
        
        # Development
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()