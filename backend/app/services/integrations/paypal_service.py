"""
PayPal Payment Service Integration

Provides PayPal payment processing as an alternative to Stripe:
- Payment processing and checkout
- Subscription management
- Webhook handling
- Refunds and disputes
- PayPal Express Checkout integration
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
import hmac
import hashlib
import base64

try:
    import paypalrestsdk
    from paypalrestsdk import Payment, BillingPlan, BillingAgreement, WebProfile
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class PayPalError(Exception):
    """PayPal service specific errors"""
    pass


class PayPalService:
    """
    PayPal payment service providing:
    - One-time payments
    - Recurring subscriptions
    - Refunds and disputes
    - Webhook validation
    - Express checkout
    - Invoice generation
    """
    
    def __init__(self):
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', None)
        self.webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', None)
        self.environment = getattr(settings, 'PAYPAL_ENVIRONMENT', 'sandbox')  # 'sandbox' or 'live'
        
        self.available = False
        
        if not PAYPAL_AVAILABLE:
            logger.warning("PayPal SDK not available")
            return
        
        if not self.client_id or not self.client_secret:
            logger.warning("PayPal credentials not configured")
            return
        
        try:
            # Configure PayPal SDK
            paypalrestsdk.configure({
                "mode": self.environment,  # sandbox or live
                "client_id": self.client_id,
                "client_secret": self.client_secret
            })
            
            self.available = True
            logger.info(f"PayPal service initialized successfully in {self.environment} mode")
            
        except Exception as e:
            logger.error(f"Failed to initialize PayPal service: {e}")
            self.available = False
        
        # Subscription plan configuration
        self.subscription_plans = {
            'basic': {
                'name': 'Basic Plan',
                'description': 'Basic content protection plan',
                'monthly_amount': '49.00',
                'yearly_amount': '490.00',  # 2 months free
                'currency': 'USD'
            },
            'professional': {
                'name': 'Professional Plan', 
                'description': 'Professional content protection plan',
                'monthly_amount': '99.00',
                'yearly_amount': '990.00',  # 2 months free
                'currency': 'USD'
            }
        }
    
    async def create_payment(
        self,
        amount: Union[str, Decimal],
        currency: str = 'USD',
        description: str = 'Payment',
        return_url: str = None,
        cancel_url: str = None,
        items: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a PayPal payment.
        
        Args:
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            description: Payment description
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancelled payment
            items: List of items being purchased
            metadata: Custom metadata
            
        Returns:
            Dict with payment details and approval URL
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            # Default URLs
            if not return_url:
                return_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/payment/success"
            if not cancel_url:
                cancel_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/payment/cancelled"
            
            # Prepare items
            payment_items = []
            if items:
                for item in items:
                    payment_items.append({
                        "name": item.get('name', 'Item'),
                        "sku": item.get('sku', 'item'),
                        "price": str(item.get('price', amount)),
                        "currency": currency,
                        "quantity": item.get('quantity', 1)
                    })
            else:
                payment_items.append({
                    "name": description,
                    "sku": "service",
                    "price": str(amount),
                    "currency": currency,
                    "quantity": 1
                })
            
            # Create payment object
            payment_data = {
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": return_url,
                    "cancel_url": cancel_url
                },
                "transactions": [{
                    "item_list": {
                        "items": payment_items
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }]
            }
            
            # Add custom metadata if provided
            if metadata:
                payment_data["transactions"][0]["custom"] = json.dumps(metadata)
            
            # Create payment
            payment = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: Payment(payment_data)
            )
            
            # Execute payment creation
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                payment.create
            )
            
            if success:
                # Find approval URL
                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                result = {
                    'success': True,
                    'payment_id': payment.id,
                    'approval_url': approval_url,
                    'amount': str(amount),
                    'currency': currency,
                    'status': payment.state,
                    'created_at': payment.create_time
                }
                
                logger.info(f"PayPal payment created: {payment.id}")
                return result
            else:
                logger.error(f"PayPal payment creation failed: {payment.error}")
                return {
                    'success': False,
                    'error': payment.error,
                    'details': getattr(payment, 'error', {})
                }
        
        except Exception as e:
            logger.error(f"PayPal payment creation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_payment(
        self,
        payment_id: str,
        payer_id: str
    ) -> Dict[str, Any]:
        """
        Execute an approved PayPal payment.
        
        Args:
            payment_id: PayPal payment ID
            payer_id: Payer ID from PayPal
            
        Returns:
            Dict with execution results
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            # Find the payment
            payment = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Payment.find(payment_id)
            )
            
            # Execute the payment
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: payment.execute({"payer_id": payer_id})
            )
            
            if success:
                result = {
                    'success': True,
                    'payment_id': payment.id,
                    'state': payment.state,
                    'payer_id': payer_id,
                    'executed_at': datetime.utcnow().isoformat()
                }
                
                # Extract transaction details
                if payment.transactions:
                    transaction = payment.transactions[0]
                    if transaction.related_resources:
                        sale = transaction.related_resources[0].sale
                        result.update({
                            'transaction_id': sale.id,
                            'amount': sale.amount.total,
                            'currency': sale.amount.currency,
                            'transaction_fee': getattr(sale.transaction_fee, 'value', None) if hasattr(sale, 'transaction_fee') else None
                        })
                
                logger.info(f"PayPal payment executed successfully: {payment_id}")
                return result
            else:
                logger.error(f"PayPal payment execution failed: {payment.error}")
                return {
                    'success': False,
                    'error': payment.error
                }
        
        except Exception as e:
            logger.error(f"PayPal payment execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_billing_plan(
        self,
        plan_name: str,
        description: str,
        amount: str,
        currency: str = 'USD',
        interval: str = 'MONTH',
        interval_count: int = 1,
        cycles: int = 0  # 0 = infinite
    ) -> Dict[str, Any]:
        """
        Create a PayPal billing plan for subscriptions.
        
        Args:
            plan_name: Name of the billing plan
            description: Plan description
            amount: Payment amount per billing cycle
            currency: Currency code
            interval: Billing interval (MONTH, WEEK, DAY, YEAR)
            interval_count: Number of intervals between payments
            cycles: Number of billing cycles (0 = infinite)
            
        Returns:
            Dict with billing plan details
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            billing_plan_data = {
                "name": plan_name,
                "description": description,
                "type": "INFINITE" if cycles == 0 else "FIXED",
                "payment_definitions": [{
                    "name": f"{plan_name} Payment",
                    "type": "REGULAR",
                    "frequency": interval,
                    "frequency_interval": str(interval_count),
                    "cycles": str(cycles) if cycles > 0 else "0",
                    "amount": {
                        "currency": currency,
                        "value": amount
                    }
                }],
                "merchant_preferences": {
                    "setup_fee": {
                        "currency": currency,
                        "value": "0"
                    },
                    "return_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/subscription/success",
                    "cancel_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/subscription/cancelled",
                    "auto_bill_amount": "YES",
                    "initial_fail_amount_action": "CONTINUE",
                    "max_fail_attempts": "3"
                }
            }
            
            # Create billing plan
            billing_plan = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: BillingPlan(billing_plan_data)
            )
            
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                billing_plan.create
            )
            
            if success:
                # Activate the plan
                patch_data = [{
                    "op": "replace",
                    "path": "/",
                    "value": {
                        "state": "ACTIVE"
                    }
                }]
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: billing_plan.replace(patch_data)
                )
                
                result = {
                    'success': True,
                    'plan_id': billing_plan.id,
                    'name': plan_name,
                    'state': 'ACTIVE',
                    'amount': amount,
                    'currency': currency,
                    'interval': interval,
                    'created_at': billing_plan.create_time
                }
                
                logger.info(f"PayPal billing plan created: {billing_plan.id}")
                return result
            else:
                logger.error(f"PayPal billing plan creation failed: {billing_plan.error}")
                return {
                    'success': False,
                    'error': billing_plan.error
                }
        
        except Exception as e:
            logger.error(f"PayPal billing plan creation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_billing_agreement(
        self,
        plan_id: str,
        agreement_name: str,
        description: str,
        start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a billing agreement for subscription.
        
        Args:
            plan_id: PayPal billing plan ID
            agreement_name: Name for the agreement
            description: Agreement description
            start_date: When the subscription should start
            
        Returns:
            Dict with billing agreement details and approval URL
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            # Default start date to now + 1 minute
            if not start_date:
                start_date = datetime.utcnow() + timedelta(minutes=1)
            
            billing_agreement_data = {
                "name": agreement_name,
                "description": description,
                "start_date": start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "plan": {
                    "id": plan_id
                },
                "payer": {
                    "payment_method": "paypal"
                }
            }
            
            # Create billing agreement
            billing_agreement = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: BillingAgreement(billing_agreement_data)
            )
            
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                billing_agreement.create
            )
            
            if success:
                # Find approval URL
                approval_url = None
                for link in billing_agreement.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                result = {
                    'success': True,
                    'agreement_id': billing_agreement.id,
                    'approval_url': approval_url,
                    'name': agreement_name,
                    'plan_id': plan_id,
                    'start_date': start_date.isoformat(),
                    'state': billing_agreement.state,
                    'created_at': billing_agreement.create_time
                }
                
                logger.info(f"PayPal billing agreement created: {billing_agreement.id}")
                return result
            else:
                logger.error(f"PayPal billing agreement creation failed: {billing_agreement.error}")
                return {
                    'success': False,
                    'error': billing_agreement.error
                }
        
        except Exception as e:
            logger.error(f"PayPal billing agreement creation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_billing_agreement(
        self,
        payment_token: str
    ) -> Dict[str, Any]:
        """
        Execute (activate) a billing agreement after customer approval.
        
        Args:
            payment_token: Token received from PayPal after approval
            
        Returns:
            Dict with executed agreement details
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            # Execute the billing agreement
            billing_agreement = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: BillingAgreement.execute(payment_token)
            )
            
            if billing_agreement and not hasattr(billing_agreement, 'error'):
                result = {
                    'success': True,
                    'agreement_id': billing_agreement.id,
                    'state': billing_agreement.state,
                    'payer_info': {
                        'email': billing_agreement.payer.payer_info.email,
                        'first_name': billing_agreement.payer.payer_info.first_name,
                        'last_name': billing_agreement.payer.payer_info.last_name,
                        'payer_id': billing_agreement.payer.payer_info.payer_id
                    },
                    'executed_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"PayPal billing agreement executed: {billing_agreement.id}")
                return result
            else:
                error_msg = getattr(billing_agreement, 'error', 'Unknown error')
                logger.error(f"PayPal billing agreement execution failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"PayPal billing agreement execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cancel_billing_agreement(
        self,
        agreement_id: str,
        note: str = "Cancellation requested by user"
    ) -> Dict[str, Any]:
        """
        Cancel a billing agreement (subscription).
        
        Args:
            agreement_id: PayPal billing agreement ID
            note: Cancellation note
            
        Returns:
            Dict with cancellation results
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            # Find the billing agreement
            billing_agreement = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: BillingAgreement.find(agreement_id)
            )
            
            # Cancel the agreement
            cancel_data = {
                "note": note
            }
            
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: billing_agreement.cancel(cancel_data)
            )
            
            if success:
                result = {
                    'success': True,
                    'agreement_id': agreement_id,
                    'cancelled_at': datetime.utcnow().isoformat(),
                    'note': note
                }
                
                logger.info(f"PayPal billing agreement cancelled: {agreement_id}")
                return result
            else:
                logger.error(f"PayPal billing agreement cancellation failed: {billing_agreement.error}")
                return {
                    'success': False,
                    'error': getattr(billing_agreement, 'error', 'Cancellation failed')
                }
        
        except Exception as e:
            logger.error(f"PayPal billing agreement cancellation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_refund(
        self,
        sale_id: str,
        amount: Optional[str] = None,
        currency: str = 'USD',
        reason: str = 'Customer request'
    ) -> Dict[str, Any]:
        """
        Process a refund for a completed payment.
        
        Args:
            sale_id: PayPal sale transaction ID
            amount: Amount to refund (None = full refund)
            currency: Currency code
            reason: Refund reason
            
        Returns:
            Dict with refund results
        """
        if not self.available:
            return {
                'error': 'PayPal service not available',
                'success': False
            }
        
        try:
            from paypalrestsdk import Sale, Refund
            
            # Find the sale
            sale = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Sale.find(sale_id)
            )
            
            # Prepare refund data
            refund_data = {
                "reason": reason
            }
            
            if amount:
                refund_data["amount"] = {
                    "total": str(amount),
                    "currency": currency
                }
            
            # Process the refund
            refund = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sale.refund(refund_data)
            )
            
            if refund and not hasattr(refund, 'error'):
                result = {
                    'success': True,
                    'refund_id': refund.id,
                    'sale_id': sale_id,
                    'amount': refund.amount.total,
                    'currency': refund.amount.currency,
                    'state': refund.state,
                    'reason': reason,
                    'created_at': refund.create_time
                }
                
                logger.info(f"PayPal refund processed: {refund.id}")
                return result
            else:
                error_msg = getattr(refund, 'error', 'Refund failed')
                logger.error(f"PayPal refund failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"PayPal refund processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_payment_details(self, payment_id: str) -> Dict[str, Any]:
        """Get details of a PayPal payment."""
        if not self.available:
            return {
                'error': 'PayPal service not available'
            }
        
        try:
            payment = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Payment.find(payment_id)
            )
            
            if payment and not hasattr(payment, 'error'):
                return {
                    'payment_id': payment.id,
                    'state': payment.state,
                    'intent': payment.intent,
                    'created_at': payment.create_time,
                    'updated_at': payment.update_time,
                    'transactions': [
                        {
                            'amount': tx.amount.__dict__,
                            'description': tx.description,
                            'custom': tx.custom,
                            'related_resources': [res.__dict__ for res in tx.related_resources] if tx.related_resources else []
                        } for tx in payment.transactions
                    ]
                }
            else:
                return {
                    'error': getattr(payment, 'error', 'Payment not found')
                }
        
        except Exception as e:
            logger.error(f"Error getting PayPal payment details: {e}")
            return {
                'error': str(e)
            }
    
    async def validate_webhook(
        self,
        webhook_body: str,
        webhook_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate PayPal webhook signature.
        
        Args:
            webhook_body: Raw webhook body
            webhook_headers: Webhook headers
            
        Returns:
            Dict with validation results and event data
        """
        if not self.available or not self.webhook_id:
            return {
                'valid': False,
                'error': 'PayPal webhook validation not available'
            }
        
        try:
            from paypalrestsdk import WebhookEvent
            
            # Get required headers
            auth_algo = webhook_headers.get('PAYPAL-AUTH-ALGO')
            transmission_id = webhook_headers.get('PAYPAL-TRANSMISSION-ID')
            cert_id = webhook_headers.get('PAYPAL-CERT-ID')
            transmission_sig = webhook_headers.get('PAYPAL-TRANSMISSION-SIG')
            transmission_time = webhook_headers.get('PAYPAL-TRANSMISSION-TIME')
            
            if not all([auth_algo, transmission_id, cert_id, transmission_sig, transmission_time]):
                return {
                    'valid': False,
                    'error': 'Missing required webhook headers'
                }
            
            # Validate webhook event
            webhook_event_data = {
                "auth_algo": auth_algo,
                "transmission_id": transmission_id,
                "cert_id": cert_id,
                "transmission_sig": transmission_sig,
                "transmission_time": transmission_time,
                "webhook_id": self.webhook_id,
                "webhook_event": json.loads(webhook_body)
            }
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: WebhookEvent.verify(webhook_event_data)
            )
            
            if result:
                event_data = json.loads(webhook_body)
                return {
                    'valid': True,
                    'event_type': event_data.get('event_type'),
                    'resource_type': event_data.get('resource_type'),
                    'event_data': event_data,
                    'validated_at': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'valid': False,
                    'error': 'Webhook signature validation failed'
                }
        
        except Exception as e:
            logger.error(f"PayPal webhook validation error: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check PayPal service health."""
        try:
            if not self.available:
                return {
                    'service': 'paypal',
                    'status': 'unavailable',
                    'message': 'PayPal SDK not available or credentials not configured'
                }
            
            return {
                'service': 'paypal',
                'status': 'healthy',
                'environment': self.environment,
                'client_id_configured': bool(self.client_id),
                'webhook_configured': bool(self.webhook_id),
                'features_available': [
                    'payments',
                    'subscriptions',
                    'refunds',
                    'webhooks'
                ]
            }
            
        except Exception as e:
            return {
                'service': 'paypal',
                'status': 'unhealthy',
                'error': str(e)
            }


# Create singleton instance
paypal_service = PayPalService()


# Convenience functions
async def create_subscription_checkout(
    plan_type: str,
    interval: str = 'monthly',
    user_email: str = None
) -> Dict[str, Any]:
    """Create PayPal subscription checkout for standard plans."""
    if plan_type not in paypal_service.subscription_plans:
        return {
            'success': False,
            'error': f'Unknown plan type: {plan_type}'
        }
    
    plan_config = paypal_service.subscription_plans[plan_type]
    amount = plan_config['monthly_amount'] if interval == 'monthly' else plan_config['yearly_amount']
    
    # Create billing plan
    billing_interval = 'MONTH' if interval == 'monthly' else 'YEAR'
    plan_result = await paypal_service.create_billing_plan(
        plan_name=f"{plan_config['name']} - {interval.title()}",
        description=plan_config['description'],
        amount=amount,
        currency=plan_config['currency'],
        interval=billing_interval
    )
    
    if not plan_result.get('success'):
        return plan_result
    
    # Create billing agreement
    agreement_result = await paypal_service.create_billing_agreement(
        plan_id=plan_result['plan_id'],
        agreement_name=f"{plan_config['name']} Subscription",
        description=f"Subscription to {plan_config['name']}"
    )
    
    return agreement_result


async def process_one_time_payment(
    amount: Union[str, Decimal],
    description: str,
    user_email: str = None,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Process a one-time payment via PayPal."""
    return await paypal_service.create_payment(
        amount=amount,
        description=description,
        metadata=metadata
    )


async def handle_subscription_webhook(
    event_type: str,
    event_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle PayPal subscription webhook events."""
    logger.info(f"Processing PayPal webhook event: {event_type}")
    
    # Handle different subscription events
    if event_type == 'BILLING.SUBSCRIPTION.CREATED':
        # Subscription created
        return {
            'processed': True,
            'action': 'subscription_created',
            'agreement_id': event_data.get('resource', {}).get('id')
        }
    
    elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
        # Subscription activated
        return {
            'processed': True,
            'action': 'subscription_activated',
            'agreement_id': event_data.get('resource', {}).get('id')
        }
    
    elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
        # Subscription cancelled
        return {
            'processed': True,
            'action': 'subscription_cancelled',
            'agreement_id': event_data.get('resource', {}).get('id')
        }
    
    elif event_type == 'PAYMENT.SALE.COMPLETED':
        # Payment completed
        return {
            'processed': True,
            'action': 'payment_completed',
            'sale_id': event_data.get('resource', {}).get('id')
        }
    
    else:
        return {
            'processed': False,
            'message': f'Unhandled event type: {event_type}'
        }