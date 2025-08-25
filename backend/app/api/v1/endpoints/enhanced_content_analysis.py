"""
API endpoints for enhanced content analysis with fingerprinting
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps.common import get_db
from app.api.deps.auth import get_current_user
from app.services.ai.enhanced_content_matcher import (
    EnhancedContentMatcher,
    EnhancedContentMatch,
    create_enhanced_content_matcher
)
from app.db.models.user import User
from app.db.models.content_fingerprint import (
    ContentFingerprint as ContentFingerprintModel,
    FingerprintMatch as FingerprintMatchModel,
    ContentRiskAssessment,
    PiracyPattern
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Response models
class FingerprintAnalysisResponse(BaseModel):
    """Response model for fingerprint analysis"""
    content_hash: str
    fingerprint_type: str
    confidence: float
    matches_found: int
    risk_assessment: Dict[str, Any]
    processing_time_ms: float
    matches: List[Dict[str, Any]] = Field(default_factory=list)


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment"""
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., regex="^(LOW|MEDIUM|HIGH)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    factors: Dict[str, Any]
    recommendations: List[str]
    prediction_metadata: Dict[str, Any] = Field(default_factory=dict)


class PiracyPatternsResponse(BaseModel):
    """Response model for piracy patterns analysis"""
    total_incidents: int
    pattern_clusters: int
    high_risk_indicators: List[str]
    temporal_patterns: Dict[str, Any]
    platform_patterns: Dict[str, Any]
    analysis_confidence: float


class ContentMetadata(BaseModel):
    """Request model for content metadata"""
    content_type: str
    platform: Optional[str] = None
    upload_time: Optional[str] = None
    size: Optional[int] = None
    duration: Optional[float] = None
    description: Optional[str] = None


# Global matcher instance (in production, use dependency injection)
_matcher_instance: Optional[EnhancedContentMatcher] = None


