#!/usr/bin/env python3
"""
AutoDMCA Celery Worker Startup Script

This script starts Celery workers with proper configuration for the AutoDMCA platform.
It supports different worker types and deployment scenarios.

Usage:
    python start_workers.py --worker-type all
    python start_workers.py --worker-type dmca --concurrency 4
    python start_workers.py --worker-type content --loglevel info
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration for workers."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/celery_workers.log') if os.path.exists('logs') else logging.NullHandler()
        ]
    )


def get_worker_queues(worker_type: str) -> list:
    """Get the queues that a specific worker type should handle."""
    queue_mappings = {
        "all": [
            "dmca_high", "content_processing", "ai_processing", 
            "notifications", "scanning", "billing", 
            "analytics_low", "maintenance", "default"
        ],
        "dmca": ["dmca_high", "default"],
        "content": ["content_processing", "ai_processing"],
        "notifications": ["notifications"],
        "scanning": ["scanning"],
        "billing": ["billing"],
        "analytics": ["analytics_low"],
        "maintenance": ["maintenance", "default"],
        "high_priority": ["dmca_high", "billing", "notifications"],
        "low_priority": ["analytics_low", "maintenance"]
    }
    
    return queue_mappings.get(worker_type, ["default"])


def build_celery_command(args) -> list:
    """Build the Celery worker command with appropriate arguments."""
    cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "worker"
    ]
    
    # Add queues
    queues = get_worker_queues(args.worker_type)
    cmd.extend(["--queues", ",".join(queues)])
    
    # Add concurrency
    cmd.extend(["--concurrency", str(args.concurrency)])
    
    # Add log level
    cmd.extend(["--loglevel", args.loglevel])
    
    # Add worker name
    worker_name = f"worker-{args.worker_type}@%h"
    cmd.extend(["--hostname", worker_name])
    
    # Add performance optimizations
    cmd.extend([
        "--pool", "prefork",  # Use prefork pool for better isolation
        "--prefetch-multiplier", "1",  # Process one task at a time
        "--max-tasks-per-child", "1000",  # Restart workers after 1000 tasks
        "--task-events",  # Enable task events for monitoring
    ])
    
    # Add optimization flags
    if args.optimize:
        cmd.extend([
            "-O", "fair",  # Fair task routing
            "--without-mingle",  # Disable worker synchronization at startup
            "--without-gossip"   # Disable gossip for faster startup
        ])
    
    return cmd


def start_beat_scheduler(args):
    """Start Celery Beat scheduler for periodic tasks."""
    import subprocess
    
    beat_cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "beat",
        "--loglevel", args.loglevel,
        "--schedule", "celerybeat-schedule.db",
        "--pidfile", "celerybeat.pid"
    ]
    
    if args.detach:
        beat_cmd.append("--detach")
    
    logger.info(f"Starting Celery Beat scheduler: {' '.join(beat_cmd)}")
    
    try:
        subprocess.run(beat_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Celery Beat: {e}")
        sys.exit(1)


def start_flower_monitoring(args):
    """Start Flower monitoring interface."""
    import subprocess
    
    flower_cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "flower",
        "--port", str(args.flower_port),
        "--basic_auth", f"admin:{args.flower_password or 'admin'}"
    ]
    
    logger.info(f"Starting Flower monitoring on port {args.flower_port}")
    
    try:
        subprocess.Popen(flower_cmd)
        logger.info(f"Flower started at http://localhost:{args.flower_port}")
    except Exception as e:
        logger.error(f"Failed to start Flower: {e}")


def main():
    """Main entry point for worker startup."""
    parser = argparse.ArgumentParser(
        description="AutoDMCA Celery Worker Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Worker Types:
  all              - All queues (default for single-server deployment)
  dmca             - High-priority DMCA processing tasks
  content          - Content processing and AI analysis
  notifications    - Email and notification delivery
  scanning         - Platform scanning and monitoring
  billing          - Subscription and payment processing
  analytics        - Analytics and reporting (low priority)
  maintenance      - Cleanup and maintenance tasks
  high_priority    - Critical tasks only (DMCA, billing, notifications)
  low_priority     - Low priority tasks only (analytics, maintenance)

Examples:
  python start_workers.py --worker-type all
  python start_workers.py --worker-type dmca --concurrency 4
  python start_workers.py --worker-type high_priority --optimize
  python start_workers.py --beat --flower
        """
    )
    
    parser.add_argument(
        "--worker-type", 
        choices=[
            "all", "dmca", "content", "notifications", "scanning", 
            "billing", "analytics", "maintenance", "high_priority", "low_priority"
        ],
        default="all",
        help="Type of worker to start (default: all)"
    )
    
    parser.add_argument(
        "--concurrency", 
        type=int, 
        default=4,
        help="Number of worker processes (default: 4)"
    )
    
    parser.add_argument(
        "--loglevel", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Enable optimization flags for production"
    )
    
    parser.add_argument(
        "--beat",
        action="store_true",
        help="Also start Celery Beat scheduler"
    )
    
    parser.add_argument(
        "--flower",
        action="store_true",
        help="Also start Flower monitoring interface"
    )
    
    parser.add_argument(
        "--flower-port",
        type=int,
        default=5555,
        help="Port for Flower monitoring interface (default: 5555)"
    )
    
    parser.add_argument(
        "--flower-password",
        help="Password for Flower basic auth (default: admin)"
    )
    
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Run Beat scheduler in background"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show command that would be executed without running it"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.loglevel)
    
    logger.info("Starting AutoDMCA Celery Workers")
    logger.info(f"Worker type: {args.worker_type}")
    logger.info(f"Queues: {', '.join(get_worker_queues(args.worker_type))}")
    logger.info(f"Concurrency: {args.concurrency}")
    
    # Start Flower monitoring if requested
    if args.flower:
        start_flower_monitoring(args)
    
    # Start Beat scheduler if requested  
    if args.beat:
        start_beat_scheduler(args)
    
    # Build and execute worker command
    worker_cmd = build_celery_command(args)
    
    if args.dry_run:
        logger.info(f"Dry run - would execute: {' '.join(worker_cmd)}")
        return
    
    logger.info(f"Starting Celery worker: {' '.join(worker_cmd)}")
    
    try:
        # Use execvp to replace the current process with Celery worker
        import subprocess
        os.execvp("celery", worker_cmd)
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()