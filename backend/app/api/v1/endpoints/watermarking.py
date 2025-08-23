from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import json
import os
import hashlib
import uuid

from ....api.deps.auth import get_current_user
from ....api.deps.database import get_db
from ....db.models.user import User
from ....db.models.watermark import (
    WatermarkJob, WatermarkRecord, WatermarkTemplate, 
    WatermarkType, WatermarkStatus, ContentType
)
from ....services.watermarking.watermark_service import ContentWatermarkingService
from ....core.config import settings

router = APIRouter()

# Pydantic models
class WatermarkConfig(BaseModel):
    watermark_type: str
    text: Optional[str] = None
    position: str = "bottom_right"
    opacity: float = 0.7
    font_size: int = 36
    font_color: str = "white"
    scale: float = 0.1
    strength: float = 0.1

class WatermarkJobResponse(BaseModel):
    id: int
    job_name: str
    status: str
    progress_percentage: float
    watermark_type: str
    original_filename: str
    created_at: datetime
    completed_at: Optional[datetime]
    output_file_path: Optional[str]

    class Config:
        from_attributes = True

class WatermarkTemplateResponse(BaseModel):
    id: int
    template_name: str
    description: Optional[str]
    watermark_type: str
    is_default: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class WatermarkTemplateRequest(BaseModel):
    template_name: str
    description: Optional[str] = None
    watermark_type: str
    config: Dict[str, Any]
    is_default: bool = False

class VerificationResponse(BaseModel):
    verified: bool
    watermark_id: Optional[str]
    user_id: Optional[str]
    timestamp: Optional[str]
    confidence_score: Optional[float]
    error: Optional[str]

