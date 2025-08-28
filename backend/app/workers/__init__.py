"""
AutoDMCA Background Workers

This package contains all Celery background task workers for the AutoDMCA platform.
Workers are organized by functional domain for better maintainability and scaling.

Worker Modules:
- dmca: DMCA takedown processing and legal workflows
- content: Content processing, file handling, and storage
- ai: AI/ML tasks for content matching and analysis
- notifications: Email, SMS, and push notification delivery
- scanning: Platform scanning and monitoring tasks
- billing: Subscription and payment processing
- analytics: Data processing and report generation
- maintenance: System cleanup and optimization tasks
- monitoring: Health checks and system monitoring
"""

from app.core.celery_app import celery_app, celery_manager, TaskPriority, route_task

__all__ = [
    'celery_app',
    'celery_manager', 
    'TaskPriority',
    'route_task'
]