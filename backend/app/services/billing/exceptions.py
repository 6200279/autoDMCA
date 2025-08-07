"""
Billing-specific exceptions for comprehensive error handling.
"""


class BillingError(Exception):
    """Base exception for billing-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "BILLING_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class SubscriptionError(BillingError):
    """Exception for subscription-related errors."""
    pass


class PaymentError(BillingError):
    """Exception for payment-related errors."""
    pass


class UsageError(BillingError):
    """Exception for usage-related errors."""
    pass


class WebhookError(BillingError):
    """Exception for webhook processing errors."""
    pass


class StripeError(BillingError):
    """Exception for Stripe-related errors."""
    pass


# Specific subscription errors
class SubscriptionNotFoundError(SubscriptionError):
    """Subscription not found."""
    
    def __init__(self, user_id: int):
        super().__init__(
            f"No subscription found for user {user_id}",
            "SUBSCRIPTION_NOT_FOUND",
            {"user_id": user_id}
        )


class SubscriptionAlreadyExistsError(SubscriptionError):
    """User already has an active subscription."""
    
    def __init__(self, user_id: int, current_status: str):
        super().__init__(
            f"User {user_id} already has an active subscription with status: {current_status}",
            "SUBSCRIPTION_ALREADY_EXISTS",
            {"user_id": user_id, "current_status": current_status}
        )


class InvalidPlanError(SubscriptionError):
    """Invalid subscription plan."""
    
    def __init__(self, plan: str):
        super().__init__(
            f"Invalid subscription plan: {plan}",
            "INVALID_PLAN",
            {"plan": plan}
        )


class PlanChangeNotAllowedError(SubscriptionError):
    """Plan change not allowed due to usage constraints."""
    
    def __init__(self, reason: str, current_plan: str, target_plan: str):
        super().__init__(
            f"Cannot change from {current_plan} to {target_plan}: {reason}",
            "PLAN_CHANGE_NOT_ALLOWED",
            {"current_plan": current_plan, "target_plan": target_plan, "reason": reason}
        )


# Payment-related errors
class PaymentMethodNotFoundError(PaymentError):
    """Payment method not found."""
    
    def __init__(self, payment_method_id: str):
        super().__init__(
            f"Payment method not found: {payment_method_id}",
            "PAYMENT_METHOD_NOT_FOUND",
            {"payment_method_id": payment_method_id}
        )


class PaymentFailedError(PaymentError):
    """Payment failed."""
    
    def __init__(self, reason: str, amount: float, currency: str = "USD"):
        super().__init__(
            f"Payment failed: {reason}",
            "PAYMENT_FAILED",
            {"reason": reason, "amount": amount, "currency": currency}
        )


class InsufficientFundsError(PaymentError):
    """Insufficient funds for payment."""
    
    def __init__(self, amount: float, currency: str = "USD"):
        super().__init__(
            f"Insufficient funds for payment of {amount} {currency}",
            "INSUFFICIENT_FUNDS",
            {"amount": amount, "currency": currency}
        )


class CardDeclinedError(PaymentError):
    """Credit card was declined."""
    
    def __init__(self, reason: str = None):
        message = f"Credit card declined: {reason}" if reason else "Credit card declined"
        super().__init__(
            message,
            "CARD_DECLINED",
            {"reason": reason}
        )


# Usage-related errors
class UsageLimitExceededError(UsageError):
    """Usage limit exceeded."""
    
    def __init__(self, metric: str, current: int, limit: int):
        super().__init__(
            f"{metric} limit exceeded: {current}/{limit}",
            "USAGE_LIMIT_EXCEEDED",
            {"metric": metric, "current": current, "limit": limit}
        )


class InvalidUsageMetricError(UsageError):
    """Invalid usage metric."""
    
    def __init__(self, metric: str):
        super().__init__(
            f"Invalid usage metric: {metric}",
            "INVALID_USAGE_METRIC",
            {"metric": metric}
        )


# Stripe-specific errors
class StripeConfigurationError(StripeError):
    """Stripe configuration error."""
    
    def __init__(self, message: str):
        super().__init__(
            f"Stripe configuration error: {message}",
            "STRIPE_CONFIGURATION_ERROR"
        )


class StripeWebhookError(WebhookError):
    """Stripe webhook processing error."""
    
    def __init__(self, event_type: str, reason: str):
        super().__init__(
            f"Failed to process Stripe webhook event {event_type}: {reason}",
            "STRIPE_WEBHOOK_ERROR",
            {"event_type": event_type, "reason": reason}
        )


class InvalidWebhookSignatureError(WebhookError):
    """Invalid webhook signature."""
    
    def __init__(self):
        super().__init__(
            "Invalid webhook signature",
            "INVALID_WEBHOOK_SIGNATURE"
        )


# Invoice-related errors
class InvoiceError(BillingError):
    """Exception for invoice-related errors."""
    pass


class InvoiceNotFoundError(InvoiceError):
    """Invoice not found."""
    
    def __init__(self, invoice_id: str):
        super().__init__(
            f"Invoice not found: {invoice_id}",
            "INVOICE_NOT_FOUND",
            {"invoice_id": invoice_id}
        )


class InvoiceAlreadyPaidError(InvoiceError):
    """Invoice already paid."""
    
    def __init__(self, invoice_id: str):
        super().__init__(
            f"Invoice {invoice_id} is already paid",
            "INVOICE_ALREADY_PAID",
            {"invoice_id": invoice_id}
        )


# Customer-related errors
class CustomerError(BillingError):
    """Exception for customer-related errors."""
    pass


class CustomerNotFoundError(CustomerError):
    """Customer not found in Stripe."""
    
    def __init__(self, customer_id: str):
        super().__init__(
            f"Customer not found in Stripe: {customer_id}",
            "CUSTOMER_NOT_FOUND",
            {"customer_id": customer_id}
        )


# Proration errors
class ProrationError(BillingError):
    """Exception for proration calculation errors."""
    pass


class InvalidProrationPeriodError(ProrationError):
    """Invalid proration period."""
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            f"Invalid proration period: {start_date} to {end_date}",
            "INVALID_PRORATION_PERIOD",
            {"start_date": start_date, "end_date": end_date}
        )