"""
Comprehensive logging configuration for the billing system.
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings


class BillingFormatter(logging.Formatter):
    """Custom formatter for billing-related logs."""
    
    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()
        
        # Add service info
        record.service = "content-protection-billing"
        record.version = settings.VERSION
        
        # Format the record
        formatted = super().format(record)
        
        return formatted


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for production logging."""
    
    def format(self, record):
        import json
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': 'content-protection-billing',
            'version': settings.VERSION,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'subscription_id'):
            log_entry['subscription_id'] = record.subscription_id
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'stripe_error'):
            log_entry['stripe_error'] = record.stripe_error
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = record.event_type
        if hasattr(record, 'event_id'):
            log_entry['event_id'] = record.event_id
        if hasattr(record, 'processing_time'):
            log_entry['processing_time'] = record.processing_time
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        },
        'detailed': {
            'format': '[%(asctime)s] %(levelname)s in %(name)s [%(pathname)s:%(lineno)d]: %(message)s'
        },
        'billing': {
            '()': BillingFormatter,
            'format': '[%(timestamp)s] %(service)s v%(version)s - %(levelname)s in %(name)s: %(message)s'
        },
        'structured': {
            '()': StructuredFormatter,
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if settings.DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'billing' if settings.DEBUG else 'structured'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'structured'
        },
        'billing_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/billing.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'structured'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'app.services.billing': {
            'level': 'DEBUG',
            'handlers': ['console', 'billing_file', 'error_file'],
            'propagate': False
        },
        'app.api.v1.endpoints.billing': {
            'level': 'DEBUG',
            'handlers': ['console', 'billing_file', 'error_file'],
            'propagate': False
        },
        'stripe': {
            'level': 'INFO',
            'handlers': ['console', 'billing_file'],
            'propagate': False
        },
        'sqlalchemy.engine': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False
        },
        '': {  # Root logger
            'level': settings.LOG_LEVEL,
            'handlers': ['console', 'file', 'error_file'],
        }
    }
}


def setup_logging():
    """Setup logging configuration."""
    import os
    
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured for {settings.PROJECT_NAME} v{settings.VERSION}",
        extra={
            'service': 'content-protection-billing',
            'version': settings.VERSION,
            'debug_mode': settings.DEBUG,
            'log_level': settings.LOG_LEVEL
        }
    )


class BillingLogger:
    """Specialized logger for billing operations."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_subscription_event(
        self,
        event_type: str,
        user_id: int,
        subscription_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        level: str = 'INFO'
    ):
        """Log subscription-related events."""
        message = f"Subscription {event_type}"
        
        extra = {
            'user_id': user_id,
            'event_type': event_type,
            'operation': 'subscription'
        }
        
        if subscription_id:
            extra['subscription_id'] = subscription_id
        
        if details:
            extra.update(details)
        
        self.logger.log(getattr(logging, level.upper()), message, extra=extra)
    
    def log_payment_event(
        self,
        event_type: str,
        user_id: int,
        amount: float,
        currency: str = 'USD',
        payment_method_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: str = 'INFO'
    ):
        """Log payment-related events."""
        message = f"Payment {event_type}: {amount} {currency}"
        
        extra = {
            'user_id': user_id,
            'event_type': event_type,
            'operation': 'payment',
            'amount': amount,
            'currency': currency
        }
        
        if payment_method_id:
            extra['payment_method_id'] = payment_method_id
        
        if details:
            extra.update(details)
        
        self.logger.log(getattr(logging, level.upper()), message, extra=extra)
    
    def log_usage_event(
        self,
        user_id: int,
        metric: str,
        quantity: int,
        allowed: bool,
        current_usage: Optional[int] = None,
        limit: Optional[int] = None,
        reason: Optional[str] = None
    ):
        """Log usage-related events."""
        status = 'allowed' if allowed else 'denied'
        message = f"Usage {metric}: {quantity} ({status})"
        
        extra = {
            'user_id': user_id,
            'operation': 'usage',
            'metric': metric,
            'quantity': quantity,
            'allowed': allowed
        }
        
        if current_usage is not None:
            extra['current_usage'] = current_usage
        
        if limit is not None:
            extra['limit'] = limit
        
        if reason:
            extra['reason'] = reason
        
        level = logging.INFO if allowed else logging.WARNING
        self.logger.log(level, message, extra=extra)
    
    def log_webhook_event(
        self,
        event_type: str,
        event_id: str,
        processed: bool,
        processing_time: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Log webhook processing events."""
        status = 'processed' if processed else 'failed'
        message = f"Webhook {event_type} ({event_id}): {status}"
        
        extra = {
            'operation': 'webhook',
            'event_type': event_type,
            'event_id': event_id,
            'processed': processed
        }
        
        if processing_time:
            extra['processing_time'] = processing_time
        
        if error:
            extra['error'] = error
        
        level = logging.INFO if processed else logging.ERROR
        self.logger.log(level, message, extra=extra)
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log errors with context."""
        message = f"Error in {operation}: {str(error)}"
        
        extra = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        if user_id:
            extra['user_id'] = user_id
        
        if context:
            extra['context'] = context
        
        if hasattr(error, 'error_code'):
            extra['error_code'] = error.error_code
        
        self.logger.error(message, extra=extra, exc_info=True)


# Performance monitoring
class PerformanceMonitor:
    """Monitor performance of billing operations."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        if duration > 5.0:  # Log slow operations
            self.logger.warning(
                f"Slow billing operation detected: {duration:.2f}s",
                extra={'processing_time': duration, 'performance': 'slow'}
            )
        elif duration > 1.0:
            self.logger.info(
                f"Billing operation completed: {duration:.2f}s",
                extra={'processing_time': duration, 'performance': 'normal'}
            )


# Create billing logger instance
billing_logger = BillingLogger('app.services.billing')