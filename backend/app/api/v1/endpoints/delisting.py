"""
Search Engine Delisting API Endpoints
Provides REST API interface for delisting automation system
PRD: "Dashboard integration for user visibility", "Real-time status tracking and reporting"
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.models.delisting import (
    DelistingRequest, DelistingSearchEngineRequest, DelistingBatch, 
    DelistingVerification, DelistingStatistics, DelistingAlert,
    DelistingRequestStatus, SearchEngineType, DelistingRequestPriority
)
from app.schemas.delisting import (
    DelistingRequestCreate, DelistingRequestResponse, DelistingBatchCreate,
    DelistingBatchResponse, DelistingStatusUpdate, DelistingStatsResponse,
    DelistingVerificationResponse, DelistingAlertResponse
)
from app.services.scanning.delisting_manager import delisting_manager
from app.services.scanning.delisting_monitor import delisting_monitor
from app.services.scanning.delisting_service import SearchEngine
from app.api.deps.auth import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/requests", response_model=DelistingRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_delisting_request(
    request_data: DelistingRequestCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a single URL for delisting across specified search engines
    PRD: "Automatically submitting requests to Google, Bing to remove offending URLs"
    """
    try:
        # Convert search engines
        search_engines = [SearchEngine(engine.value) for engine in request_data.search_engines]
        
        # Submit to delisting manager
        request_id = await delisting_manager.submit_url_removal(
            url=request_data.url,
            search_engines=search_engines,
            priority=request_data.priority,
            reason=request_data.reason,
            evidence_url=request_data.evidence_url
        )
        
        # Create database record
        db_request = DelistingRequest(
            id=request_id,
            url=request_data.url,
            original_content_url=request_data.original_content_url,
            reason=request_data.reason,
            evidence_url=request_data.evidence_url,
            priority=request_data.priority,
            user_id=current_user.id,
            profile_id=request_data.profile_id
        )
        
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        
        logger.info(f"Delisting request {request_id} submitted for {request_data.url}")
        
        return DelistingRequestResponse(
            id=request_id,
            url=request_data.url,
            status=DelistingRequestStatus.PENDING,
            search_engines=[engine.name for engine in search_engines],
            submitted_at=datetime.utcnow(),
            message="Request submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting delisting request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit delisting request: {str(e)}"
        )

