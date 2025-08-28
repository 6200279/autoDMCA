"""
Celery tasks for subscription and billing management.

This module contains Celery tasks that handle subscription status checks,
payment processing, and billing-related operations.
"""

import logging
from typing import Dict, Any
from celery import current_app as celery_app
from app.workers.base import BaseWorkerTask, worker_task
from app.core.service_registry import container
from app.services.billing.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.workers.billing.check_subscription_statuses")
async def check_subscription_statuses(self) -> Dict[str, Any]:
    """
    Check and update subscription statuses for all users.
    
    This task runs daily at 8:00 AM and verifies subscription statuses
    with Stripe, handles failed payments, and manages subscription lifecycle.
    """
    logger.info("Starting subscription status check task")
    
    try:
        # Get the subscription service
        subscription_service = await container.get(SubscriptionService)
        
        # Check all subscription statuses
        result = await subscription_service.check_all_subscription_statuses()
        
        logger.info(f"Subscription status check completed: {result}")
        return {
            "status": "success",
            "subscriptions_checked": result.get("subscriptions_checked", 0),
            "subscriptions_updated": result.get("subscriptions_updated", 0),
            "failed_payments": result.get("failed_payments", 0),
            "cancellations_processed": result.get("cancellations_processed", 0),
            "renewals_processed": result.get("renewals_processed", 0)
        }
        
    except Exception as e:
        logger.error(f"Subscription status check failed: {e}")
        raise