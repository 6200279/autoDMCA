"""
API endpoints for third-party service integrations.

Provides endpoints for:
- SendGrid email operations
- Google Vision API content analysis  
- PayPal payment processing
- Service health checks
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.service_registry import (
    get_sendgrid_service,
    get_google_vision_service,
    get_paypal_service
)
from app.api.deps.auth import get_current_user
from app.schemas.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Request/Response Models
# =============================================================================

class EmailRequest(BaseModel):
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    text_content: str = Field(..., description="Plain text content")
    html_content: Optional[str] = Field(None, description="HTML content")
    to_name: Optional[str] = Field(None, description="Recipient name")
    template_id: Optional[str] = Field(None, description="SendGrid template ID")
    template_data: Optional[Dict[str, Any]] = Field(None, description="Template data")
    categories: Optional[List[str]] = Field(None, description="Email categories")

class BulkEmailRequest(BaseModel):
    recipients: List[Dict[str, Any]] = Field(..., description="List of recipients")
    subject: str = Field(..., description="Email subject")
    text_content: str = Field(..., description="Plain text content")
    html_content: Optional[str] = Field(None, description="HTML content")
    template_id: Optional[str] = Field(None, description="SendGrid template ID")
    categories: Optional[List[str]] = Field(None, description="Email categories")

class ImageAnalysisRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    include_text: bool = Field(True, description="Include text detection")
    include_objects: bool = Field(True, description="Include object detection")
    include_faces: bool = Field(True, description="Include face detection")
    include_logos: bool = Field(False, description="Include logo detection")
    include_explicit_check: bool = Field(True, description="Include explicit content check")

class PaymentRequest(BaseModel):
    amount: str = Field(..., description="Payment amount")
    currency: str = Field("USD", description="Currency code")
    description: str = Field(..., description="Payment description")
    return_url: Optional[str] = Field(None, description="Return URL after payment")
    cancel_url: Optional[str] = Field(None, description="Cancel URL")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata")

class SubscriptionRequest(BaseModel):
    plan_type: str = Field(..., description="Subscription plan type (basic/professional)")
    interval: str = Field("monthly", description="Billing interval (monthly/yearly)")
    user_email: Optional[str] = Field(None, description="User email")

class RefundRequest(BaseModel):
    sale_id: str = Field(..., description="PayPal sale ID")
    amount: Optional[str] = Field(None, description="Refund amount (None = full refund)")
    reason: str = Field("Customer request", description="Refund reason")

# =============================================================================
# SendGrid Email Endpoints
# =============================================================================

@router.post("/sendgrid/send-email")
async def send_email(
    request: EmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a single email via SendGrid."""
    try:
        sendgrid_service = await get_sendgrid_service()
        if not sendgrid_service:
            raise HTTPException(status_code=503, detail="SendGrid service not available")
        
        success = await sendgrid_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            text_content=request.text_content,
            html_content=request.html_content,
            to_name=request.to_name,
            template_id=request.template_id,
            template_data=request.template_data,
            categories=request.categories
        )
        
        return {
            "success": success,
            "message": "Email sent successfully" if success else "Email sending failed",
            "sent_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"SendGrid email send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sendgrid/send-bulk-email")
async def send_bulk_email(
    request: BulkEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send bulk emails via SendGrid."""
    try:
        sendgrid_service = await get_sendgrid_service()
        if not sendgrid_service:
            raise HTTPException(status_code=503, detail="SendGrid service not available")
        
        result = await sendgrid_service.send_bulk_email(
            recipients=request.recipients,
            subject=request.subject,
            text_content=request.text_content,
            html_content=request.html_content,
            template_id=request.template_id,
            categories=request.categories
        )
        
        return {
            "sent_count": result.get("sent", 0),
            "failed_count": len(result.get("failed", [])),
            "failed_recipients": result.get("failed", []),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"SendGrid bulk email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sendgrid/statistics")
async def get_email_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get SendGrid email statistics."""
    try:
        sendgrid_service = await get_sendgrid_service()
        if not sendgrid_service:
            raise HTTPException(status_code=503, detail="SendGrid service not available")
        
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        categories_list = categories.split(',') if categories else None
        
        stats = await sendgrid_service.get_email_statistics(
            start_date=start_dt,
            end_date=end_dt,
            categories=categories_list
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"SendGrid statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Google Vision API Endpoints
# =============================================================================

@router.post("/google-vision/analyze-image")
async def analyze_image(
    request: ImageAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Analyze image using Google Vision API."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            raise HTTPException(status_code=503, detail="Google Vision API not available")
        
        # Decode base64 image data
        try:
            image_data = base64.b64decode(request.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        analysis = await vision_service.analyze_image_comprehensive(
            image_data=image_data,
            include_text=request.include_text,
            include_objects=request.include_objects,
            include_faces=request.include_faces,
            include_logos=request.include_logos,
            include_explicit_check=request.include_explicit_check
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Google Vision analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/google-vision/analyze-upload")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    include_text: bool = True,
    include_objects: bool = True,
    include_faces: bool = True,
    include_logos: bool = False,
    include_explicit_check: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Analyze uploaded image file using Google Vision API."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            raise HTTPException(status_code=503, detail="Google Vision API not available")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file data
        image_data = await file.read()
        
        analysis = await vision_service.analyze_image_comprehensive(
            image_data=image_data,
            include_text=include_text,
            include_objects=include_objects,
            include_faces=include_faces,
            include_logos=include_logos,
            include_explicit_check=include_explicit_check
        )
        
        # Add file metadata
        analysis['file_info'] = {
            'filename': file.filename,
            'content_type': file.content_type,
            'file_size': len(image_data)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Google Vision file analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/google-vision/detect-explicit-content")
async def detect_explicit_content(
    request: ImageAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Detect explicit content in image for content moderation."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            raise HTTPException(status_code=503, detail="Google Vision API not available")
        
        # Decode base64 image data
        try:
            image_data = base64.b64decode(request.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        result = await vision_service.detect_explicit_content(
            image_data=image_data,
            include_details=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Google Vision explicit content detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/google-vision/extract-text")
async def extract_text_from_image(
    request: ImageAnalysisRequest,
    language_hints: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Extract text from image using OCR."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            raise HTTPException(status_code=503, detail="Google Vision API not available")
        
        # Decode base64 image data
        try:
            image_data = base64.b64decode(request.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Parse language hints
        languages = language_hints.split(',') if language_hints else None
        
        result = await vision_service.detect_text(
            image_data=image_data,
            language_hints=languages
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Google Vision text extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PayPal Payment Endpoints
# =============================================================================

@router.post("/paypal/create-payment")
async def create_payment(
    request: PaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a PayPal payment."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        result = await paypal_service.create_payment(
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            return_url=request.return_url,
            cancel_url=request.cancel_url,
            metadata=request.metadata
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PayPal payment creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paypal/execute-payment")
async def execute_payment(
    payment_id: str,
    payer_id: str,
    current_user: User = Depends(get_current_user)
):
    """Execute an approved PayPal payment."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        result = await paypal_service.execute_payment(
            payment_id=payment_id,
            payer_id=payer_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PayPal payment execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paypal/create-subscription")
async def create_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a PayPal subscription."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        from app.services.integrations.paypal_service import create_subscription_checkout
        
        result = await create_subscription_checkout(
            plan_type=request.plan_type,
            interval=request.interval,
            user_email=request.user_email or current_user.email
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PayPal subscription creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paypal/cancel-subscription")
async def cancel_subscription(
    agreement_id: str,
    note: str = "Cancellation requested by user",
    current_user: User = Depends(get_current_user)
):
    """Cancel a PayPal subscription."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        result = await paypal_service.cancel_billing_agreement(
            agreement_id=agreement_id,
            note=note
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PayPal subscription cancellation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paypal/process-refund")
async def process_refund(
    request: RefundRequest,
    current_user: User = Depends(get_current_user)
):
    """Process a PayPal refund."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        result = await paypal_service.process_refund(
            sale_id=request.sale_id,
            amount=request.amount,
            reason=request.reason
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PayPal refund processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/paypal/payment-details/{payment_id}")
async def get_payment_details(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get PayPal payment details."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            raise HTTPException(status_code=503, detail="PayPal service not available")
        
        result = await paypal_service.get_payment_details(payment_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PayPal payment details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Service Health Check Endpoints
# =============================================================================

@router.get("/health-check")
async def integration_health_check(current_user: User = Depends(get_current_user)):
    """Check health of all integration services."""
    try:
        health_status = {}
        
        # Check SendGrid
        sendgrid_service = await get_sendgrid_service()
        if sendgrid_service:
            health_status['sendgrid'] = sendgrid_service.health_check()
        else:
            health_status['sendgrid'] = {
                'service': 'sendgrid',
                'status': 'not_configured'
            }
        
        # Check Google Vision
        vision_service = await get_google_vision_service()
        if vision_service:
            health_status['google_vision'] = vision_service.health_check()
        else:
            health_status['google_vision'] = {
                'service': 'google_vision',
                'status': 'not_configured'
            }
        
        # Check PayPal
        paypal_service = await get_paypal_service()
        if paypal_service:
            health_status['paypal'] = paypal_service.health_check()
        else:
            health_status['paypal'] = {
                'service': 'paypal',
                'status': 'not_configured'
            }
        
        # Overall status
        all_services = list(health_status.values())
        healthy_count = len([s for s in all_services if s.get('status') == 'healthy'])
        total_services = len(all_services)
        
        overall_status = {
            'overall_status': 'healthy' if healthy_count == total_services else 'partial',
            'healthy_services': healthy_count,
            'total_services': total_services,
            'services': health_status,
            'checked_at': datetime.utcnow().isoformat()
        }
        
        return overall_status
        
    except Exception as e:
        logger.error(f"Integration health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sendgrid/health")
async def sendgrid_health_check():
    """Check SendGrid service health."""
    try:
        sendgrid_service = await get_sendgrid_service()
        if not sendgrid_service:
            return {"service": "sendgrid", "status": "not_configured"}
        
        return sendgrid_service.health_check()
        
    except Exception as e:
        logger.error(f"SendGrid health check error: {e}")
        return {"service": "sendgrid", "status": "error", "error": str(e)}

@router.get("/google-vision/health")
async def google_vision_health_check():
    """Check Google Vision API service health."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            return {"service": "google_vision", "status": "not_configured"}
        
        return vision_service.health_check()
        
    except Exception as e:
        logger.error(f"Google Vision health check error: {e}")
        return {"service": "google_vision", "status": "error", "error": str(e)}

@router.get("/paypal/health")
async def paypal_health_check():
    """Check PayPal service health."""
    try:
        paypal_service = await get_paypal_service()
        if not paypal_service:
            return {"service": "paypal", "status": "not_configured"}
        
        return paypal_service.health_check()
        
    except Exception as e:
        logger.error(f"PayPal health check error: {e}")
        return {"service": "paypal", "status": "error", "error": str(e)}

# =============================================================================
# Background Tasks for Async Operations
# =============================================================================

async def background_image_analysis(
    image_data: bytes,
    user_id: int,
    analysis_id: str
):
    """Background task for processing large image analysis."""
    try:
        vision_service = await get_google_vision_service()
        if not vision_service:
            logger.error(f"Vision service not available for analysis {analysis_id}")
            return
        
        # Perform comprehensive analysis
        result = await vision_service.analyze_image_comprehensive(image_data)
        
        # Store results in database or cache
        # This would typically save to database with analysis_id
        logger.info(f"Background image analysis completed for {analysis_id}")
        
    except Exception as e:
        logger.error(f"Background image analysis failed for {analysis_id}: {e}")

@router.post("/google-vision/analyze-async")
async def analyze_image_async(
    background_tasks: BackgroundTasks,
    request: ImageAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Start asynchronous image analysis for large images."""
    try:
        # Generate analysis ID
        analysis_id = f"analysis_{current_user.id}_{int(datetime.utcnow().timestamp())}"
        
        # Decode image data
        try:
            image_data = base64.b64decode(request.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Start background task
        background_tasks.add_task(
            background_image_analysis,
            image_data,
            current_user.id,
            analysis_id
        )
        
        return {
            "analysis_id": analysis_id,
            "status": "processing",
            "message": "Image analysis started in background",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Async image analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))