@router.post("/batch", response_model=DelistingBatchResponse, status_code=status.HTTP_201_CREATED)
async def submit_batch_delisting(
    batch_data: DelistingBatchCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit multiple URLs for delisting as a batch operation
    PRD: "Batch processing of multiple URLs"
    """
    try:
        # Convert search engines
        search_engines = [SearchEngine(engine.value) for engine in batch_data.search_engines]
        
        # Submit batch to delisting manager
        batch_id = await delisting_manager.submit_batch_removal(
            urls=batch_data.urls,
            search_engines=search_engines,
            priority=batch_data.priority,
            reason=batch_data.reason,
            evidence_url=batch_data.evidence_url,
            batch_size=batch_data.batch_size
        )
        
        # Create database batch record
        db_batch = DelistingBatch(
            id=batch_id,
            name=batch_data.name,
            description=batch_data.description,
            total_requests=len(batch_data.urls),
            batch_size=batch_data.batch_size,
            priority=batch_data.priority,
            user_id=current_user.id
        )
        
        db.add(db_batch)
        db.commit()
        db.refresh(db_batch)
        
        logger.info(f"Batch delisting {batch_id} submitted with {len(batch_data.urls)} URLs")
        
        return DelistingBatchResponse(
            id=batch_id,
            name=batch_data.name,
            total_requests=len(batch_data.urls),
            submitted_at=datetime.utcnow(),
            status="submitted",
            message="Batch submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting batch delisting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit batch delisting: {str(e)}"
        )

@router.get("/requests/{request_id}", response_model=DelistingRequestResponse)
async def get_delisting_request_status(
    request_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed status of a specific delisting request
    PRD: "Status tracking for removal requests"
    """
    try:
        # Get from database
        db_request = db.query(DelistingRequest).filter(
            DelistingRequest.id == request_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delisting request not found"
            )
        
        # Get real-time status from manager
        manager_status = await delisting_manager.get_request_status(request_id)
        
        # Get search engine specific statuses
        engine_statuses = {}
        for se_request in db_request.search_engine_requests:
            engine_statuses[se_request.search_engine.value] = {
                "status": se_request.status.value,
                "submitted_at": se_request.submitted_at,
                "completed_at": se_request.completed_at,
                "message": se_request.response_message
            }
        
        return DelistingRequestResponse(
            id=request_id,
            url=db_request.url,
            status=db_request.status,
            search_engines=list(engine_statuses.keys()),
            submitted_at=db_request.created_at,
            updated_at=db_request.updated_at,
            engine_statuses=engine_statuses,
            retry_count=db_request.retry_count,
            message=manager_status.get("message", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delisting request status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get request status"
        )

@router.get("/batch/{batch_id}", response_model=DelistingBatchResponse)
async def get_batch_status(
    batch_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed status of a batch delisting request
    PRD: "Batch processing status tracking"
    """
    try:
        # Get from database
        db_batch = db.query(DelistingBatch).filter(
            DelistingBatch.id == batch_id
        ).first()
        
        if not db_batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch not found"
            )
        
        # Get real-time status from manager
        manager_status = await delisting_manager.get_batch_status(batch_id)
        
        # Determine overall status
        overall_status = "completed"
        if manager_status.get("status") == "processing":
            overall_status = "processing"
        elif manager_status.get("status") == "pending":
            overall_status = "pending"
        
        return DelistingBatchResponse(
            id=batch_id,
            name=db_batch.name,
            description=db_batch.description,
            total_requests=db_batch.total_requests,
            completed_requests=db_batch.completed_requests,
            failed_requests=db_batch.failed_requests,
            success_rate=db_batch.success_rate,
            submitted_at=db_batch.created_at,
            started_at=db_batch.started_at,
            completed_at=db_batch.completed_at,
            status=overall_status,
            message=f"Batch processing: {db_batch.completed_requests}/{db_batch.total_requests} completed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get batch status"
        )

@router.get("/requests", response_model=List[DelistingRequestResponse])
async def list_delisting_requests(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[DelistingRequestStatus] = Query(None),
    url_filter: Optional[str] = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List delisting requests with filtering and pagination
    """
    try:
        query = db.query(DelistingRequest).filter(
            DelistingRequest.user_id == current_user.id
        )
        
        if status_filter:
            query = query.filter(DelistingRequest.status == status_filter)
        
        if url_filter:
            query = query.filter(DelistingRequest.url.ilike(f"%{url_filter}%"))
        
        requests = query.order_by(desc(DelistingRequest.created_at)).offset(offset).limit(limit).all()
        
        return [
            DelistingRequestResponse(
                id=req.id,
                url=req.url,
                status=req.status,
                search_engines=[se.search_engine.value for se in req.search_engine_requests],
                submitted_at=req.created_at,
                updated_at=req.updated_at,
                retry_count=req.retry_count
            )
            for req in requests
        ]
        
    except Exception as e:
        logger.error(f"Error listing delisting requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list requests"
        )

@router.post("/requests/{request_id}/cancel")
async def cancel_delisting_request(
    request_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending delisting request
    """
    try:
        # Check if request exists and belongs to user
        db_request = db.query(DelistingRequest).filter(
            DelistingRequest.id == request_id,
            DelistingRequest.user_id == current_user.id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delisting request not found"
            )
        
        if db_request.status not in [DelistingRequestStatus.PENDING, DelistingRequestStatus.SUBMITTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request cannot be cancelled in current status"
            )
        
        # Cancel in manager
        cancelled = await delisting_manager.cancel_request(request_id)
        
        if cancelled:
            db_request.status = DelistingRequestStatus.FAILED
            db_request.updated_at = datetime.utcnow()
            db.commit()
            
            return {"message": "Request cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request could not be cancelled"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling delisting request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel request"
        )

@router.post("/requests/{request_id}/retry")
async def retry_delisting_request(
    request_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retry a failed delisting request
    PRD: "Retry logic for failed submissions"
    """
    try:
        # Check if request exists and belongs to user
        db_request = db.query(DelistingRequest).filter(
            DelistingRequest.id == request_id,
            DelistingRequest.user_id == current_user.id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delisting request not found"
            )
        
        if db_request.status != DelistingRequestStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed requests can be retried"
            )
        
        if db_request.retry_count >= db_request.max_retries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum retry attempts reached"
            )
        
        # Resubmit request
        search_engines = [SearchEngine(se.search_engine.value) for se in db_request.search_engine_requests]
        
        new_request_id = await delisting_manager.submit_url_removal(
            url=db_request.url,
            search_engines=search_engines,
            priority=db_request.priority,
            reason=db_request.reason,
            evidence_url=db_request.evidence_url
        )
        
        # Update database
        db_request.retry_count += 1
        db_request.last_retry_at = datetime.utcnow()
        db_request.status = DelistingRequestStatus.PENDING
        db_request.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Request retry submitted successfully", "new_request_id": new_request_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying delisting request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry request"
        )

@router.get("/statistics", response_model=DelistingStatsResponse)
async def get_delisting_statistics(
    time_period: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive delisting statistics
    PRD: "Report success rates to users", "Success/failure monitoring and reporting"
    """
    try:
        # Calculate time window
        time_windows = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        cutoff_time = datetime.utcnow() - time_windows[time_period]
        
        # Get real-time metrics from monitor
        performance_metrics = await delisting_monitor.get_performance_metrics(time_windows[time_period])
        
        # Get database statistics for user
        user_stats = db.query(
            func.count(DelistingRequest.id).label("total"),
            func.count(DelistingRequest.id).filter(DelistingRequest.status == DelistingRequestStatus.REMOVED).label("successful"),
            func.count(DelistingRequest.id).filter(DelistingRequest.status.in_([DelistingRequestStatus.FAILED, DelistingRequestStatus.REJECTED])).label("failed"),
            func.count(DelistingRequest.id).filter(DelistingRequest.status.in_([DelistingRequestStatus.PENDING, DelistingRequestStatus.SUBMITTED, DelistingRequestStatus.IN_PROGRESS])).label("pending"),
        ).filter(
            DelistingRequest.user_id == current_user.id,
            DelistingRequest.created_at >= cutoff_time
        ).first()
        
        # Calculate success rate
        success_rate = 0.0
        if user_stats.successful + user_stats.failed > 0:
            success_rate = user_stats.successful / (user_stats.successful + user_stats.failed)
        
        # Get search engine breakdown
        engine_stats = {}
        for engine in SearchEngineType:
            engine_requests = db.query(DelistingSearchEngineRequest).join(DelistingRequest).filter(
                DelistingRequest.user_id == current_user.id,
                DelistingSearchEngineRequest.search_engine == engine,
                DelistingRequest.created_at >= cutoff_time
            ).all()
            
            successful = len([r for r in engine_requests if r.status == DelistingRequestStatus.REMOVED])
            total = len(engine_requests)
            
            engine_stats[engine.value] = {
                "total_requests": total,
                "successful": successful,
                "success_rate": successful / total if total > 0 else 0.0
            }
        
        return DelistingStatsResponse(
            time_period=time_period,
            total_requests=user_stats.total,
            successful_requests=user_stats.successful,
            failed_requests=user_stats.failed,
            pending_requests=user_stats.pending,
            success_rate=success_rate,
            average_processing_time=performance_metrics.average_processing_time,
            search_engine_breakdown=engine_stats,
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting delisting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time dashboard data for monitoring
    PRD: "Real-time status updates", "Dashboard integration for user visibility"
    """
    try:
        # Get real-time data from monitor
        dashboard_data = await delisting_monitor.get_real_time_dashboard_data()
        
        # Get user-specific recent activity
        recent_requests = db.query(DelistingRequest).filter(
            DelistingRequest.user_id == current_user.id,
            DelistingRequest.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(desc(DelistingRequest.created_at)).limit(10).all()
        
        # Get active alerts
        active_alerts = db.query(DelistingAlert).filter(
            DelistingAlert.is_active == True,
            DelistingAlert.triggered_at >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        return {
            "system_status": dashboard_data,
            "recent_requests": [
                {
                    "id": req.id,
                    "url": req.url,
                    "status": req.status.value,
                    "created_at": req.created_at.isoformat()
                }
                for req in recent_requests
            ],
            "active_alerts": [
                {
                    "id": alert.id,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat()
                }
                for alert in active_alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard data"
        )

@router.get("/verification/{request_id}", response_model=List[DelistingVerificationResponse])
async def get_verification_results(
    request_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get verification results for a delisting request
    PRD: "Verification of successful removals"
    """
    try:
        # Check if request exists and belongs to user
        db_request = db.query(DelistingRequest).filter(
            DelistingRequest.id == request_id,
            DelistingRequest.user_id == current_user.id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delisting request not found"
            )
        
        # Get verification records
        verifications = db.query(DelistingVerification).filter(
            DelistingVerification.delisting_request_id == request_id
        ).all()
        
        return [
            DelistingVerificationResponse(
                id=v.id,
                url=v.url,
                search_engine=v.search_engine.value,
                is_removed=v.is_removed,
                verified_at=v.verified_at,
                verification_method=v.verification_method,
                search_queries_used=v.search_queries_used,
                search_results_found=v.search_results_found
            )
            for v in verifications
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification results"
        )

@router.post("/verify/{request_id}")
async def trigger_verification(
    request_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger verification for a completed delisting request
    """
    try:
        # Check if request exists and belongs to user
        db_request = db.query(DelistingRequest).filter(
            DelistingRequest.id == request_id,
            DelistingRequest.user_id == current_user.id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delisting request not found"
            )
        
        if db_request.status != DelistingRequestStatus.REMOVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only successfully removed requests can be verified"
            )
        
        # Queue verification
        background_tasks.add_task(
            _verify_request_background,
            request_id,
            db_request.url
        )
        
        return {"message": "Verification queued successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger verification"
        )

async def _verify_request_background(request_id: str, url: str):
    """Background task to verify a delisting request"""
    try:
        from app.services.scanning.delisting_service import SearchEngineDelistingService
        
        async with SearchEngineDelistingService() as service:
            verification_result = await service.verify_url_removal(url)
            
            # Store verification results in database
            # This would be implemented with proper database session handling
            logger.info(f"Verification completed for {request_id}: {verification_result}")
            
    except Exception as e:
        logger.error(f"Error in background verification: {e}")