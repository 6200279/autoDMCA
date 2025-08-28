"""
Celery tasks for email report generation and delivery.

This module contains Celery tasks that handle the automated generation
and delivery of comprehensive email reports to users.
"""

import logging
from typing import Dict, Any
from celery import current_app as celery_app
from app.workers.base import BaseWorkerTask, worker_task
from app.core.service_registry import container
from app.services.notifications.comprehensive_email_reports import ComprehensiveEmailReports

logger = logging.getLogger(__name__)


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.services.notifications.comprehensive_email_reports.send_daily_reports")
async def send_daily_reports(self) -> Dict[str, Any]:
    """
    Send daily email reports to all subscribed users.
    
    This task runs daily at 9:00 AM and sends personalized daily reports
    containing scan results, takedown progress, and account activity.
    """
    logger.info("Starting daily email reports task")
    
    try:
        # Get the email reports service
        email_service = await container.get(ComprehensiveEmailReports)
        
        # Send daily reports
        result = await email_service.send_daily_reports()
        
        logger.info(f"Daily email reports completed: {result}")
        return {
            "status": "success",
            "reports_sent": result.get("reports_sent", 0),
            "users_processed": result.get("users_processed", 0),
            "delivery_failures": result.get("delivery_failures", 0),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Daily email reports failed: {e}")
        raise


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.services.notifications.comprehensive_email_reports.send_weekly_reports")
async def send_weekly_reports(self) -> Dict[str, Any]:
    """
    Send weekly email reports to all subscribed users.
    
    This task runs weekly on Mondays at 10:00 AM and sends comprehensive
    weekly summaries of scanning activity, takedown success rates, and trends.
    """
    logger.info("Starting weekly email reports task")
    
    try:
        # Get the email reports service
        email_service = await container.get(ComprehensiveEmailReports)
        
        # Send weekly reports
        result = await email_service.send_weekly_reports()
        
        logger.info(f"Weekly email reports completed: {result}")
        return {
            "status": "success",
            "reports_sent": result.get("reports_sent", 0),
            "users_processed": result.get("users_processed", 0),
            "delivery_failures": result.get("delivery_failures", 0),
            "weekly_stats": result.get("weekly_stats", {})
        }
        
    except Exception as e:
        logger.error(f"Weekly email reports failed: {e}")
        raise


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.services.notifications.comprehensive_email_reports.send_monthly_reports")
async def send_monthly_reports(self) -> Dict[str, Any]:
    """
    Send monthly email reports to all subscribed users.
    
    This task runs monthly on the 1st at 11:00 AM and sends detailed
    monthly analytics reports with insights and recommendations.
    """
    logger.info("Starting monthly email reports task")
    
    try:
        # Get the email reports service
        email_service = await container.get(ComprehensiveEmailReports)
        
        # Send monthly reports
        result = await email_service.send_monthly_reports()
        
        logger.info(f"Monthly email reports completed: {result}")
        return {
            "status": "success",
            "reports_sent": result.get("reports_sent", 0),
            "users_processed": result.get("users_processed", 0),
            "delivery_failures": result.get("delivery_failures", 0),
            "monthly_insights": result.get("monthly_insights", {}),
            "performance_metrics": result.get("performance_metrics", {})
        }
        
    except Exception as e:
        logger.error(f"Monthly email reports failed: {e}")
        raise