async def get_enhanced_matcher() -> EnhancedContentMatcher:
    """Get enhanced content matcher instance"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = await create_enhanced_content_matcher()
    return _matcher_instance


@router.post("/analyze-content", response_model=FingerprintAnalysisResponse)
async def analyze_content_with_fingerprinting(
    file: UploadFile = File(...),
    source_url: str = Form(...),
    profile_id: int = Form(...),
    enable_fingerprinting: bool = Form(True),
    enable_risk_assessment: bool = Form(True),
    similarity_threshold: float = Form(0.8),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    matcher: EnhancedContentMatcher = Depends(get_enhanced_matcher)
):
    """
    Analyze content using enhanced fingerprinting and pattern recognition
    
    This endpoint provides:
    - Advanced audio/video fingerprinting
    - Enhanced perceptual image hashing
    - ML-based pattern recognition
    - Risk assessment for content
    """
    import time
    start_time = time.time()
    
    try:
        # Read file content
        content_data = await file.read()
        
        if len(content_data) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(content_data) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        
        # Configure matcher
        matcher.configure_fingerprinting(
            enable_fingerprinting=enable_fingerprinting,
            enable_risk_assessment=enable_risk_assessment,
            similarity_threshold=similarity_threshold
        )
        
        # Get profile data (simplified - in production, fetch from database)
        profile_data = {
            'profile_id': profile_id,
            'user_id': current_user.id,
            'source_url': source_url,
            # Add face encodings and other profile data as needed
            'face_encodings': [],  # Would be fetched from profile
            'follower_count': 10000  # Mock data
        }
        
        # Run enhanced analysis
        matches = await matcher.analyze_content_enhanced(
            content_url=source_url,
            content_data=content_data,
            profile_data=profile_data,
            user_id=str(current_user.id),
            client_ip="unknown",  # In production, extract from request
            db=db
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Format matches for response
        formatted_matches = []
        risk_assessment = {}
        
        for match in matches:
            match_data = {
                'match_type': match.match_type.value if hasattr(match.match_type, 'value') else str(match.match_type),
                'confidence': match.confidence,
                'source_url': match.source_url,
                'matched_content_id': match.matched_content_id,
                'fingerprint_similarity': match.fingerprint_similarity,
                'fingerprint_type': match.fingerprint_type.value if match.fingerprint_type else None,
                'metadata': match.metadata,
                'timestamp': match.timestamp.isoformat()
            }
            
            # Extract risk assessment from first match that has it
            if match.risk_assessment and not risk_assessment:
                risk_assessment = match.risk_assessment
            
            formatted_matches.append(match_data)
        
        # Create content hash for response
        import hashlib
        content_hash = hashlib.sha256(content_data).hexdigest()
        
        # Determine fingerprint type
        fingerprint_type = matcher._determine_fingerprint_type(content_data).value
        
        return FingerprintAnalysisResponse(
            content_hash=content_hash,
            fingerprint_type=fingerprint_type,
            confidence=max([m.confidence for m in matches], default=0.0),
            matches_found=len([m for m in matches if not m.metadata.get('risk_warning', False)]),
            risk_assessment=risk_assessment,
            processing_time_ms=processing_time_ms,
            matches=formatted_matches
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced content analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/assess-risk", response_model=RiskAssessmentResponse)
async def assess_content_risk(
    file: UploadFile = File(...),
    metadata: str = Form(...),  # JSON string of ContentMetadata
    profile_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    matcher: EnhancedContentMatcher = Depends(get_enhanced_matcher)
):
    """
    Assess piracy risk for content without full fingerprinting analysis
    Faster endpoint for risk scoring
    """
    try:
        import json
        
        # Parse metadata
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
        
        # Read file content
        content_data = await file.read()
        
        if len(content_data) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Get profile data
        profile_data = {
            'profile_id': profile_id,
            'user_id': current_user.id,
            'follower_count': 10000  # Mock data - would be fetched from profile
        }
        
        # Get risk assessment
        risk_data = await matcher.get_content_risk_score(
            content_data=content_data,
            profile_data=profile_data,
            db=db
        )
        
        return RiskAssessmentResponse(
            risk_score=risk_data.get('risk_score', 0.5),
            risk_level=risk_data.get('risk_level', 'MEDIUM'),
            confidence=risk_data.get('confidence', 0.5),
            factors=risk_data.get('factors', {}),
            recommendations=risk_data.get('recommendations', []),
            prediction_metadata={
                'model_version': '1.0',
                'analysis_time': risk_data.get('analysis_time', 'unknown')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in risk assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")


@router.get("/piracy-patterns/{profile_id}", response_model=PiracyPatternsResponse)
async def analyze_piracy_patterns(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    matcher: EnhancedContentMatcher = Depends(get_enhanced_matcher)
):
    """
    Analyze historical piracy patterns for a creator profile
    Provides insights into when and where piracy typically occurs
    """
    try:
        # Verify user has access to this profile
        # In production, add proper authorization check
        
        patterns = await matcher.analyze_historical_patterns(profile_id, db)
        
        if patterns.get('error'):
            raise HTTPException(status_code=500, detail=patterns['error'])
        
        if patterns.get('insufficient_data'):
            raise HTTPException(status_code=404, detail="Insufficient historical data for pattern analysis")
        
        return PiracyPatternsResponse(
            total_incidents=patterns.get('total_incidents', 0),
            pattern_clusters=patterns.get('pattern_clusters', 0),
            high_risk_indicators=patterns.get('high_risk_indicators', []),
            temporal_patterns=patterns.get('temporal_patterns', {}),
            platform_patterns=patterns.get('platform_patterns', {}),
            analysis_confidence=0.8  # Mock confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing piracy patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@router.get("/fingerprints/{profile_id}")
async def get_content_fingerprints(
    profile_id: int,
    fingerprint_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get content fingerprints for a profile
    Useful for understanding what content has been analyzed
    """
    try:
        # Verify user has access to this profile
        # In production, add proper authorization check
        
        query = db.query(ContentFingerprintModel).filter(
            ContentFingerprintModel.profile_id == profile_id
        )
        
        if fingerprint_type:
            query = query.filter(ContentFingerprintModel.fingerprint_type == fingerprint_type)
        
        fingerprints = query.offset(offset).limit(limit).all()
        
        result = []
        for fp in fingerprints:
            result.append({
                'id': fp.id,
                'content_hash': fp.content_hash,
                'fingerprint_type': fp.fingerprint_type,
                'confidence': fp.confidence,
                'source_url': fp.source_url,
                'file_size': fp.file_size,
                'created_at': fp.created_at.isoformat() if fp.created_at else None,
                'matches_count': len(fp.query_matches)
            })
        
        return {
            'fingerprints': result,
            'total': len(result),
            'offset': offset,
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"Error getting fingerprints: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get fingerprints: {str(e)}")


