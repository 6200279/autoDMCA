"""
Enhanced Content Matcher with Advanced Fingerprinting
Integrates the new ContentFingerprintingService with the existing ContentMatcher
"""

import asyncio
import hashlib
import io
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from PIL import Image
import torch
from sqlalchemy.orm import Session

# Import existing services and models
from app.services.ai.content_matcher import ContentMatcher, ContentMatch, MatchType
from app.services.ai.content_fingerprinting_service import (
    ContentFingerprintingService,
    FingerprintType,
    ContentFingerprint,
    FingerprintMatch
)
from app.db.models.content_fingerprint import (
    ContentFingerprint as ContentFingerprintModel,
    FingerprintMatch as FingerprintMatchModel,
    AudioSignature,
    VideoSignature,
    ImageHash,
    ContentRiskAssessment,
    RiskLevel
)
from app.db.session import get_db

logger = logging.getLogger(__name__)


@dataclass
class EnhancedContentMatch:
    """Enhanced content match with fingerprinting capabilities"""
    # Original match data
    match_type: MatchType
    confidence: float
    source_url: str
    matched_content_id: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    # Enhanced fingerprinting data
    fingerprint_similarity: Optional[float] = None
    fingerprint_type: Optional[FingerprintType] = None
    fingerprint_match_id: Optional[int] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    pattern_indicators: Optional[List[str]] = None


