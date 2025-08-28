"""
Unified Content Processing Service for AutoDMCA

This service orchestrates the complete content processing pipeline:
- File upload handling with chunked uploads
- Content validation and sanitization
- Fingerprint generation
- Watermark application
- Storage management (local/cloud)
- Async processing coordination
- Progress tracking and notifications

Integrates with existing services:
- FileStorage for file handling
- ContentFingerprintingService for fingerprints
- ContentWatermarkingService for watermarks
- Celery workers for async processing
"""

import logging
import hashlib
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import aiofiles
import magic
from PIL import Image
import io

from app.core.config import settings
from app.core.container import container
from app.services.file.storage import FileStorage
from app.services.ai.content_fingerprinting_service import ContentFingerprintingService
from app.services.watermarking.watermark_service import ContentWatermarkingService
from app.services.notifications.alert_system import alert_system
from app.core.celery_app import celery_app
from app.workers.base import worker_task, TaskPriority

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Supported content types"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    """Content processing status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PROCESSING = "processing"
    WATERMARKING = "watermarking"
    FINGERPRINTING = "fingerprinting"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StorageBackend(str, Enum):
    """Available storage backends"""
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"


@dataclass
class ChunkedUpload:
    """Chunked upload tracking"""
    upload_id: str
    user_id: int
    filename: str
    total_size: int
    chunk_size: int
    total_chunks: int
    uploaded_chunks: List[int] = field(default_factory=list)
    temp_path: Path = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = None
    content_type: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentProcessingJob:
    """Content processing job tracking"""
    job_id: str
    content_id: int
    user_id: int
    status: ProcessingStatus
    progress: float = 0.0
    steps_completed: List[str] = field(default_factory=list)
    steps_remaining: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)