@router.get("/matches/{fingerprint_id}")
async def get_fingerprint_matches(
    fingerprint_id: int,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get matches for a specific fingerprint
    Shows what other content was detected as similar
    """
    try:
        # Verify user has access to this fingerprint
        fingerprint = db.query(ContentFingerprintModel).filter(
            ContentFingerprintModel.id == fingerprint_id
        ).first()
        
        if not fingerprint:
            raise HTTPException(status_code=404, detail="Fingerprint not found")
        
        # In production, add proper authorization check for profile access
        
        matches = db.query(FingerprintMatchModel).filter(
            FingerprintMatchModel.query_fingerprint_id == fingerprint_id
        ).offset(offset).limit(limit).all()
        
        result = []
        for match in matches:
            result.append({
                'id': match.id,
                'matched_fingerprint_id': match.matched_fingerprint_id,
                'similarity_score': match.similarity_score,
                'match_confidence': match.match_confidence,
                'comparison_method': match.comparison_method,
                'is_confirmed_match': match.is_confirmed_match,
                'reviewed_by_human': match.reviewed_by_human,
                'notes': match.notes,
                'created_at': match.created_at.isoformat() if match.created_at else None,
                'matched_content': {
                    'content_hash': match.matched_fingerprint.content_hash,
                    'source_url': match.matched_fingerprint.source_url,
                    'fingerprint_type': match.matched_fingerprint.fingerprint_type
                } if match.matched_fingerprint else None
            })
        
        return {
            'matches': result,
            'fingerprint': {
                'id': fingerprint.id,
                'content_hash': fingerprint.content_hash,
                'fingerprint_type': fingerprint.fingerprint_type,
                'source_url': fingerprint.source_url
            },
            'total': len(result),
            'offset': offset,
            'limit': limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fingerprint matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get matches: {str(e)}")


@router.post("/configure-fingerprinting")
async def configure_fingerprinting_settings(
    enable_fingerprinting: bool = True,
    enable_risk_assessment: bool = True,
    similarity_threshold: float = 0.8,
    current_user: User = Depends(get_current_user),
    matcher: EnhancedContentMatcher = Depends(get_enhanced_matcher)
):
    """
    Configure fingerprinting settings for the current session
    """
    try:
        if not 0.1 <= similarity_threshold <= 1.0:
            raise HTTPException(
                status_code=400, 
                detail="Similarity threshold must be between 0.1 and 1.0"
            )
        
        matcher.configure_fingerprinting(
            enable_fingerprinting=enable_fingerprinting,
            enable_risk_assessment=enable_risk_assessment,
            similarity_threshold=similarity_threshold
        )
        
        return {
            'message': 'Fingerprinting settings configured successfully',
            'settings': {
                'enable_fingerprinting': enable_fingerprinting,
                'enable_risk_assessment': enable_risk_assessment,
                'similarity_threshold': similarity_threshold
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring fingerprinting: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")


@router.get("/statistics/{profile_id}")
async def get_fingerprinting_statistics(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get fingerprinting statistics for a profile
    """
    try:
        # Verify user has access to this profile
        # In production, add proper authorization check
        
        # Count fingerprints by type
        fingerprint_counts = db.query(
            ContentFingerprintModel.fingerprint_type,
            db.func.count(ContentFingerprintModel.id).label('count')
        ).filter(
            ContentFingerprintModel.profile_id == profile_id
        ).group_by(ContentFingerprintModel.fingerprint_type).all()
        
        # Count total matches
        total_matches = db.query(FingerprintMatchModel).join(
            ContentFingerprintModel,
            FingerprintMatchModel.query_fingerprint_id == ContentFingerprintModel.id
        ).filter(
            ContentFingerprintModel.profile_id == profile_id
        ).count()
        
        # Count high-confidence matches
        high_confidence_matches = db.query(FingerprintMatchModel).join(
            ContentFingerprintModel,
            FingerprintMatchModel.query_fingerprint_id == ContentFingerprintModel.id
        ).filter(
            ContentFingerprintModel.profile_id == profile_id,
            FingerprintMatchModel.match_confidence >= 0.8
        ).count()
        
        # Get risk assessments
        risk_assessments = db.query(ContentRiskAssessment).filter(
            ContentRiskAssessment.profile_id == profile_id
        ).all()
        
        risk_distribution = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
        avg_risk_score = 0.0
        
        if risk_assessments:
            for assessment in risk_assessments:
                risk_distribution[assessment.risk_level] += 1
            avg_risk_score = sum(a.risk_score for a in risk_assessments) / len(risk_assessments)
        
        return {
            'profile_id': profile_id,
            'fingerprint_counts': {fp_type: count for fp_type, count in fingerprint_counts},
            'total_fingerprints': sum(count for _, count in fingerprint_counts),
            'total_matches': total_matches,
            'high_confidence_matches': high_confidence_matches,
            'match_rate': high_confidence_matches / max(sum(count for _, count in fingerprint_counts), 1),
            'risk_distribution': risk_distribution,
            'average_risk_score': avg_risk_score,
            'total_risk_assessments': len(risk_assessments)
        }
        
    except Exception as e:
        logger.error(f"Error getting fingerprinting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Add health check endpoint
@router.get("/health")
async def health_check():
    """Health check for enhanced content analysis service"""
    return {
        'status': 'healthy',
        'service': 'enhanced-content-analysis',
        'version': '1.0.0',
        'features': [
            'audio_fingerprinting',
            'video_fingerprinting', 
            'enhanced_image_hashing',
            'ml_pattern_recognition',
            'risk_assessment'
        ]
    }