class EnhancedContentMatcher:
    """
    Enhanced content matcher that combines existing face recognition
    with advanced audio/video fingerprinting and ML pattern recognition
    """
    
    def __init__(self):
        # Initialize existing content matcher
        self.base_matcher = ContentMatcher()
        
        # Initialize new fingerprinting service
        self.fingerprinting_service = ContentFingerprintingService()
        
        # Performance settings
        self.enable_fingerprinting = True
        self.enable_risk_assessment = True
        self.similarity_threshold = 0.8
        
    async def analyze_content_enhanced(
        self,
        content_url: str,
        content_data: bytes,
        profile_data: Dict[str, Any],
        user_id: str = "unknown",
        client_ip: str = "unknown",
        db: Optional[Session] = None
    ) -> List[EnhancedContentMatch]:
        """
        Enhanced content analysis combining existing face recognition
        with advanced fingerprinting and risk assessment
        """
        enhanced_matches = []
        
        try:
            # Step 1: Run existing content analysis for face recognition
            logger.info(f"Running base content analysis for {content_url}")
            base_matches = await self.base_matcher.analyze_content(
                content_url, content_data, profile_data, user_id, client_ip
            )
            
            # Convert base matches to enhanced matches
            for match in base_matches:
                enhanced_match = EnhancedContentMatch(
                    match_type=match.match_type,
                    confidence=match.confidence,
                    source_url=match.source_url,
                    matched_content_id=match.matched_content_id,
                    metadata=match.metadata,
                    timestamp=match.timestamp
                )
                enhanced_matches.append(enhanced_match)
            
            # Step 2: Create content fingerprint if enabled
            if self.enable_fingerprinting:
                try:
                    fingerprint_type = self._determine_fingerprint_type(content_data)
                    logger.info(f"Creating {fingerprint_type.value} fingerprint for {content_url}")
                    
                    fingerprint = await self.fingerprinting_service.create_content_fingerprint(
                        content_data=content_data,
                        content_type=fingerprint_type,
                        source_url=content_url,
                        metadata={
                            'profile_id': profile_data.get('profile_id'),
                            'user_id': user_id,
                            'analysis_timestamp': datetime.utcnow().isoformat()
                        }
                    )
                    
                    # Step 3: Find fingerprint matches
                    fingerprint_matches = await self.fingerprinting_service.find_matching_fingerprints(
                        fingerprint, self.similarity_threshold
                    )
                    
                    # Step 4: Store fingerprint in database if provided
                    if db:
                        await self._store_fingerprint_in_db(fingerprint, db)
                        
                        # Store fingerprint matches
                        for fp_match in fingerprint_matches:
                            await self._store_fingerprint_match_in_db(fp_match, db)
                    
                    # Step 5: Convert fingerprint matches to enhanced matches
                    for fp_match in fingerprint_matches:
                        enhanced_match = EnhancedContentMatch(
                            match_type=self._fingerprint_to_match_type(fingerprint_type),
                            confidence=fp_match.match_confidence,
                            source_url=fp_match.matched_fingerprint.source_url or "unknown",
                            matched_content_id=fp_match.matched_fingerprint.content_hash,
                            metadata={
                                'fingerprint_similarity': fp_match.similarity_score,
                                'comparison_method': fp_match.match_metadata.get('comparison_method'),
                                'fingerprint_type': fingerprint_type.value
                            },
                            timestamp=datetime.utcnow(),
                            fingerprint_similarity=fp_match.similarity_score,
                            fingerprint_type=fingerprint_type,
                            fingerprint_match_id=None  # Will be set after DB storage
                        )
                        enhanced_matches.append(enhanced_match)
                    
                    logger.info(f"Found {len(fingerprint_matches)} fingerprint matches")
                    
                except Exception as e:
                    logger.error(f"Error in fingerprinting analysis: {e}")
                    # Continue with base matches even if fingerprinting fails
            
            # Step 6: Risk assessment if enabled
            if self.enable_risk_assessment:
                try:
                    content_metadata = {
                        'type': self._determine_content_type_string(content_data),
                        'url': content_url,
                        'size': len(content_data),
                        'upload_time': datetime.utcnow().isoformat()
                    }
                    
                    risk_assessment = await self.fingerprinting_service.predict_piracy_risk(
                        content_metadata=content_metadata,
                        creator_profile=profile_data
                    )
                    
                    # Add risk assessment to all matches
                    for match in enhanced_matches:
                        match.risk_assessment = risk_assessment
                    
                    # If high risk but no matches found, create a warning match
                    if (risk_assessment.get('risk_level') == 'HIGH' and 
                        risk_assessment.get('risk_score', 0) > 0.7 and 
                        not enhanced_matches):
                        
                        warning_match = EnhancedContentMatch(
                            match_type=MatchType.SIMILAR_IMAGE,  # Generic match type
                            confidence=risk_assessment.get('confidence', 0.5),
                            source_url=content_url,
                            matched_content_id="high_risk_content",
                            metadata={
                                'risk_warning': True,
                                'risk_factors': risk_assessment.get('factors', {}),
                                'recommendations': risk_assessment.get('recommendations', [])
                            },
                            timestamp=datetime.utcnow(),
                            risk_assessment=risk_assessment
                        )
                        enhanced_matches.append(warning_match)
                    
                    logger.info(f"Risk assessment: {risk_assessment.get('risk_level')} ({risk_assessment.get('risk_score', 0):.2f})")
                    
                except Exception as e:
                    logger.error(f"Error in risk assessment: {e}")
            
            # Step 7: Sort matches by confidence
            enhanced_matches.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Enhanced analysis complete: {len(enhanced_matches)} total matches found")
            return enhanced_matches
            
        except Exception as e:
            logger.error(f"Error in enhanced content analysis: {e}")
            # Return base matches if enhancement fails
            return [EnhancedContentMatch(
                match_type=match.match_type,
                confidence=match.confidence,
                source_url=match.source_url,
                matched_content_id=match.matched_content_id,
                metadata=match.metadata,
                timestamp=match.timestamp
            ) for match in base_matches] if 'base_matches' in locals() else []
    
    def _determine_fingerprint_type(self, content_data: bytes) -> FingerprintType:
        """Determine fingerprint type based on content data"""
        # Check magic bytes
        if content_data.startswith(b'\xff\xd8\xff') or content_data.startswith(b'\x89PNG'):
            return FingerprintType.IMAGE
        elif content_data.startswith(b'GIF'):
            return FingerprintType.IMAGE
        elif b'ftypmp4' in content_data[:50] or b'ftypisom' in content_data[:50]:
            return FingerprintType.VIDEO
        elif b'WEBM' in content_data[:50]:
            return FingerprintType.VIDEO
        elif b'RIFF' in content_data[:50] and b'WAVE' in content_data[:50]:
            return FingerprintType.AUDIO
        elif b'ID3' in content_data[:50] or content_data.startswith(b'\xff\xfb'):
            return FingerprintType.AUDIO
        else:
            # Default to image for unknown types (will be handled gracefully)
            return FingerprintType.IMAGE
    
    def _determine_content_type_string(self, content_data: bytes) -> str:
        """Determine content type as string for risk assessment"""
        fingerprint_type = self._determine_fingerprint_type(content_data)
        return fingerprint_type.value
    
    def _fingerprint_to_match_type(self, fingerprint_type: FingerprintType) -> MatchType:
        """Convert fingerprint type to match type"""
        if fingerprint_type == FingerprintType.IMAGE:
            return MatchType.SIMILAR_IMAGE
        elif fingerprint_type == FingerprintType.VIDEO:
            return MatchType.SIMILAR_IMAGE  # Reuse for video
        elif fingerprint_type == FingerprintType.AUDIO:
            return MatchType.SIMILAR_IMAGE  # Reuse for audio
        else:
            return MatchType.TEXT_MATCH
    
    async def _store_fingerprint_in_db(
        self, 
        fingerprint: ContentFingerprint, 
        db: Session
    ) -> ContentFingerprintModel:
        """Store fingerprint in database"""
        try:
            # Check if fingerprint already exists
            existing = db.query(ContentFingerprintModel).filter(
                ContentFingerprintModel.content_hash == fingerprint.content_hash
            ).first()
            
            if existing:
                return existing
            
            # Create new fingerprint record
            db_fingerprint = ContentFingerprintModel(
                content_hash=fingerprint.content_hash,
                fingerprint_type=fingerprint.fingerprint_type.value,
                fingerprint_data=fingerprint.fingerprint_data,
                confidence=fingerprint.confidence,
                source_url=fingerprint.source_url,
                profile_id=fingerprint.metadata.get('profile_id') if fingerprint.metadata else None,
                file_size=len(fingerprint.fingerprint_data.get('signature_vector', [])) * 8,  # Rough estimate
                metadata=fingerprint.metadata or {}
            )
            
            db.add(db_fingerprint)
            db.commit()
            db.refresh(db_fingerprint)
            
            # Store specialized signatures
            await self._store_specialized_signatures(fingerprint, db_fingerprint, db)
            
            return db_fingerprint
            
        except Exception as e:
            logger.error(f"Error storing fingerprint in DB: {e}")
            db.rollback()
            raise
    
    async def _store_specialized_signatures(
        self,
        fingerprint: ContentFingerprint,
        db_fingerprint: ContentFingerprintModel,
        db: Session
    ):
        """Store specialized signatures based on fingerprint type"""
        try:
            if fingerprint.fingerprint_type == FingerprintType.AUDIO:
                audio_sig = AudioSignature(
                    fingerprint_id=db_fingerprint.id,
                    mfcc_signature=fingerprint.fingerprint_data.get('mfccs'),
                    chroma_signature=fingerprint.fingerprint_data.get('chroma'),
                    spectral_signature=fingerprint.fingerprint_data.get('spectral_centroid'),
                    tempo=fingerprint.fingerprint_data.get('tempo'),
                    zero_crossing_rate=fingerprint.fingerprint_data.get('zero_crossing_rate'),
                    rms_energy=fingerprint.fingerprint_data.get('rms_energy'),
                    signature_vector=fingerprint.fingerprint_data.get('signature_vector')
                )
                db.add(audio_sig)
                
            elif fingerprint.fingerprint_type == FingerprintType.VIDEO:
                video_sig = VideoSignature(
                    fingerprint_id=db_fingerprint.id,
                    frame_count=fingerprint.fingerprint_data.get('extracted_frames'),
                    fps=fingerprint.fingerprint_data.get('fps'),
                    aspect_ratio=fingerprint.fingerprint_data.get('aspect_ratio'),
                    avg_brightness=fingerprint.fingerprint_data.get('avg_brightness'),
                    avg_contrast=fingerprint.fingerprint_data.get('avg_contrast'),
                    motion_intensity=fingerprint.fingerprint_data.get('motion_intensity'),
                    motion_variance=fingerprint.fingerprint_data.get('motion_variance'),
                    dominant_colors=fingerprint.fingerprint_data.get('dominant_colors'),
                    scene_change_indices=fingerprint.fingerprint_data.get('scene_changes'),
                    signature_vector=fingerprint.fingerprint_data.get('signature_vector')
                )
                db.add(video_sig)
                
            elif fingerprint.fingerprint_type == FingerprintType.IMAGE:
                image_hash = ImageHash(
                    fingerprint_id=db_fingerprint.id,
                    phash=fingerprint.fingerprint_data.get('phash'),
                    ahash=fingerprint.fingerprint_data.get('ahash'),
                    dhash=fingerprint.fingerprint_data.get('dhash'),
                    whash=fingerprint.fingerprint_data.get('whash'),
                    colorhash=fingerprint.fingerprint_data.get('colorhash'),
                    crop_resistant_hash=fingerprint.fingerprint_data.get('crop_resistant')
                )
                db.add(image_hash)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing specialized signatures: {e}")
            db.rollback()
            raise
    
    async def _store_fingerprint_match_in_db(
        self,
        fp_match: FingerprintMatch,
        db: Session
    ) -> Optional[FingerprintMatchModel]:
        """Store fingerprint match in database"""
        try:
            # We would need the database IDs for the fingerprints
            # This is a simplified version - in practice, you'd need to 
            # look up the fingerprints by content hash
            
            query_fp = db.query(ContentFingerprintModel).filter(
                ContentFingerprintModel.content_hash == fp_match.original_fingerprint.content_hash
            ).first()
            
            matched_fp = db.query(ContentFingerprintModel).filter(
                ContentFingerprintModel.content_hash == fp_match.matched_fingerprint.content_hash
            ).first()
            
            if not query_fp or not matched_fp:
                logger.warning("Could not find fingerprints in DB for match storage")
                return None
            
            # Check if match already exists
            existing_match = db.query(FingerprintMatchModel).filter(
                FingerprintMatchModel.query_fingerprint_id == query_fp.id,
                FingerprintMatchModel.matched_fingerprint_id == matched_fp.id
            ).first()
            
            if existing_match:
                return existing_match
            
            db_match = FingerprintMatchModel(
                query_fingerprint_id=query_fp.id,
                matched_fingerprint_id=matched_fp.id,
                similarity_score=fp_match.similarity_score,
                match_confidence=fp_match.match_confidence,
                comparison_method=fp_match.match_metadata.get('comparison_method', 'unknown'),
                match_metadata=fp_match.match_metadata or {}
            )
            
            db.add(db_match)
            db.commit()
            db.refresh(db_match)
            
            return db_match
            
        except Exception as e:
            logger.error(f"Error storing fingerprint match in DB: {e}")
            db.rollback()
            return None
    
    async def analyze_historical_patterns(
        self,
        profile_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Analyze historical patterns for a specific profile"""
        try:
            # Get historical infringement data (this would be from actual infringement records)
            # For now, using mock data structure
            historical_data = self._get_mock_historical_data(profile_id, db)
            
            if not historical_data:
                return {'message': 'No historical data available'}
            
            patterns = await self.fingerprinting_service.analyze_content_patterns(historical_data)
            
            # Store patterns in database
            if patterns and not patterns.get('error'):
                await self._store_piracy_patterns(profile_id, patterns, db)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing historical patterns: {e}")
            return {'error': str(e)}
    
    def _get_mock_historical_data(self, profile_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get historical infringement data (mock implementation)"""
        # In a real implementation, this would query actual infringement records
        # For now, return mock data based on stored fingerprints
        
        fingerprints = db.query(ContentFingerprintModel).filter(
            ContentFingerprintModel.profile_id == profile_id
        ).limit(50).all()
        
        historical_data = []
        for fp in fingerprints:
            historical_data.append({
                'timestamp': fp.created_at,
                'platform': 'unknown',  # Would be extracted from source_url
                'content_type': fp.fingerprint_type,
                'resolved': True,  # Mock data
                'response_time_hours': 24.0  # Mock data
            })
        
        return historical_data
    
    async def _store_piracy_patterns(
        self,
        profile_id: int,
        patterns: Dict[str, Any],
        db: Session
    ):
        """Store detected piracy patterns in database"""
        try:
            from app.db.models.content_fingerprint import PiracyPattern
            
            # Store temporal patterns
            if patterns.get('temporal_patterns'):
                pattern = PiracyPattern(
                    profile_id=profile_id,
                    pattern_type='temporal',
                    pattern_data=patterns['temporal_patterns'],
                    confidence=0.8,  # Mock confidence
                    incidents_analyzed=patterns.get('total_incidents', 0),
                    risk_score=0.6  # Mock risk score
                )
                db.add(pattern)
            
            # Store platform patterns
            if patterns.get('platform_patterns'):
                pattern = PiracyPattern(
                    profile_id=profile_id,
                    pattern_type='platform',
                    pattern_data=patterns['platform_patterns'],
                    confidence=0.8,
                    incidents_analyzed=patterns.get('total_incidents', 0),
                    risk_score=0.7
                )
                db.add(pattern)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing piracy patterns: {e}")
            db.rollback()
    
    async def get_content_risk_score(
        self,
        content_data: bytes,
        profile_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Get risk score for content without full analysis"""
        try:
            content_metadata = {
                'type': self._determine_content_type_string(content_data),
                'size': len(content_data),
                'upload_time': datetime.utcnow().isoformat()
            }
            
            risk_assessment = await self.fingerprinting_service.predict_piracy_risk(
                content_metadata=content_metadata,
                creator_profile=profile_data
            )
            
            # Store risk assessment in database if provided
            if db and profile_data.get('profile_id'):
                try:
                    assessment = ContentRiskAssessment(
                        profile_id=profile_data['profile_id'],
                        content_metadata=content_metadata,
                        risk_score=risk_assessment['risk_score'],
                        risk_level=RiskLevel(risk_assessment['risk_level']),
                        risk_factors=risk_assessment.get('factors', {}),
                        recommendations=risk_assessment.get('recommendations'),
                        prediction_confidence=risk_assessment.get('confidence', 0.5),
                        model_version='1.0'
                    )
                    db.add(assessment)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error storing risk assessment: {e}")
                    db.rollback()
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error getting content risk score: {e}")
            return {
                'risk_score': 0.5,
                'risk_level': 'MEDIUM',
                'confidence': 0.1,
                'error': str(e)
            }
    
    def configure_fingerprinting(
        self,
        enable_fingerprinting: bool = True,
        enable_risk_assessment: bool = True,
        similarity_threshold: float = 0.8
    ):
        """Configure fingerprinting settings"""
        self.enable_fingerprinting = enable_fingerprinting
        self.enable_risk_assessment = enable_risk_assessment
        self.similarity_threshold = max(0.1, min(1.0, similarity_threshold))
        
        logger.info(f"Fingerprinting configured: enabled={enable_fingerprinting}, "
                   f"risk_assessment={enable_risk_assessment}, "
                   f"threshold={similarity_threshold}")


# Convenience function for easy integration
async def create_enhanced_content_matcher() -> EnhancedContentMatcher:
    """Create and configure enhanced content matcher"""
    matcher = EnhancedContentMatcher()
    await asyncio.sleep(0)  # Allow for any async initialization
    return matcher