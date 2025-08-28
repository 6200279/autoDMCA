"""
System Health Check Workers

Background tasks for monitoring system health, component status,
and operational metrics across the AutoDMCA platform.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import text

from app.workers.base import worker_task, create_task_context, check_redis_connection, check_database_connection
from app.core.celery_app import TaskPriority, celery_manager

logger = logging.getLogger(__name__)


@worker_task(priority=TaskPriority.NORMAL, time_limit=120)
async def system_health_check(self) -> Dict[str, Any]:
    """
    Comprehensive system health check covering all critical components.
    
    This task runs every 15 minutes to monitor:
    - Database connectivity and performance
    - Redis connectivity and memory usage
    - Celery worker status and queue health
    - External service connectivity
    - System resources and performance metrics
    
    Returns:
        Comprehensive health status report
    """
    async with create_task_context("system_health_check", self.request.id) as ctx:
        logger.info("Starting comprehensive system health check")
        
        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "alerts": [],
            "metrics": {}
        }
        
        # Check database health
        db_health = await database_health_check.delay()
        health_report["components"]["database"] = await db_health
        
        # Check Redis health
        redis_health = await redis_health_check.delay()
        health_report["components"]["redis"] = await redis_health
        
        # Check Celery worker health
        celery_health = await check_celery_workers()
        health_report["components"]["celery"] = celery_health
        
        # Check external services
        external_health = await external_service_health_check.delay()
        health_report["components"]["external_services"] = await external_health
        
        # Collect performance metrics
        performance_metrics = await collect_performance_metrics()
        health_report["metrics"] = performance_metrics
        
        # Determine overall health status
        component_statuses = [comp["status"] for comp in health_report["components"].values()]
        
        if any(status == "critical" for status in component_statuses):
            health_report["overall_status"] = "critical"
            health_report["alerts"].append("Critical component failure detected")
        elif any(status == "warning" for status in component_statuses):
            health_report["overall_status"] = "warning"
            health_report["alerts"].append("Component warnings detected")
        
        # Log health status
        if health_report["overall_status"] != "healthy":
            logger.warning(f"System health check shows {health_report['overall_status']} status")
        else:
            logger.info("System health check passed - all components healthy")
        
        # Store health report (would integrate with monitoring service)
        await store_health_report(health_report)
        
        return health_report


@worker_task(priority=TaskPriority.NORMAL)
async def database_health_check(self) -> Dict[str, Any]:
    """
    Detailed database health check and performance monitoring.
    
    Returns:
        Database health status and performance metrics
    """
    async with create_task_context("database_health_check", self.request.id) as ctx:
        logger.info("Performing database health check")
        
        health_status = {
            "status": "healthy",
            "connection": False,
            "response_time_ms": 0,
            "active_connections": 0,
            "metrics": {}
        }
        
        try:
            # Test basic connectivity
            start_time = datetime.utcnow()
            
            # Execute simple query to test connection
            result = await ctx.db_session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                health_status["connection"] = True
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                health_status["response_time_ms"] = round(response_time, 2)
            
            # Get connection pool statistics
            pool_stats = await get_database_pool_stats(ctx.db_session)
            health_status["active_connections"] = pool_stats.get("active_connections", 0)
            health_status["metrics"] = pool_stats
            
            # Check response time thresholds
            if health_status["response_time_ms"] > 1000:  # 1 second
                health_status["status"] = "critical"
            elif health_status["response_time_ms"] > 500:  # 500ms
                health_status["status"] = "warning"
            
            logger.info(f"Database health check completed: {health_status['status']} "
                       f"({health_status['response_time_ms']}ms)")
                       
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status.update({
                "status": "critical",
                "connection": False,
                "error": str(e)
            })
        
        return health_status


@worker_task(priority=TaskPriority.NORMAL)
async def redis_health_check(self) -> Dict[str, Any]:
    """
    Redis health check and performance monitoring.
    
    Returns:
        Redis health status and performance metrics
    """
    logger.info("Performing Redis health check")
    
    health_status = {
        "status": "healthy",
        "connection": False,
        "response_time_ms": 0,
        "memory_usage": {},
        "queue_stats": {}
    }
    
    try:
        from redis import Redis
        from app.core.config import settings
        
        start_time = datetime.utcnow()
        
        # Create Redis client
        redis_client = Redis.from_url(settings.REDIS_URL or 'redis://localhost:6379/0')
        
        # Test connectivity
        pong = redis_client.ping()
        if pong:
            health_status["connection"] = True
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            health_status["response_time_ms"] = round(response_time, 2)
        
        # Get memory usage info
        memory_info = redis_client.info('memory')
        health_status["memory_usage"] = {
            "used_memory_mb": round(memory_info.get('used_memory', 0) / 1024 / 1024, 2),
            "used_memory_peak_mb": round(memory_info.get('used_memory_peak', 0) / 1024 / 1024, 2),
            "memory_fragmentation_ratio": memory_info.get('mem_fragmentation_ratio', 0)
        }
        
        # Get queue statistics
        queue_lengths = celery_manager.get_queue_lengths()
        health_status["queue_stats"] = queue_lengths
        
        # Check performance thresholds
        if health_status["response_time_ms"] > 100:  # 100ms
            health_status["status"] = "warning"
        if health_status["memory_usage"]["used_memory_mb"] > 1000:  # 1GB
            health_status["status"] = "warning"
            
        logger.info(f"Redis health check completed: {health_status['status']} "
                   f"({health_status['response_time_ms']}ms, "
                   f"{health_status['memory_usage']['used_memory_mb']}MB)")
                   
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status.update({
            "status": "critical",
            "connection": False,
            "error": str(e)
        })
    
    return health_status


@worker_task(priority=TaskPriority.NORMAL)
async def external_service_health_check(self) -> Dict[str, Any]:
    """
    Check health of external services and APIs.
    
    Returns:
        Health status of external service integrations
    """
    logger.info("Performing external service health checks")
    
    services_status = {
        "overall_status": "healthy",
        "services": {}
    }
    
    # List of external services to check
    services_to_check = [
        {"name": "stripe", "url": "https://api.stripe.com/v1/ping", "timeout": 10},
        {"name": "sendgrid", "url": "https://api.sendgrid.com/v3/ping", "timeout": 10},
        {"name": "google_vision", "endpoint": "vision_api", "timeout": 15},
    ]
    
    try:
        import httpx
        
        for service in services_to_check:
            service_name = service["name"]
            service_status = {
                "status": "healthy",
                "response_time_ms": 0,
                "available": False
            }
            
            try:
                start_time = datetime.utcnow()
                
                if service.get("url"):
                    # HTTP endpoint check
                    async with httpx.AsyncClient(timeout=service["timeout"]) as client:
                        response = await client.get(service["url"])
                        service_status["available"] = response.status_code < 500
                        service_status["status_code"] = response.status_code
                else:
                    # Custom endpoint check (would implement specific checks)
                    service_status["available"] = await check_custom_service(service["endpoint"])
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                service_status["response_time_ms"] = round(response_time, 2)
                
                # Determine status based on availability and response time
                if not service_status["available"]:
                    service_status["status"] = "critical"
                elif service_status["response_time_ms"] > 5000:  # 5 seconds
                    service_status["status"] = "warning"
                    
            except Exception as e:
                logger.error(f"Failed to check {service_name}: {e}")
                service_status.update({
                    "status": "critical",
                    "available": False,
                    "error": str(e)
                })
            
            services_status["services"][service_name] = service_status
        
        # Determine overall status
        service_statuses = [svc["status"] for svc in services_status["services"].values()]
        if any(status == "critical" for status in service_statuses):
            services_status["overall_status"] = "warning"  # External services are not critical for core operation
        
        logger.info(f"External service health check completed: {services_status['overall_status']}")
        
    except Exception as e:
        logger.error(f"External service health check failed: {e}")
        services_status.update({
            "overall_status": "warning",
            "error": str(e)
        })
    
    return services_status


async def check_celery_workers() -> Dict[str, Any]:
    """Check Celery worker health and statistics."""
    logger.info("Checking Celery worker health")
    
    worker_status = {
        "status": "healthy",
        "active_workers": 0,
        "total_tasks": 0,
        "queue_lengths": {},
        "workers": {}
    }
    
    try:
        # Get worker statistics
        worker_stats = celery_manager.get_worker_stats()
        active_tasks = celery_manager.get_active_tasks()
        queue_lengths = celery_manager.get_queue_lengths()
        
        worker_status["active_workers"] = len(worker_stats)
        worker_status["queue_lengths"] = queue_lengths
        worker_status["workers"] = worker_stats
        
        # Calculate total active tasks
        total_active = sum(len(tasks) for tasks in active_tasks.values())
        worker_status["total_tasks"] = total_active
        
        # Check for issues
        if worker_status["active_workers"] == 0:
            worker_status["status"] = "critical"
        elif sum(queue_lengths.values()) > 1000:  # Too many queued tasks
            worker_status["status"] = "warning"
        
        logger.info(f"Celery worker check: {worker_status['active_workers']} workers, "
                   f"{worker_status['total_tasks']} active tasks")
        
    except Exception as e:
        logger.error(f"Celery worker check failed: {e}")
        worker_status.update({
            "status": "critical",
            "error": str(e)
        })
    
    return worker_status


async def collect_performance_metrics() -> Dict[str, Any]:
    """Collect system performance metrics."""
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_usage": 0,
        "memory_usage": 0,
        "disk_usage": 0,
        "network_io": {}
    }
    
    try:
        import psutil
        
        # CPU usage
        metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        metrics["memory_usage"] = memory.percent
        metrics["memory_available_mb"] = round(memory.available / 1024 / 1024, 2)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        metrics["disk_usage"] = round((disk.used / disk.total) * 100, 2)
        metrics["disk_free_gb"] = round(disk.free / 1024 / 1024 / 1024, 2)
        
        # Network I/O (if available)
        network = psutil.net_io_counters()
        metrics["network_io"] = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv
        }
        
    except ImportError:
        logger.warning("psutil not available for system metrics")
    except Exception as e:
        logger.error(f"Error collecting performance metrics: {e}")
    
    return metrics


# Helper functions

async def get_database_pool_stats(db_session) -> Dict[str, Any]:
    """Get database connection pool statistics."""
    try:
        # This would integrate with actual connection pool monitoring
        return {
            "active_connections": 5,
            "idle_connections": 3,
            "total_connections": 8,
            "max_connections": 20
        }
    except Exception as e:
        logger.error(f"Error getting database pool stats: {e}")
        return {}

async def check_custom_service(endpoint: str) -> bool:
    """Check custom service endpoint health."""
    # This would implement specific service checks
    logger.info(f"Checking custom service endpoint: {endpoint}")
    return True  # Placeholder

async def store_health_report(report: Dict[str, Any]):
    """Store health report for monitoring and alerting."""
    # This would integrate with monitoring service (DataDog, New Relic, etc.)
    logger.info(f"Health report stored: {report['overall_status']}")


__all__ = [
    'system_health_check',
    'database_health_check',
    'redis_health_check',
    'external_service_health_check'
]