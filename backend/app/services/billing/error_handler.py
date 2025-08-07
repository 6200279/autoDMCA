"""
Comprehensive error handler for billing operations with logging and monitoring.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import stripe

from app.core.config import settings
from .exceptions import (
    BillingError,
    SubscriptionError,
    PaymentError,
    UsageError,
    WebhookError,
    StripeError,
    StripeConfigurationError,
    PaymentFailedError,
    CardDeclinedError,
    InsufficientFundsError,
    UsageLimitExceededError,
    InvalidWebhookSignatureError
)

logger = logging.getLogger(__name__)


class BillingErrorHandler:
    """Centralized error handling for billing operations."""
    
    @staticmethod
    def handle_stripe_error(
        stripe_error: stripe.error.StripeError,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BillingError:
        """Convert Stripe errors to application-specific errors with logging."""
        
        context = context or {}
        error_details = {
            "operation": operation,
            "stripe_error_type": type(stripe_error).__name__,
            "stripe_error_code": getattr(stripe_error, 'code', None),
            "stripe_error_param": getattr(stripe_error, 'param', None),
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Log the Stripe error
        logger.error(
            f"Stripe error in {operation}: {stripe_error}",
            extra={
                "stripe_error": str(stripe_error),
                "error_details": error_details
            }
        )
        
        # Convert specific Stripe errors to application errors
        if isinstance(stripe_error, stripe.error.CardError):
            return BillingErrorHandler._handle_card_error(stripe_error, error_details)
        
        elif isinstance(stripe_error, stripe.error.InvalidRequestError):
            return BillingErrorHandler._handle_invalid_request_error(stripe_error, error_details)
        
        elif isinstance(stripe_error, stripe.error.AuthenticationError):
            return StripeConfigurationError("Invalid Stripe API key")
        
        elif isinstance(stripe_error, stripe.error.PermissionError):
            return StripeConfigurationError("Insufficient permissions for Stripe operation")
        
        elif isinstance(stripe_error, stripe.error.RateLimitError):
            return StripeError(
                "Rate limit exceeded. Please try again later.",
                "STRIPE_RATE_LIMIT",
                error_details
            )
        
        elif isinstance(stripe_error, stripe.error.APIConnectionError):
            return StripeError(
                "Unable to connect to Stripe. Please check your internet connection.",
                "STRIPE_CONNECTION_ERROR",
                error_details
            )
        
        elif isinstance(stripe_error, stripe.error.APIError):
            return StripeError(
                "An error occurred with Stripe's API. Please try again.",
                "STRIPE_API_ERROR",
                error_details
            )
        
        elif isinstance(stripe_error, stripe.error.SignatureVerificationError):
            return InvalidWebhookSignatureError()
        
        else:
            # Generic Stripe error
            return StripeError(
                f"Stripe error: {str(stripe_error)}",
                "STRIPE_GENERIC_ERROR",
                error_details
            )
    
    @staticmethod
    def _handle_card_error(
        card_error: stripe.error.CardError,
        error_details: Dict[str, Any]
    ) -> PaymentError:
        """Handle Stripe card errors."""
        
        decline_code = card_error.decline_code
        error_code = card_error.code
        
        # Map Stripe decline codes to specific errors
        if decline_code == 'insufficient_funds':
            return InsufficientFundsError(0)  # Amount would come from context
        
        elif decline_code in ['card_declined', 'generic_decline']:
            return CardDeclinedError(card_error.user_message or "Your card was declined")
        
        elif error_code in ['card_expired', 'expired_card']:
            return PaymentFailedError(
                "Your card has expired. Please update your payment method.",
                0,
                error_details.get('context', {}).get('currency', 'USD')
            )
        
        elif error_code == 'incorrect_cvc':
            return PaymentFailedError(
                "Your card's security code (CVC) is incorrect.",
                0,
                error_details.get('context', {}).get('currency', 'USD')
            )
        
        elif error_code == 'processing_error':
            return PaymentFailedError(
                "An error occurred while processing your card. Please try again.",
                0,
                error_details.get('context', {}).get('currency', 'USD')
            )
        
        else:
            return PaymentFailedError(
                card_error.user_message or "Your payment could not be processed.",
                0,
                error_details.get('context', {}).get('currency', 'USD')
            )
    
    @staticmethod
    def _handle_invalid_request_error(
        invalid_request_error: stripe.error.InvalidRequestError,
        error_details: Dict[str, Any]
    ) -> StripeError:
        """Handle Stripe invalid request errors."""
        
        param = invalid_request_error.param
        message = str(invalid_request_error)
        
        # Common invalid request scenarios
        if 'customer' in message.lower():
            return StripeError(
                "Customer not found or invalid.",
                "INVALID_CUSTOMER",
                error_details
            )
        
        elif 'subscription' in message.lower():
            return StripeError(
                "Subscription not found or invalid.",
                "INVALID_SUBSCRIPTION",
                error_details
            )
        
        elif 'payment_method' in message.lower():
            return StripeError(
                "Payment method not found or invalid.",
                "INVALID_PAYMENT_METHOD",
                error_details
            )
        
        else:
            return StripeError(
                f"Invalid request to Stripe: {message}",
                "STRIPE_INVALID_REQUEST",
                error_details
            )
    
    @staticmethod
    def handle_application_error(
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BillingError:
        """Handle application-specific errors with logging."""
        
        context = context or {}
        
        # If it's already a BillingError, just log and return
        if isinstance(error, BillingError):
            logger.warning(
                f"Billing error in {operation}: {error.message}",
                extra={
                    "error_code": error.error_code,
                    "details": error.details,
                    "context": context
                }
            )
            return error
        
        # Handle other common exceptions
        if isinstance(error, ValueError):
            logger.error(f"Value error in {operation}: {str(error)}")
            return BillingError(
                f"Invalid value in {operation}: {str(error)}",
                "INVALID_VALUE",
                {"original_error": str(error), "context": context}
            )
        
        elif isinstance(error, KeyError):
            logger.error(f"Key error in {operation}: {str(error)}")
            return BillingError(
                f"Missing required parameter in {operation}",
                "MISSING_PARAMETER",
                {"missing_key": str(error), "context": context}
            )
        
        else:
            # Generic error handling
            logger.exception(f"Unexpected error in {operation}")
            return BillingError(
                f"An unexpected error occurred in {operation}",
                "UNEXPECTED_ERROR",
                {
                    "original_error": str(error),
                    "error_type": type(error).__name__,
                    "traceback": traceback.format_exc(),
                    "context": context
                }
            )
    
    @staticmethod
    def log_successful_operation(
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log successful billing operations for monitoring."""
        
        details = details or {}
        logger.info(
            f"Successful billing operation: {operation}",
            extra={
                "operation": operation,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    @staticmethod
    def log_usage_event(
        user_id: int,
        metric: str,
        quantity: int,
        allowed: bool,
        reason: Optional[str] = None
    ) -> None:
        """Log usage events for monitoring and analytics."""
        
        log_level = logging.INFO if allowed else logging.WARNING
        message = f"Usage event: {metric} - {'allowed' if allowed else 'denied'}"
        
        logger.log(
            log_level,
            message,
            extra={
                "user_id": user_id,
                "metric": metric,
                "quantity": quantity,
                "allowed": allowed,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    @staticmethod
    def log_webhook_event(
        event_type: str,
        event_id: str,
        processed: bool,
        error: Optional[str] = None
    ) -> None:
        """Log webhook processing events."""
        
        log_level = logging.INFO if processed else logging.ERROR
        message = f"Webhook {event_type}: {'processed' if processed else 'failed'}"
        
        logger.log(
            log_level,
            message,
            extra={
                "event_type": event_type,
                "event_id": event_id,
                "processed": processed,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    @staticmethod
    def get_user_friendly_message(error: BillingError) -> str:
        """Get user-friendly error messages for API responses."""
        
        error_messages = {
            "SUBSCRIPTION_NOT_FOUND": "No active subscription found. Please subscribe to a plan.",
            "SUBSCRIPTION_ALREADY_EXISTS": "You already have an active subscription.",
            "INVALID_PLAN": "The selected plan is not valid.",
            "PLAN_CHANGE_NOT_ALLOWED": "Cannot change to this plan due to current usage.",
            "PAYMENT_METHOD_NOT_FOUND": "Payment method not found.",
            "PAYMENT_FAILED": "Payment could not be processed. Please check your payment method.",
            "CARD_DECLINED": "Your card was declined. Please try a different payment method.",
            "INSUFFICIENT_FUNDS": "Insufficient funds. Please use a different payment method.",
            "USAGE_LIMIT_EXCEEDED": "You've reached your plan's usage limit.",
            "INVALID_USAGE_METRIC": "Invalid usage metric specified.",
            "STRIPE_CONFIGURATION_ERROR": "Payment system configuration error. Please contact support.",
            "STRIPE_WEBHOOK_ERROR": "Payment system synchronization error.",
            "INVALID_WEBHOOK_SIGNATURE": "Invalid payment system signature.",
            "INVOICE_NOT_FOUND": "Invoice not found.",
            "INVOICE_ALREADY_PAID": "Invoice is already paid.",
            "CUSTOMER_NOT_FOUND": "Customer account not found.",
            "STRIPE_RATE_LIMIT": "Too many requests. Please try again later.",
            "STRIPE_CONNECTION_ERROR": "Unable to connect to payment system.",
            "STRIPE_API_ERROR": "Payment system error. Please try again.",
        }
        
        return error_messages.get(
            error.error_code,
            error.message or "An error occurred. Please try again."
        )
    
    @staticmethod
    def should_retry_operation(error: BillingError) -> bool:
        """Determine if an operation should be retried based on the error type."""
        
        retryable_codes = {
            "STRIPE_RATE_LIMIT",
            "STRIPE_CONNECTION_ERROR",
            "STRIPE_API_ERROR",
        }
        
        return error.error_code in retryable_codes
    
    @staticmethod
    def get_error_category(error: BillingError) -> str:
        """Categorize errors for monitoring and alerting."""
        
        if isinstance(error, SubscriptionError):
            return "subscription"
        elif isinstance(error, PaymentError):
            return "payment"
        elif isinstance(error, UsageError):
            return "usage"
        elif isinstance(error, WebhookError):
            return "webhook"
        elif isinstance(error, StripeError):
            return "stripe"
        else:
            return "general"


# Decorator for automatic error handling
def handle_billing_errors(operation_name: str):
    """Decorator to automatically handle billing operation errors."""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                BillingErrorHandler.log_successful_operation(
                    operation_name,
                    {"function": func.__name__}
                )
                return result
            
            except stripe.error.StripeError as e:
                raise BillingErrorHandler.handle_stripe_error(
                    e,
                    operation_name,
                    {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
                )
            
            except BillingError:
                # Re-raise billing errors as-is
                raise
            
            except Exception as e:
                raise BillingErrorHandler.handle_application_error(
                    e,
                    operation_name,
                    {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
                )
        
        return wrapper
    return decorator