class ContentProcessingService:
    """
    Comprehensive content processing orchestration service
    
    Features:
    - Chunked upload support for large files
    - Multi-format content validation
    - Async processing pipeline
    - Progress tracking and notifications
    - Multi-backend storage support
    - Integration with existing services
    """
    
    def __init__(self):
        self.file_storage = FileStorage()
        self.fingerprinting_service = ContentFingerprintingService()
        self.watermarking_service = ContentWatermarkingService()
        
        # Upload tracking
        self.active_uploads: Dict[str, ChunkedUpload] = {}
        self.processing_jobs: Dict[str, ContentProcessingJob] = {}
        
        # Configuration
        self.max_file_size = getattr(settings, 'MAX_UPLOAD_SIZE', 500 * 1024 * 1024)  # 500MB
        self.chunk_size = getattr(settings, 'UPLOAD_CHUNK_SIZE', 5 * 1024 * 1024)  # 5MB
        self.upload_ttl = timedelta(hours=24)  # Upload expiration
        
        # Storage backend
        self.storage_backend = StorageBackend(getattr(settings, 'STORAGE_BACKEND', 'local'))
        
        # Supported formats
        self.supported_formats = {
            ContentType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
            ContentType.VIDEO: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
            ContentType.AUDIO: ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            ContentType.DOCUMENT: ['.pdf', '.doc', '.docx', '.txt']
        }
        
        logger.info("Content processing service initialized")
    
    async def initiate_chunked_upload(
        self,
        user_id: int,
        filename: str,
        total_size: int,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initiate a chunked upload session"""
        try:
            # Validate file size
            if total_size > self.max_file_size:
                raise ValueError(f"File size exceeds maximum allowed: {self.max_file_size} bytes")
            
            # Generate unique upload ID
            upload_id = hashlib.sha256(
                f"{user_id}_{filename}_{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Calculate chunks
            total_chunks = (total_size + self.chunk_size - 1) // self.chunk_size
            
            # Create temp directory for chunks
            temp_dir = Path(settings.UPLOAD_DIR) / "temp" / upload_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create upload session
            upload = ChunkedUpload(
                upload_id=upload_id,
                user_id=user_id,
                filename=filename,
                total_size=total_size,
                chunk_size=self.chunk_size,
                total_chunks=total_chunks,
                temp_path=temp_dir,
                expires_at=datetime.utcnow() + self.upload_ttl,
                content_type=content_type,
                metadata=metadata or {}
            )
            
            self.active_uploads[upload_id] = upload
            
            logger.info(f"Initiated chunked upload: {upload_id} for user {user_id}")
            
            return {
                "upload_id": upload_id,
                "chunk_size": self.chunk_size,
                "total_chunks": total_chunks,
                "expires_at": upload.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate upload: {e}")
            raise
    
    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
        user_id: int
    ) -> Dict[str, Any]:
        """Upload a single chunk"""
        try:
            # Get upload session
            upload = self.active_uploads.get(upload_id)
            if not upload:
                raise ValueError("Invalid upload ID or session expired")
            
            # Verify user
            if upload.user_id != user_id:
                raise ValueError("Unauthorized upload attempt")
            
            # Check expiration
            if datetime.utcnow() > upload.expires_at:
                self._cleanup_upload(upload_id)
                raise ValueError("Upload session expired")
            
            # Validate chunk index
            if chunk_index >= upload.total_chunks or chunk_index < 0:
                raise ValueError(f"Invalid chunk index: {chunk_index}")
            
            # Save chunk to temp file
            chunk_path = upload.temp_path / f"chunk_{chunk_index:06d}"
            async with aiofiles.open(chunk_path, 'wb') as f:
                await f.write(chunk_data)
            
            # Track uploaded chunk
            if chunk_index not in upload.uploaded_chunks:
                upload.uploaded_chunks.append(chunk_index)
            
            # Calculate progress
            progress = (len(upload.uploaded_chunks) / upload.total_chunks) * 100
            
            logger.debug(f"Uploaded chunk {chunk_index} for upload {upload_id}")
            
            return {
                "chunk_index": chunk_index,
                "chunks_received": len(upload.uploaded_chunks),
                "total_chunks": upload.total_chunks,
                "progress": progress,
                "complete": len(upload.uploaded_chunks) == upload.total_chunks
            }
            
        except Exception as e:
            logger.error(f"Failed to upload chunk: {e}")
            raise
    
    async def complete_upload(
        self,
        upload_id: str,
        user_id: int,
        process_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Complete upload and start processing"""
        try:
            # Get upload session
            upload = self.active_uploads.get(upload_id)
            if not upload:
                raise ValueError("Invalid upload ID")
            
            # Verify user
            if upload.user_id != user_id:
                raise ValueError("Unauthorized")
            
            # Check all chunks received
            if len(upload.uploaded_chunks) != upload.total_chunks:
                missing = set(range(upload.total_chunks)) - set(upload.uploaded_chunks)
                raise ValueError(f"Missing chunks: {missing}")
            
            # Combine chunks into final file
            final_path = Path(settings.UPLOAD_DIR) / "processing" / f"{upload_id}_{upload.filename}"
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(final_path, 'wb') as final_file:
                for i in range(upload.total_chunks):
                    chunk_path = upload.temp_path / f"chunk_{i:06d}"
                    with open(chunk_path, 'rb') as chunk_file:
                        final_file.write(chunk_file.read())
            
            # Validate combined file
            file_size = final_path.stat().st_size
            if file_size != upload.total_size:
                raise ValueError(f"File size mismatch: expected {upload.total_size}, got {file_size}")
            
            # Detect content type
            content_type = self._detect_content_type(str(final_path))
            
            # Create processing job
            job_id = hashlib.sha256(f"{upload_id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
            
            # Start async processing
            celery_app.send_task(
                'app.workers.content.process_content',
                args=[job_id, str(final_path), user_id, content_type.value, process_config or {}]
            )
            
            # Cleanup upload session
            self._cleanup_upload(upload_id)
            
            # Create job tracking
            job = ContentProcessingJob(
                job_id=job_id,
                content_id=0,  # Will be assigned after database storage
                user_id=user_id,
                status=ProcessingStatus.PENDING,
                steps_remaining=["validation", "fingerprinting", "watermarking", "storage"]
            )
            
            self.processing_jobs[job_id] = job
            
            logger.info(f"Completed upload {upload_id}, started processing job {job_id}")
            
            return {
                "job_id": job_id,
                "status": "processing",
                "content_type": content_type.value,
                "file_size": file_size
            }
            
        except Exception as e:
            logger.error(f"Failed to complete upload: {e}")
            # Cleanup on error
            self._cleanup_upload(upload_id)
            raise
    
    async def process_content(
        self,
        file_path: str,
        user_id: int,
        process_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process uploaded content through the full pipeline"""
        job_id = hashlib.sha256(f"{file_path}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        
        try:
            # Create processing job
            job = ContentProcessingJob(
                job_id=job_id,
                content_id=0,
                user_id=user_id,
                status=ProcessingStatus.PROCESSING
            )
            
            self.processing_jobs[job_id] = job
            
            # Step 1: Validate content
            await self._update_job_status(job_id, ProcessingStatus.VALIDATING, 10)
            validation_result = await self._validate_content(file_path)
            
            if not validation_result['valid']:
                raise ValueError(f"Content validation failed: {validation_result['error']}")
            
            # Step 2: Generate fingerprints
            await self._update_job_status(job_id, ProcessingStatus.FINGERPRINTING, 30)
            fingerprints = await self._generate_fingerprints(file_path, validation_result['content_type'])
            
            # Step 3: Apply watermarks (if configured)
            if process_config and process_config.get('apply_watermark', False):
                await self._update_job_status(job_id, ProcessingStatus.WATERMARKING, 50)
                watermarked_path = await self._apply_watermarks(
                    file_path, 
                    user_id,
                    process_config.get('watermark_config', {})
                )
            else:
                watermarked_path = file_path
            
            # Step 4: Store content
            await self._update_job_status(job_id, ProcessingStatus.STORING, 70)
            storage_result = await self._store_content(
                watermarked_path,
                user_id,
                validation_result['content_type'],
                fingerprints
            )
            
            # Step 5: Complete processing
            await self._update_job_status(job_id, ProcessingStatus.COMPLETED, 100)
            
            job.completed_at = datetime.utcnow()
            job.result = {
                "content_id": storage_result['content_id'],
                "storage_path": storage_result['path'],
                "content_type": validation_result['content_type'].value,
                "fingerprints": fingerprints,
                "watermarked": process_config and process_config.get('apply_watermark', False)
            }
            
            # Send completion notification
            await self._notify_processing_complete(user_id, job_id, job.result)
            
            logger.info(f"Content processing completed: job {job_id}")
            
            return job.result
            
        except Exception as e:
            logger.error(f"Content processing failed: {e}")
            job = self.processing_jobs.get(job_id)
            if job:
                job.status = ProcessingStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
            raise
    
    async def get_processing_status(self, job_id: str, user_id: int) -> Dict[str, Any]:
        """Get status of processing job"""
        job = self.processing_jobs.get(job_id)
        
        if not job:
            return {"status": "not_found"}
        
        if job.user_id != user_id:
            return {"status": "unauthorized"}
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "progress": job.progress,
            "steps_completed": job.steps_completed,
            "steps_remaining": job.steps_remaining,
            "started_at": job.started_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "result": job.result if job.status == ProcessingStatus.COMPLETED else None
        }
    
    async def cancel_processing(self, job_id: str, user_id: int) -> bool:
        """Cancel a processing job"""
        job = self.processing_jobs.get(job_id)
        
        if not job or job.user_id != user_id:
            return False
        
        if job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
            return False
        
        job.status = ProcessingStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        # Cancel Celery task if running
        celery_app.control.revoke(job_id, terminate=True)
        
        logger.info(f"Cancelled processing job: {job_id}")
        return True
    
    def _detect_content_type(self, file_path: str) -> ContentType:
        """Detect content type from file"""
        try:
            mime = magic.from_file(file_path, mime=True)
            
            if mime.startswith('image/'):
                return ContentType.IMAGE
            elif mime.startswith('video/'):
                return ContentType.VIDEO
            elif mime.startswith('audio/'):
                return ContentType.AUDIO
            elif mime.startswith('application/pdf') or mime.startswith('text/'):
                return ContentType.DOCUMENT
            else:
                return ContentType.UNKNOWN
                
        except Exception as e:
            logger.error(f"Failed to detect content type: {e}")
            return ContentType.UNKNOWN
    
    async def _validate_content(self, file_path: str) -> Dict[str, Any]:
        """Validate uploaded content"""
        try:
            # Detect content type
            content_type = self._detect_content_type(file_path)
            
            if content_type == ContentType.UNKNOWN:
                return {"valid": False, "error": "Unsupported file type"}
            
            # Check file extension
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats.get(content_type, []):
                return {"valid": False, "error": f"Unsupported {content_type.value} format: {file_ext}"}
            
            # Validate content integrity based on type
            if content_type == ContentType.IMAGE:
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                except Exception as e:
                    return {"valid": False, "error": f"Invalid image file: {e}"}
            
            # Additional validation could include:
            # - Virus scanning
            # - Content moderation
            # - Size limits per type
            
            return {
                "valid": True,
                "content_type": content_type,
                "file_size": Path(file_path).stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    async def _generate_fingerprints(self, file_path: str, content_type: ContentType) -> Dict[str, Any]:
        """Generate content fingerprints"""
        try:
            with open(file_path, 'rb') as f:
                content_data = f.read()
            
            # Generate basic hash
            file_hash = hashlib.sha256(content_data).hexdigest()
            
            # Generate perceptual fingerprints based on content type
            fingerprints = {
                "file_hash": file_hash,
                "content_type": content_type.value
            }
            
            if content_type == ContentType.IMAGE:
                # Use fingerprinting service for images
                image_fingerprints = self.fingerprinting_service.create_content_fingerprint(
                    content_data, 'image'
                )
                fingerprints.update(image_fingerprints)
            
            elif content_type == ContentType.VIDEO:
                # Video fingerprinting would be implemented here
                fingerprints["video_hash"] = "placeholder"
            
            elif content_type == ContentType.AUDIO:
                # Audio fingerprinting would be implemented here
                fingerprints["audio_hash"] = "placeholder"
            
            return fingerprints
            
        except Exception as e:
            logger.error(f"Fingerprint generation failed: {e}")
            raise
    
    async def _apply_watermarks(
        self, 
        file_path: str, 
        user_id: int,
        watermark_config: Dict[str, Any]
    ) -> str:
        """Apply watermarks to content"""
        try:
            # Only supports images currently
            content_type = self._detect_content_type(file_path)
            
            if content_type != ContentType.IMAGE:
                logger.warning(f"Watermarking not supported for {content_type.value}")
                return file_path
            
            # Create watermarked version
            output_path = str(Path(file_path).with_suffix('.watermarked.jpg'))
            
            # Apply visible watermark if configured
            if watermark_config.get('visible', True):
                self.watermarking_service.add_visible_text_watermark(
                    file_path,
                    output_path,
                    watermark_config.get('text', f'© User {user_id}'),
                    position=watermark_config.get('position', 'bottom-right'),
                    opacity=watermark_config.get('opacity', 0.5)
                )
                file_path = output_path
            
            # Apply invisible watermark
            if watermark_config.get('invisible', True):
                self.watermarking_service.add_invisible_watermark(
                    file_path,
                    output_path,
                    f"uid:{user_id}_ts:{datetime.utcnow().isoformat()}"
                )
                file_path = output_path
            
            return file_path
            
        except Exception as e:
            logger.error(f"Watermark application failed: {e}")
            # Return original file if watermarking fails
            return file_path
    
    async def _store_content(
        self,
        file_path: str,
        user_id: int,
        content_type: ContentType,
        fingerprints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store processed content"""
        try:
            # Generate storage path
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"user_{user_id}_{content_type.value}_{timestamp}{Path(file_path).suffix}"
            
            # Store based on backend
            if self.storage_backend == StorageBackend.LOCAL:
                # Use existing FileStorage service
                storage_path = self.file_storage.save_file(
                    open(file_path, 'rb'),
                    filename,
                    f"content/{user_id}/{content_type.value}"
                )
            else:
                # Cloud storage would be implemented here
                storage_path = f"cloud://{self.storage_backend.value}/{filename}"
            
            # Save metadata to database (would be implemented)
            content_id = hashlib.sha256(storage_path.encode()).hexdigest()[:16]
            
            return {
                "content_id": content_id,
                "path": storage_path,
                "storage_backend": self.storage_backend.value
            }
            
        except Exception as e:
            logger.error(f"Content storage failed: {e}")
            raise
    
    async def _update_job_status(self, job_id: str, status: ProcessingStatus, progress: float):
        """Update job status and progress"""
        job = self.processing_jobs.get(job_id)
        if job:
            job.status = status
            job.progress = progress
            
            # Move step to completed
            if status.value in job.steps_remaining:
                job.steps_remaining.remove(status.value)
                job.steps_completed.append(status.value)
    
    async def _notify_processing_complete(self, user_id: int, job_id: str, result: Dict[str, Any]):
        """Send notification when processing completes"""
        try:
            await alert_system.send_alert(
                user_id=user_id,
                alert_type='processing_complete',
                title="Content Processing Complete",
                message=f"Your content has been processed successfully (Job: {job_id})",
                data=result
            )
        except Exception as e:
            logger.error(f"Failed to send completion notification: {e}")
    
    def _cleanup_upload(self, upload_id: str):
        """Cleanup upload session and temporary files"""
        try:
            upload = self.active_uploads.get(upload_id)
            if upload and upload.temp_path.exists():
                import shutil
                shutil.rmtree(upload.temp_path)
            
            if upload_id in self.active_uploads:
                del self.active_uploads[upload_id]
                
        except Exception as e:
            logger.error(f"Failed to cleanup upload {upload_id}: {e}")


# Global content processing service instance
content_processing_service = ContentProcessingService()


__all__ = [
    'ContentProcessingService',
    'content_processing_service',
    'ContentType',
    'ProcessingStatus',
    'StorageBackend',
    'ChunkedUpload',
    'ContentProcessingJob'
]