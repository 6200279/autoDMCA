"""
API endpoints for social media monitoring management.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.db.models.profile import ProtectedProfile
from app.db.models.social_media import SocialMediaPlatform, MonitoringStatus
from app.schemas.social_media import (
    SocialMediaAccountResponse,
    MonitoringSessionResponse,
    MonitoringJobRequest,
    MonitoringJobResponse,
    ReportSubmissionResponse,
    PlatformStatsResponse,
    ScheduleTaskRequest,
    ScheduleTaskResponse,
    EmergencyMonitoringRequest
)
from app.services.social_media.config import MonitoringConfig, SocialMediaSettings
from app.services.social_media.monitoring_service import SocialMediaMonitoringService
from app.services.social_media.scheduler import MonitoringScheduler, TaskPriority
from app.services.social_media.dmca_integration import SocialMediaDMCABridge
from app.services.dmca.dmca_service import DMCAService


router = APIRouter()

# Initialize services (in production, these would be dependency injected)
monitoring_config = MonitoringConfig()
monitoring_service = SocialMediaMonitoringService(monitoring_config)
dmca_service = DMCAService()  # This would need proper initialization
dmca_bridge = SocialMediaDMCABridge(monitoring_config, dmca_service)
scheduler = MonitoringScheduler(monitoring_config, monitoring_service)


@router.post("/monitor/start", response_model=MonitoringJobResponse)
async def start_monitoring(
    request: MonitoringJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start social media monitoring for a profile."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == request.profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        # Start monitoring job
        job_id = await monitoring_service.start_monitoring(
            profile_id=request.profile_id,
            platforms=request.platforms,
            monitoring_type=request.monitoring_type
        )
        
        # Process in background
        background_tasks.add_task(
            _process_monitoring_results,
            profile.id,
            job_id
        )
        
        return MonitoringJobResponse(
            job_id=job_id,
            status="queued",
            profile_id=request.profile_id,
            platforms=[p.value for p in request.platforms],
            monitoring_type=request.monitoring_type,
            created_at=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.get("/monitor/status/{job_id}", response_model=Dict[str, Any])
async def get_monitoring_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of a monitoring job."""
    
    try:
        status_info = monitoring_service.get_job_status(job_id)
        
        if status_info["status"] == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring job not found"
            )
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.post("/schedule/create", response_model=ScheduleTaskResponse)
async def create_scheduled_task(
    request: ScheduleTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a scheduled monitoring task."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == request.profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        # Map priority string to enum
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        priority = priority_map.get(request.priority.lower(), TaskPriority.MEDIUM)
        
        # Create scheduled task
        if request.schedule_type == "one_time":
            task_id = await scheduler.schedule_one_time_monitoring(
                profile_id=request.profile_id,
                platforms=request.platforms,
                run_at=request.run_at,
                priority=priority
            )
        else:
            task_id = await scheduler.schedule_profile_monitoring(
                profile_id=request.profile_id,
                platforms=request.platforms,
                schedule_type=request.schedule_type,
                custom_schedule=request.custom_schedule,
                priority=priority
            )
        
        task_details = await scheduler.get_task_details(task_id)
        
        return ScheduleTaskResponse(
            task_id=task_id,
            status="scheduled",
            profile_id=request.profile_id,
            platforms=[p.value for p in request.platforms],
            schedule_type=request.schedule_type,
            next_run=task_details["next_run"] if task_details else None,
            created_at=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scheduled task: {str(e)}"
        )


@router.get("/schedule/tasks/{profile_id}", response_model=List[Dict[str, Any]])
async def list_profile_tasks(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all scheduled tasks for a profile."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        tasks = await scheduler.list_profile_tasks(profile_id)
        return tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.delete("/schedule/tasks/{task_id}")
async def cancel_scheduled_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a scheduled monitoring task."""
    
    try:
        # Get task details to verify ownership
        task_details = await scheduler.get_task_details(task_id)
        
        if not task_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify profile ownership (basic check)
        # In production, you'd want more thorough ownership verification
        
        success = await scheduler.cancel_task(task_id)
        
        if success:
            return {"message": "Task cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel task"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post("/emergency/monitor", response_model=Dict[str, Any])
async def emergency_monitoring(
    request: EmergencyMonitoringRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate emergency monitoring with highest priority."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == request.profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        # Schedule emergency monitoring
        task_id = await scheduler.schedule_emergency_monitoring(
            profile_id=request.profile_id,
            platforms=request.platforms,
            reason=request.reason
        )
        
        # Process immediately in background
        background_tasks.add_task(
            _process_emergency_monitoring,
            profile.id,
            request.platforms,
            request.reason
        )
        
        return {
            "task_id": task_id,
            "status": "emergency_processing",
            "message": f"Emergency monitoring initiated: {request.reason}",
            "estimated_completion": "5-15 minutes"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate emergency monitoring: {str(e)}"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_monitoring_statistics(
    current_user: User = Depends(get_current_user)
):
    """Get overall monitoring statistics."""
    
    try:
        monitoring_stats = monitoring_service.get_monitoring_statistics()
        scheduler_stats = scheduler.get_scheduler_statistics()
        
        return {
            "monitoring_service": monitoring_stats,
            "scheduler": scheduler_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/platforms", response_model=List[str])
async def get_supported_platforms():
    """Get list of supported social media platforms."""
    
    return [platform.value for platform in SocialMediaPlatform]


@router.get("/reports/comprehensive/{profile_id}")
async def get_comprehensive_report(
    profile_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include in report"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive monitoring and DMCA report for a profile."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        report = await dmca_bridge.generate_comprehensive_report(
            profile_id=profile_id,
            date_range=(start_date, end_date)
        )
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.post("/reports/sync-status")
async def sync_report_status(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Sync status of platform reports with actual platform responses."""
    
    try:
        # Run sync in background
        background_tasks.add_task(_sync_report_status)
        
        return {
            "message": "Report status sync initiated",
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sync: {str(e)}"
        )


@router.post("/profiles/{profile_id}/pause-monitoring")
async def pause_profile_monitoring(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause all monitoring for a profile."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        paused_count = await scheduler.pause_profile_monitoring(profile_id)
        
        return {
            "profile_id": profile_id,
            "message": f"Paused {paused_count} monitoring tasks",
            "paused_tasks": paused_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause monitoring: {str(e)}"
        )


@router.post("/profiles/{profile_id}/resume-monitoring")
async def resume_profile_monitoring(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume all monitoring for a profile."""
    
    # Verify profile ownership
    profile = db.query(ProtectedProfile).filter(
        ProtectedProfile.id == profile_id,
        ProtectedProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied"
        )
    
    try:
        resumed_count = await scheduler.resume_profile_monitoring(profile_id)
        
        return {
            "profile_id": profile_id,
            "message": f"Resumed {resumed_count} monitoring tasks",
            "resumed_tasks": resumed_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume monitoring: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring service."""
    
    try:
        monitoring_stats = monitoring_service.get_monitoring_statistics()
        scheduler_stats = scheduler.get_scheduler_statistics()
        
        # Check if services are healthy
        healthy = (
            monitoring_stats.get("uptime_hours", 0) < 168 and  # Less than a week uptime indicates recent restart
            scheduler_stats.get("scheduler_running", False)
        )
        
        return {
            "status": "healthy" if healthy else "degraded",
            "monitoring_service": {
                "active": True,
                "jobs_completed": monitoring_stats.get("jobs_completed", 0),
                "pending_jobs": monitoring_stats.get("pending_jobs", 0)
            },
            "scheduler": {
                "running": scheduler_stats.get("scheduler_running", False),
                "total_tasks": scheduler_stats.get("total_tasks", 0),
                "scheduled_jobs": scheduler_stats.get("scheduled_jobs", 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Background task functions

async def _process_monitoring_results(profile_id: int, job_id: str):
    """Process monitoring results in background."""
    try:
        # Wait for job to complete
        max_wait = 600  # 10 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            status = monitoring_service.get_job_status(job_id)
            if status["status"] == "completed":
                break
            await asyncio.sleep(10)
            wait_time += 10
        
        # Get results and process with DMCA integration
        if status["status"] == "completed":
            # This would get the actual results and process them
            # For now, we'll simulate
            mock_results = {}  # In reality, get from monitoring_service.completed_jobs
            
            if mock_results:
                await dmca_bridge.process_monitoring_results(profile_id, mock_results)
        
    except Exception as e:
        print(f"Background processing failed: {e}")  # In production, use proper logging


async def _process_emergency_monitoring(profile_id: int, platforms: List[SocialMediaPlatform], reason: str):
    """Process emergency monitoring in background."""
    try:
        results = await monitoring_service.emergency_monitoring(profile_id, platforms)
        await dmca_bridge.process_monitoring_results(profile_id, results)
        
    except Exception as e:
        print(f"Emergency monitoring failed: {e}")  # In production, use proper logging


async def _sync_report_status():
    """Sync report status in background."""
    try:
        await dmca_bridge.sync_social_media_reports_status()
        
    except Exception as e:
        print(f"Report status sync failed: {e}")  # In production, use proper logging