"""
Content Processing Workers for AutoDMCA

Celery workers that handle asynchronous content processing tasks:
- Content validation and analysis
- Fingerprint generation
- Watermark application  
- Storage operations
- Batch processing
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.core.celery_app import celery_app
from app.workers.base import BaseWorkerTask, worker_task, TaskPriority, TaskStatus
from app.services.content.content_processing_service import (
    content_processing_service,
    ContentType,
    ProcessingStatus
)
from app.services.ai.content_fingerprinting_service import ContentFingerprintingService
from app.services.watermarking.watermark_service import ContentWatermarkingService
from app.services.file.storage import FileStorage
from app.services.notifications.alert_system import alert_system

logger = logging.getLogger(__name__)


class ContentProcessorWorker(BaseWorkerTask):
    """Main content processing worker"""
    
    def __init__(self):
        super().__init__()
        self.fingerprinting_service = ContentFingerprintingService()
        self.watermarking_service = ContentWatermarkingService()
        self.file_storage = FileStorage()
    
    @worker_task(
        name='app.workers.content.process_content',
        priority=TaskPriority.HIGH,
        queue='content_processing',
        max_retries=3
    )
    async def process_content(
        self,
        job_id: str,
        file_path: str,
        user_id: int,
        content_type: str,
        process_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process uploaded content through the full pipeline
        
        Args:
            job_id: Processing job ID
            file_path: Path to uploaded file
            user_id: User ID
            content_type: Type of content (image/video/audio)
            process_config: Processing configuration
        
        Returns:
            Processing result with content ID and metadata
        """
        try:
            logger.info(f"Starting content processing: job {job_id}")
            
            # Run async processing in event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._process_content_sync,
                job_id, file_path, user_id, content_type, process_config
            )
            
            # Notify completion
            await self._notify_completion(user_id, job_id, result)
            
            logger.info(f"Content processing completed: job {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Content processing failed for job {job_id}: {e}")
            await self._notify_failure(user_id, job_id, str(e))
            raise
    
    def _process_content_sync(
        self,
        job_id: str,
        file_path: str,
        user_id: int,
        content_type: str,
        process_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous content processing implementation"""
        
        result = {
            "job_id": job_id,
            "user_id": user_id,
            "content_type": content_type,
            "steps": {}
        }
        
        try:
            # Step 1: Validate content
            self._update_progress(job_id, "validating", 10)
            validation_result = self._validate_content(file_path, content_type)
            result["steps"]["validation"] = validation_result
            
            if not validation_result.get("valid", False):
                raise ValueError(f"Content validation failed: {validation_result.get('error')}")
            
            # Step 2: Generate fingerprints
            self._update_progress(job_id, "fingerprinting", 30)
            fingerprints = self._generate_fingerprints(file_path, content_type)
            result["steps"]["fingerprints"] = fingerprints
            
            # Step 3: Apply watermarks (if configured)
            watermarked_path = file_path
            if process_config.get("apply_watermark", False):
                self._update_progress(job_id, "watermarking", 50)
                watermarked_path = self._apply_watermarks(
                    file_path,
                    user_id,
                    process_config.get("watermark_config", {})
                )
                result["steps"]["watermark"] = {
                    "applied": True,
                    "path": watermarked_path
                }
            
            # Step 4: Store content
            self._update_progress(job_id, "storing", 70)
            storage_result = self._store_content(
                watermarked_path,
                user_id,
                content_type,
                fingerprints
            )
            result["steps"]["storage"] = storage_result
            
            # Step 5: Register in database
            self._update_progress(job_id, "registering", 90)
            content_id = self._register_content(
                user_id,
                file_path,
                content_type,
                fingerprints,
                storage_result
            )
            result["content_id"] = content_id
            
            # Complete
            self._update_progress(job_id, "completed", 100)
            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Processing error in job {job_id}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            raise
    
    def _validate_content(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """Validate content file"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {"valid": False, "error": "File not found"}
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                return {"valid": False, "error": "Empty file"}
            
            # Type-specific validation
            if content_type == "image":
                from PIL import Image
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                        width, height = img.size
                        return {
                            "valid": True,
                            "dimensions": f"{width}x{height}",
                            "format": img.format,
                            "size": file_size
                        }
                except Exception as e:
                    return {"valid": False, "error": f"Invalid image: {e}"}
            
            # Default validation for other types
            return {
                "valid": True,
                "size": file_size,
                "type": content_type
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {"valid": False, "error": str(e)}
    
    def _generate_fingerprints(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """Generate content fingerprints"""
        try:
            import hashlib
            
            # Basic file hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            fingerprints = {
                "file_hash": file_hash,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Type-specific fingerprints
            if content_type == "image":
                # Use existing fingerprinting service
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                image_fingerprints = self.fingerprinting_service.create_content_fingerprint(
                    image_data, 'image'
                )
                fingerprints.update(image_fingerprints)
            
            return fingerprints
            
        except Exception as e:
            logger.error(f"Fingerprinting error: {e}")
            return {"error": str(e)}
    
    def _apply_watermarks(
        self,
        file_path: str,
        user_id: int,
        config: Dict[str, Any]
    ) -> str:
        """Apply watermarks to content"""
        try:
            output_path = str(Path(file_path).with_suffix('.watermarked.jpg'))
            
            # Apply visible watermark
            if config.get("visible", True):
                self.watermarking_service.add_visible_text_watermark(
                    file_path,
                    output_path,
                    config.get("text", f"© User {user_id}"),
                    position=config.get("position", "bottom-right"),
                    opacity=config.get("opacity", 0.5)
                )
                file_path = output_path
            
            # Apply invisible watermark
            if config.get("invisible", True):
                self.watermarking_service.add_invisible_watermark(
                    file_path,
                    output_path,
                    f"uid:{user_id}"
                )
                file_path = output_path
            
            return file_path
            
        except Exception as e:
            logger.error(f"Watermarking error: {e}")
            return file_path  # Return original if watermarking fails
    
    def _store_content(
        self,
        file_path: str,
        user_id: int,
        content_type: str,
        fingerprints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store content in storage backend"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"user_{user_id}_{content_type}_{timestamp}{Path(file_path).suffix}"
            
            # Store file
            with open(file_path, 'rb') as f:
                storage_path = self.file_storage.save_file(
                    f,
                    filename,
                    f"content/{user_id}/{content_type}"
                )
            
            return {
                "path": storage_path,
                "filename": filename,
                "stored_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Storage error: {e}")
            raise
    
    def _register_content(
        self,
        user_id: int,
        file_path: str,
        content_type: str,
        fingerprints: Dict[str, Any],
        storage_result: Dict[str, Any]
    ) -> str:
        """Register content in database"""
        # This would save to database
        # For now, generate a content ID
        import hashlib
        content_id = hashlib.sha256(
            f"{user_id}_{file_path}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        logger.info(f"Registered content: {content_id}")
        return content_id
    
    def _update_progress(self, job_id: str, stage: str, progress: int):
        """Update job progress"""
        logger.debug(f"Job {job_id}: {stage} ({progress}%)")
        # This would update the job tracking in the service
    
    async def _notify_completion(self, user_id: int, job_id: str, result: Dict[str, Any]):
        """Send completion notification"""
        try:
            await alert_system.send_alert(
                user_id=user_id,
                alert_type='processing_complete',
                title="Content Processing Complete",
                message=f"Your content has been processed (Job: {job_id})",
                data=result
            )
        except Exception as e:
            logger.error(f"Failed to send completion notification: {e}")
    
    async def _notify_failure(self, user_id: int, job_id: str, error: str):
        """Send failure notification"""
        try:
            await alert_system.send_alert(
                user_id=user_id,
                alert_type='processing_failed',
                title="Content Processing Failed",
                message=f"Processing failed for job {job_id}: {error}",
                data={"job_id": job_id, "error": error}
            )
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")


class BatchContentProcessor(BaseWorkerTask):
    """Batch content processing worker"""
    
    @worker_task(
        name='app.workers.content.batch_process',
        priority=TaskPriority.LOW,
        queue='content_processing',
        max_retries=2
    )
    async def batch_process_content(
        self,
        user_id: int,
        file_paths: List[str],
        process_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process multiple content files in batch
        
        Args:
            user_id: User ID
            file_paths: List of file paths to process
            process_config: Processing configuration
        
        Returns:
            Batch processing results
        """
        try:
            logger.info(f"Starting batch processing for {len(file_paths)} files")
            
            results = {
                "total": len(file_paths),
                "successful": 0,
                "failed": 0,
                "results": []
            }
            
            processor = ContentProcessorWorker()
            
            for file_path in file_paths:
                try:
                    # Generate job ID for each file
                    import hashlib
                    job_id = hashlib.sha256(
                        f"{file_path}_{datetime.utcnow().isoformat()}".encode()
                    ).hexdigest()[:16]
                    
                    # Detect content type
                    import magic
                    mime = magic.from_file(file_path, mime=True)
                    if mime.startswith('image/'):
                        content_type = 'image'
                    elif mime.startswith('video/'):
                        content_type = 'video'
                    elif mime.startswith('audio/'):
                        content_type = 'audio'
                    else:
                        content_type = 'document'
                    
                    # Process file
                    result = processor._process_content_sync(
                        job_id,
                        file_path,
                        user_id,
                        content_type,
                        process_config
                    )
                    
                    results["successful"] += 1
                    results["results"].append({
                        "file": file_path,
                        "status": "success",
                        "content_id": result.get("content_id")
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results["failed"] += 1
                    results["results"].append({
                        "file": file_path,
                        "status": "failed",
                        "error": str(e)
                    })
            
            logger.info(f"Batch processing completed: {results['successful']}/{results['total']} successful")
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise


# Create worker instances
content_processor = ContentProcessorWorker()
batch_processor = BatchContentProcessor()

# Register tasks with Celery
celery_app.register_task(content_processor.process_content)
celery_app.register_task(batch_processor.batch_process_content)


__all__ = [
    'ContentProcessorWorker',
    'BatchContentProcessor',
    'content_processor',
    'batch_processor'
]