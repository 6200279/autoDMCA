"""
Content Upload API Endpoints for AutoDMCA

Provides comprehensive file upload capabilities:
- Chunked upload support for large files
- Content validation and processing
- Progress tracking
- Async processing integration
"""

import logging
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_verified_user
from app.db.session import get_async_session
from app.db.models.user import User
from app.core.container import container
from app.services.content.content_processing_service import (
    content_processing_service,
    ContentType,
    ProcessingStatus
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload/initiate")
async def initiate_upload(
    filename: str = Form(...),
    total_size: int = Form(...),
    content_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Initiate a chunked upload session
    
    Args:
        filename: Original filename
        total_size: Total file size in bytes
        content_type: Optional content type hint
        
    Returns:
        Upload session details including upload_id and chunk info
    """
    try:
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Initiate upload session
        result = await service.initiate_chunked_upload(
            user_id=current_user.id,
            filename=filename,
            total_size=total_size,
            content_type=content_type
        )
        
        logger.info(f"Upload initiated for user {current_user.id}: {result['upload_id']}")
        
        return {
            "success": True,
            "upload_id": result["upload_id"],
            "chunk_size": result["chunk_size"],
            "total_chunks": result["total_chunks"],
            "expires_at": result["expires_at"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload initiation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate upload"
        )


@router.post("/upload/chunk/{upload_id}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    chunk_data: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Upload a single chunk of data
    
    Args:
        upload_id: Upload session ID
        chunk_index: Index of this chunk (0-based)
        chunk_data: Chunk data file
        
    Returns:
        Upload progress and completion status
    """
    try:
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Read chunk data
        chunk_bytes = await chunk_data.read()
        
        # Upload chunk
        result = await service.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_bytes,
            user_id=current_user.id
        )
        
        logger.debug(f"Chunk {chunk_index} uploaded for {upload_id}")
        
        return {
            "success": True,
            "chunk_index": result["chunk_index"],
            "progress": result["progress"],
            "chunks_received": result["chunks_received"],
            "total_chunks": result["total_chunks"],
            "complete": result["complete"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Chunk upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload chunk"
        )


@router.post("/upload/complete/{upload_id}")
async def complete_upload(
    upload_id: str,
    apply_watermark: bool = Form(False),
    watermark_text: Optional[str] = Form(None),
    watermark_position: str = Form("bottom-right"),
    watermark_opacity: float = Form(0.5),
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Complete upload and start processing
    
    Args:
        upload_id: Upload session ID
        apply_watermark: Whether to apply watermark
        watermark_text: Custom watermark text
        watermark_position: Watermark position
        watermark_opacity: Watermark opacity (0.0-1.0)
        
    Returns:
        Processing job details
    """
    try:
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Build processing config
        process_config = {
            "apply_watermark": apply_watermark
        }
        
        if apply_watermark:
            process_config["watermark_config"] = {
                "text": watermark_text or f"© User {current_user.id}",
                "position": watermark_position,
                "opacity": max(0.0, min(1.0, watermark_opacity)),
                "visible": True,
                "invisible": True
            }
        
        # Complete upload and start processing
        result = await service.complete_upload(
            upload_id=upload_id,
            user_id=current_user.id,
            process_config=process_config
        )
        
        logger.info(f"Upload completed for user {current_user.id}: {result['job_id']}")
        
        return {
            "success": True,
            "job_id": result["job_id"],
            "status": result["status"],
            "content_type": result["content_type"],
            "file_size": result["file_size"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload completion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload"
        )


@router.post("/upload/simple")
async def simple_upload(
    file: UploadFile = File(...),
    apply_watermark: bool = Form(False),
    watermark_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Simple single-file upload (non-chunked)
    
    Args:
        file: Upload file
        apply_watermark: Whether to apply watermark
        watermark_text: Custom watermark text
        
    Returns:
        Processing job details
    """
    try:
        # Check file size (limit for simple upload)
        max_simple_size = 50 * 1024 * 1024  # 50MB
        
        # Read file data
        file_data = await file.read()
        
        if len(file_data) > max_simple_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large for simple upload. Use chunked upload for files > {max_simple_size//1024//1024}MB"
            )
        
        # Save to temporary file
        import tempfile
        import os
        from pathlib import Path
        
        temp_dir = Path(tempfile.gettempdir()) / "autodmca_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"simple_{current_user.id}_{file.filename}"
        
        with open(temp_file, 'wb') as f:
            f.write(file_data)
        
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Build processing config
        process_config = {
            "apply_watermark": apply_watermark
        }
        
        if apply_watermark:
            process_config["watermark_config"] = {
                "text": watermark_text or f"© User {current_user.id}",
                "position": "bottom-right",
                "opacity": 0.5,
                "visible": True,
                "invisible": True
            }
        
        # Process content directly
        result = await service.process_content(
            file_path=str(temp_file),
            user_id=current_user.id,
            process_config=process_config
        )
        
        # Cleanup temp file
        try:
            os.unlink(temp_file)
        except:
            pass
        
        logger.info(f"Simple upload processed for user {current_user.id}")
        
        return {
            "success": True,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simple upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload"
        )


@router.get("/upload/status/{job_id}")
async def get_upload_status(
    job_id: str,
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Get processing status for a job
    
    Args:
        job_id: Processing job ID
        
    Returns:
        Job status and progress
    """
    try:
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Get job status
        status_info = await service.get_processing_status(job_id, current_user.id)
        
        if status_info.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        if status_info.get("status") == "unauthorized":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return {
            "success": True,
            **status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get status"
        )


@router.delete("/upload/cancel/{job_id}")
async def cancel_upload(
    job_id: str,
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Cancel a processing job
    
    Args:
        job_id: Processing job ID
        
    Returns:
        Cancellation result
    """
    try:
        # Get content processing service
        service = await container.get('ContentProcessingService')
        
        # Cancel job
        success = await service.cancel_processing(job_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel job (not found, unauthorized, or already completed)"
            )
        
        return {
            "success": True,
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job cancellation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


@router.post("/batch-upload")
async def batch_upload(
    files: List[UploadFile] = File(...),
    apply_watermark: bool = Form(False),
    watermark_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Batch upload multiple files
    
    Args:
        files: List of files to upload
        apply_watermark: Whether to apply watermarks
        watermark_text: Custom watermark text
        
    Returns:
        Batch processing job details
    """
    try:
        if len(files) > 10:  # Limit batch size
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 files per batch"
            )
        
        # Save files to temp directory
        import tempfile
        import os
        from pathlib import Path
        
        temp_dir = Path(tempfile.gettempdir()) / "autodmca_batch" / str(current_user.id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_paths = []
        
        for i, file in enumerate(files):
            # Check individual file size
            file_data = await file.read()
            if len(file_data) > 100 * 1024 * 1024:  # 100MB limit per file
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File {file.filename} is too large (max 100MB for batch upload)"
                )
            
            # Save file
            temp_file = temp_dir / f"batch_{i}_{file.filename}"
            with open(temp_file, 'wb') as f:
                f.write(file_data)
            
            file_paths.append(str(temp_file))
        
        # Build processing config
        process_config = {
            "apply_watermark": apply_watermark
        }
        
        if apply_watermark:
            process_config["watermark_config"] = {
                "text": watermark_text or f"© User {current_user.id}",
                "position": "bottom-right",
                "opacity": 0.5,
                "visible": True,
                "invisible": True
            }
        
        # Start batch processing
        from app.core.celery_app import celery_app
        
        task = celery_app.send_task(
            'app.workers.content.batch_process',
            args=[current_user.id, file_paths, process_config]
        )
        
        logger.info(f"Batch upload started for user {current_user.id}: {len(files)} files")
        
        return {
            "success": True,
            "batch_id": task.id,
            "file_count": len(files),
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch upload"
        )


@router.get("/upload/formats")
async def get_supported_formats() -> Any:
    """Get list of supported file formats"""
    return {
        "success": True,
        "formats": {
            "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
            "video": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"],
            "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
            "document": [".pdf", ".doc", ".docx", ".txt"]
        },
        "max_file_size": "500MB",
        "max_batch_files": 10,
        "chunk_size": "5MB"
    }


__all__ = ['router']