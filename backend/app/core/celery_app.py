"""
Celery application configuration for AutoDMCA background job processing.

This module sets up Celery for handling background tasks including:
- DMCA processing workflows
- Content scanning and analysis
- Email notifications and campaigns
- File processing and storage
- Data analytics and reporting
"""

import os
from typing import Any, Dict, List, Optional
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import settings

# Create Celery instance
celery_app = Celery("autodmca")

# Task routing configuration
task_routes = {
    # High priority DMCA processing tasks
    'app.workers.dmca.*': {'queue': 'dmca_high'},
    
    # Content processing and AI analysis
    'app.workers.content.*': {'queue': 'content_processing'},
    'app.workers.ai.*': {'queue': 'ai_processing'},
    
    # Email and notification tasks
    'app.workers.notifications.*': {'queue': 'notifications'},
    
    # Scanning and monitoring tasks
    'app.workers.scanning.*': {'queue': 'scanning'},
    
    # Billing and subscription tasks
    'app.workers.billing.*': {'queue': 'billing'},
    
    # Analytics and reporting (low priority)
    'app.workers.analytics.*': {'queue': 'analytics_low'},
    
    # Cleanup and maintenance tasks
    'app.workers.maintenance.*': {'queue': 'maintenance'},
}

# Queue definitions with priorities
task_queues = [
    # High priority DMCA processing
    Queue('dmca_high', Exchange('dmca_high'), routing_key='dmca_high',
          queue_arguments={'x-max-priority': 10}),
    
    # Content and AI processing
    Queue('content_processing', Exchange('content_processing'), routing_key='content_processing',
          queue_arguments={'x-max-priority': 8}),
    Queue('ai_processing', Exchange('ai_processing'), routing_key='ai_processing',
          queue_arguments={'x-max-priority': 8}),
    
    # Notifications and communications
    Queue('notifications', Exchange('notifications'), routing_key='notifications',
          queue_arguments={'x-max-priority': 7}),
    
    # Platform scanning
    Queue('scanning', Exchange('scanning'), routing_key='scanning',
          queue_arguments={'x-max-priority': 6}),
    
    # Billing and subscription management
    Queue('billing', Exchange('billing'), routing_key='billing',
          queue_arguments={'x-max-priority': 9}),
    
    # Analytics and reporting (lower priority)
    Queue('analytics_low', Exchange('analytics_low'), routing_key='analytics_low',
          queue_arguments={'x-max-priority': 3}),
    
    # Maintenance and cleanup tasks
    Queue('maintenance', Exchange('maintenance'), routing_key='maintenance',
          queue_arguments={'x-max-priority': 1}),
    
    # Default queue for unspecified tasks
    Queue('default', Exchange('default'), routing_key='default',
          queue_arguments={'x-max-priority': 5}),
]

# Celery configuration
celery_config = {
    # Broker settings
    'broker_url': settings.REDIS_URL or 'redis://localhost:6379/0',
    'result_backend': settings.REDIS_URL or 'redis://localhost:6379/0',
    
    # Task routing and queues
    'task_routes': task_routes,
    'task_queues': task_queues,
    'task_default_queue': 'default',
    'task_default_exchange': 'default',
    'task_default_exchange_type': 'direct',
    'task_default_routing_key': 'default',
    
    # Task execution settings
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'result_expires': 3600,  # 1 hour
    'timezone': 'UTC',
    'enable_utc': True,
    
    # Task acknowledgment settings
    'task_acks_late': True,
    'worker_prefetch_multiplier': 1,
    
    # Error handling
    'task_reject_on_worker_lost': True,
    'task_ignore_result': False,
    
    # Monitoring and logging
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    
    # Performance settings
    'worker_max_tasks_per_child': 1000,
    'worker_disable_rate_limits': False,
    
    # Security settings
    'worker_hijack_root_logger': False,
    'worker_log_color': False,
    
    # Database connection pool settings for tasks
    'database_engine_options': {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
    }
}

# Periodic task schedule (cron-like scheduling)
beat_schedule = {
    # Daily tasks
    'daily-cleanup': {
        'task': 'app.workers.maintenance.cleanup_expired_data',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
        'options': {'queue': 'maintenance'}
    },
    
    # Hourly scanning for premium customers
    'hourly-priority-scans': {
        'task': 'app.workers.scanning.run_priority_scans',
        'schedule': crontab(minute=0),  # Every hour
        'options': {'queue': 'scanning'}
    },
    
    # Generate daily reports
    'daily-analytics': {
        'task': 'app.workers.analytics.generate_daily_reports',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM daily
        'options': {'queue': 'analytics_low'}
    },
    
    # Check subscription statuses
    'subscription-status-check': {
        'task': 'app.workers.billing.check_subscription_statuses',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM daily
        'options': {'queue': 'billing'}
    },
    
    # Weekly maintenance tasks
    'weekly-maintenance': {
        'task': 'app.workers.maintenance.weekly_cleanup',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),  # Mondays at 1:00 AM
        'options': {'queue': 'maintenance'}
    },
    
    # Health checks every 15 minutes
    'health-check': {
        'task': 'app.workers.monitoring.system_health_check',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'queue': 'default'}
    },
    
    # New service scheduled tasks
    'daily-scan-scheduling': {
        'task': 'app.services.scanning.automated_scheduler.schedule_all_daily_scans',
        'schedule': crontab(hour=1, minute=30),  # 1:30 AM daily
        'options': {'queue': 'scanning'}
    },
    
    'continuous-monitoring-scheduling': {
        'task': 'app.services.scanning.automated_scheduler.schedule_continuous_monitoring', 
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'options': {'queue': 'scanning'}
    },
    
    'send-daily-email-reports': {
        'task': 'app.services.notifications.comprehensive_email_reports.send_daily_reports',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
        'options': {'queue': 'notifications'}
    },
    
    'send-weekly-email-reports': {
        'task': 'app.services.notifications.comprehensive_email_reports.send_weekly_reports', 
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Mondays at 10:00 AM
        'options': {'queue': 'notifications'}
    },
    
    'send-monthly-email-reports': {
        'task': 'app.services.notifications.comprehensive_email_reports.send_monthly_reports',
        'schedule': crontab(hour=11, minute=0, day=1),  # 1st of month at 11:00 AM
        'options': {'queue': 'notifications'}
    }
}