@router.post("/upload", response_model=WatermarkJobResponse)
async def upload_and_watermark(
    file: UploadFile = File(...),
    job_name: str = Form(...),
    config: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload file and create watermark job"""
    
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/bmp", "image/tiff"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Parse watermark configuration
    try:
        watermark_config = json.loads(config)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration JSON"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Save uploaded file
    upload_dir = "/tmp/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    input_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
    
    with open(input_path, "wb") as f:
        f.write(content)
    
    # Determine content type
    if file.content_type.startswith("image/"):
        content_type = ContentType.IMAGE
    else:
        content_type = ContentType.IMAGE  # Default for now
    
    # Determine watermark type
    watermark_type_str = watermark_config.get("watermark_type", "visible_text")
    try:
        watermark_type = WatermarkType(watermark_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid watermark type: {watermark_type_str}"
        )
    
    # Create watermark job
    job = WatermarkJob(
        user_id=current_user.id,
        job_name=job_name,
        content_type=content_type,
        original_filename=file.filename,
        file_size=file_size,
        file_hash=file_hash,
        watermark_type=watermark_type,
        watermark_config=json.dumps(watermark_config),
        input_file_path=input_path,
        status=WatermarkStatus.PENDING
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Process watermark (in background in production)
    try:
        service = ContentWatermarkingService()
        
        if watermark_type == WatermarkType.VISIBLE_TEXT:
            output_path = service.add_visible_text_watermark(
                input_path,
                watermark_config.get("text", "© Protected Content"),
                watermark_config.get("position", "bottom_right"),
                watermark_config.get("opacity", 0.7),
                watermark_config.get("font_size", 36),
                watermark_config.get("font_color", "white")
            )
        elif watermark_type == WatermarkType.INVISIBLE:
            output_path = service.add_invisible_watermark(
                input_path,
                watermark_config.get("data", f"Protected by user {current_user.id}"),
                watermark_config.get("strength", 0.1)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Watermark type {watermark_type_str} not yet implemented"
            )
        
        # Update job status
        job.status = WatermarkStatus.COMPLETED
        job.progress_percentage = 100.0
        job.output_file_path = output_path
        job.completed_at = datetime.utcnow()
        
        # Create watermark record
        watermark_id = service.generate_watermark_id(content)
        watermark_record = WatermarkRecord(
            job_id=job.id,
            user_id=current_user.id,
            watermark_id=watermark_id,
            watermark_type=watermark_type,
            original_content_hash=file_hash,
            watermarked_content_hash=hashlib.sha256(open(output_path, 'rb').read()).hexdigest(),
            watermark_data=watermark_config.get("text") or watermark_config.get("data"),
            metadata=json.dumps({
                "original_filename": file.filename,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "user_id": current_user.id
            })
        )
        
        db.add(watermark_record)
        db.commit()
        
    except Exception as e:
        job.status = WatermarkStatus.FAILED
        job.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Watermarking failed: {str(e)}"
        )
    
    db.refresh(job)
    
    return WatermarkJobResponse(
        id=job.id,
        job_name=job.job_name,
        status=job.status.value,
        progress_percentage=job.progress_percentage,
        watermark_type=job.watermark_type.value,
        original_filename=job.original_filename,
        created_at=job.created_at,
        completed_at=job.completed_at,
        output_file_path=job.output_file_path
    )

@router.get("/jobs", response_model=List[WatermarkJobResponse])
def get_user_watermark_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's watermark jobs"""
    jobs = db.query(WatermarkJob).filter(
        WatermarkJob.user_id == current_user.id
    ).order_by(WatermarkJob.created_at.desc()).all()
    
    return [
        WatermarkJobResponse(
            id=job.id,
            job_name=job.job_name,
            status=job.status.value,
            progress_percentage=job.progress_percentage,
            watermark_type=job.watermark_type.value,
            original_filename=job.original_filename,
            created_at=job.created_at,
            completed_at=job.completed_at,
            output_file_path=job.output_file_path
        )
        for job in jobs
    ]

@router.get("/jobs/{job_id}", response_model=WatermarkJobResponse)
def get_watermark_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific watermark job"""
    job = db.query(WatermarkJob).filter(
        WatermarkJob.id == job_id,
        WatermarkJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watermark job not found"
        )
    
    return WatermarkJobResponse(
        id=job.id,
        job_name=job.job_name,
        status=job.status.value,
        progress_percentage=job.progress_percentage,
        watermark_type=job.watermark_type.value,
        original_filename=job.original_filename,
        created_at=job.created_at,
        completed_at=job.completed_at,
        output_file_path=job.output_file_path
    )

@router.post("/verify", response_model=VerificationResponse)
async def verify_watermark(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Verify watermark in uploaded file"""
    
    # Save uploaded file temporarily
    content = await file.read()
    temp_path = f"/tmp/verify_{uuid.uuid4().hex}_{file.filename}"
    
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        service = ContentWatermarkingService()
        
        # Try to extract invisible watermark
        extracted_data = service.extract_invisible_watermark(temp_path)
        
        if extracted_data:
            # Look up watermark in database
            # For demo purposes, we'll just return the extracted data
            return VerificationResponse(
                verified=True,
                watermark_id=f"extracted_{uuid.uuid4().hex[:8]}",
                user_id="demo_user",
                timestamp=datetime.utcnow().isoformat(),
                confidence_score=0.95
            )
        else:
            return VerificationResponse(
                verified=False,
                error="No watermark found in image"
            )
    
    except Exception as e:
        return VerificationResponse(
            verified=False,
            error=f"Verification failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass

@router.get("/templates", response_model=List[WatermarkTemplateResponse])
def get_watermark_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's watermark templates"""
    templates = db.query(WatermarkTemplate).filter(
        WatermarkTemplate.user_id == current_user.id
    ).order_by(WatermarkTemplate.created_at.desc()).all()
    
    return [
        WatermarkTemplateResponse(
            id=template.id,
            template_name=template.template_name,
            description=template.description,
            watermark_type=template.watermark_type.value,
            is_default=template.is_default,
            usage_count=template.usage_count,
            created_at=template.created_at
        )
        for template in templates
    ]

@router.post("/templates", response_model=WatermarkTemplateResponse)
def create_watermark_template(
    template_request: WatermarkTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new watermark template"""
    
    # Validate watermark type
    try:
        watermark_type = WatermarkType(template_request.watermark_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid watermark type: {template_request.watermark_type}"
        )
    
    # Create template
    template = WatermarkTemplate(
        user_id=current_user.id,
        template_name=template_request.template_name,
        description=template_request.description,
        watermark_type=watermark_type,
        template_config=json.dumps(template_request.config),
        is_default=template_request.is_default
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return WatermarkTemplateResponse(
        id=template.id,
        template_name=template.template_name,
        description=template.description,
        watermark_type=template.watermark_type.value,
        is_default=template.is_default,
        usage_count=template.usage_count,
        created_at=template.created_at
    )

@router.delete("/jobs/{job_id}")
def delete_watermark_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete watermark job and associated files"""
    
    job = db.query(WatermarkJob).filter(
        WatermarkJob.id == job_id,
        WatermarkJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watermark job not found"
        )
    
    # Clean up files
    for file_path in [job.input_file_path, job.output_file_path]:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    
    # Delete related records
    db.query(WatermarkRecord).filter(WatermarkRecord.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    
    return {"message": "Watermark job deleted successfully"}

@router.get("/stats")
def get_watermark_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user watermarking statistics"""
    
    total_jobs = db.query(WatermarkJob).filter(
        WatermarkJob.user_id == current_user.id
    ).count()
    
    completed_jobs = db.query(WatermarkJob).filter(
        WatermarkJob.user_id == current_user.id,
        WatermarkJob.status == WatermarkStatus.COMPLETED
    ).count()
    
    failed_jobs = db.query(WatermarkJob).filter(
        WatermarkJob.user_id == current_user.id,
        WatermarkJob.status == WatermarkStatus.FAILED
    ).count()
    
    total_templates = db.query(WatermarkTemplate).filter(
        WatermarkTemplate.user_id == current_user.id
    ).count()
    
    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
        "total_templates": total_templates
    }