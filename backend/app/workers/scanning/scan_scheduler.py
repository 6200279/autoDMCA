"""
Celery tasks for automated scan scheduling.

This module contains Celery tasks that handle the scheduling of automated
content scans for the AutoDMCA platform.
"""

import logging
from typing import Dict, Any
from celery import current_app as celery_app
from app.workers.base import BaseWorkerTask, worker_task
from app.core.service_registry import container
from app.services.scanning.automated_scheduler import AutomatedScanScheduler

logger = logging.getLogger(__name__)


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.services.scanning.automated_scheduler.schedule_all_daily_scans")
async def schedule_all_daily_scans(self) -> Dict[str, Any]:
    """
    Schedule all daily scans for active users.
    
    This task runs daily at 1:30 AM and schedules content scans for all
    users who have daily scanning enabled in their subscription.
    """
    logger.info("Starting daily scan scheduling task")
    
    try:
        # Get the automated scan scheduler service
        scheduler = await container.get(AutomatedScanScheduler)
        
        # Schedule all daily scans
        result = await scheduler.schedule_all_daily_scans()
        
        logger.info(f"Daily scan scheduling completed: {result}")
        return {
            "status": "success",
            "scans_scheduled": result.get("scans_scheduled", 0),
            "users_processed": result.get("users_processed", 0),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Daily scan scheduling failed: {e}")
        raise


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.services.scanning.automated_scheduler.schedule_continuous_monitoring")
async def schedule_continuous_monitoring(self) -> Dict[str, Any]:
    """
    Schedule continuous monitoring tasks.
    
    This task runs every 30 minutes and schedules immediate scans for
    high-priority content and premium users with continuous monitoring enabled.
    """
    logger.info("Starting continuous monitoring scheduling task")
    
    try:
        # Get the automated scan scheduler service
        scheduler = await container.get(AutomatedScanScheduler)
        
        # Schedule continuous monitoring
        result = await scheduler.schedule_continuous_monitoring()
        
        logger.info(f"Continuous monitoring scheduling completed: {result}")
        return {
            "status": "success",
            "monitoring_tasks_scheduled": result.get("monitoring_tasks_scheduled", 0),
            "priority_scans_scheduled": result.get("priority_scans_scheduled", 0),
            "users_processed": result.get("users_processed", 0)
        }
        
    except Exception as e:
        logger.error(f"Continuous monitoring scheduling failed: {e}")
        raise


@celery_app.task(base=BaseWorkerTask, bind=True, name="app.workers.scanning.run_priority_scans")
async def run_priority_scans(self) -> Dict[str, Any]:
    """
    Run high-priority content scans for premium users.
    
    This task runs hourly and processes high-priority scan requests
    for premium subscribers and urgent content protection needs.
    """
    logger.info("Starting priority scans task")
    
    try:
        # Get the automated scan scheduler service
        scheduler = await container.get(AutomatedScanScheduler)
        
        # Run priority scans
        result = await scheduler.run_priority_scans()
        
        logger.info(f"Priority scans completed: {result}")
        return {
            "status": "success",
            "scans_executed": result.get("scans_executed", 0),
            "matches_found": result.get("matches_found", 0),
            "takedowns_initiated": result.get("takedowns_initiated", 0)
        }
        
    except Exception as e:
        logger.error(f"Priority scans failed: {e}")
        raise