# Apply configuration
celery_app.config_from_object(celery_config)
celery_app.conf.beat_schedule = beat_schedule

# Auto-discover tasks from all worker modules
celery_app.autodiscover_tasks([
    'app.workers.dmca',
    'app.workers.content',
    'app.workers.ai',
    'app.workers.notifications',
    'app.workers.scanning',
    'app.workers.billing',
    'app.workers.analytics',
    'app.workers.maintenance',
    'app.workers.monitoring',
    # New worker modules
    'app.workers.notifications.email_reports',
    'app.workers.scanning.scan_scheduler',
    'app.workers.analytics.report_generator',
    'app.workers.maintenance.cleanup_tasks',
    'app.workers.billing.subscription_manager',
])


class CeleryManager:
    """Manager class for Celery operations and monitoring."""
    
    def __init__(self, celery_instance: Celery = celery_app):
        self.celery = celery_instance
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """Get list of currently active tasks."""
        inspect = self.celery.control.inspect()
        return inspect.active() or {}
    
    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """Get list of scheduled tasks."""
        inspect = self.celery.control.inspect()
        return inspect.scheduled() or {}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        inspect = self.celery.control.inspect()
        return inspect.stats() or {}
    
    def purge_queue(self, queue_name: str) -> int:
        """Purge all tasks from a specific queue."""
        return self.celery.control.purge_queue(queue_name)
    
    def cancel_task(self, task_id: str) -> None:
        """Cancel a specific task by ID."""
        self.celery.control.revoke(task_id, terminate=True)
    
    def get_queue_lengths(self) -> Dict[str, int]:
        """Get the number of tasks in each queue."""
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL or 'redis://localhost:6379/0')
        
        queue_lengths = {}
        for queue in task_queues:
            queue_name = queue.name
            length = redis_client.llen(f'celery:{queue_name}')
            queue_lengths[queue_name] = length
        
        return queue_lengths


# Global manager instance
celery_manager = CeleryManager()

# Task priority constants
class TaskPriority:
    """Task priority levels for queue routing."""
    CRITICAL = 10    # DMCA takedowns, billing issues
    HIGH = 8         # Content processing, AI analysis
    NORMAL = 5       # General tasks
    LOW = 3          # Analytics, reporting
    MAINTENANCE = 1  # Cleanup, maintenance


def route_task(task_name: str, priority: int = TaskPriority.NORMAL) -> Dict[str, Any]:
    """Route a task to the appropriate queue based on name and priority."""
    routing = {'priority': priority}
    
    # Route based on task name patterns
    if 'dmca' in task_name.lower():
        routing['queue'] = 'dmca_high'
        routing['priority'] = TaskPriority.CRITICAL
    elif 'content' in task_name.lower():
        routing['queue'] = 'content_processing'
        routing['priority'] = TaskPriority.HIGH
    elif 'ai' in task_name.lower():
        routing['queue'] = 'ai_processing'
        routing['priority'] = TaskPriority.HIGH
    elif 'notification' in task_name.lower() or 'email' in task_name.lower():
        routing['queue'] = 'notifications'
        routing['priority'] = TaskPriority.HIGH
    elif 'scan' in task_name.lower():
        routing['queue'] = 'scanning'
        routing['priority'] = TaskPriority.NORMAL
    elif 'billing' in task_name.lower() or 'payment' in task_name.lower():
        routing['queue'] = 'billing'
        routing['priority'] = TaskPriority.CRITICAL
    elif 'analytics' in task_name.lower() or 'report' in task_name.lower():
        routing['queue'] = 'analytics_low'
        routing['priority'] = TaskPriority.LOW
    elif 'maintenance' in task_name.lower() or 'cleanup' in task_name.lower():
        routing['queue'] = 'maintenance'
        routing['priority'] = TaskPriority.MAINTENANCE
    else:
        routing['queue'] = 'default'
    
    return routing


# Export for use in other modules
__all__ = [
    'celery_app',
    'celery_manager',
    'TaskPriority',
    'route_task',
    'CeleryManager'
]