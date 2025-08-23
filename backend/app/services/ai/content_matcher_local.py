"""
Lightweight Content Matching System for Local Development
Uses basic image hashing without heavy AI dependencies
"""
import hashlib
import io
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from PIL import Image
import imagehash
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    EXACT = "exact"
    PERCEPTUAL_HASH = "perceptual_hash"
    TEXT_MATCH = "text_match"

 
@dataclass
class ContentMatch:
    """Result of content matching"""
    match_type: MatchType
    confidence: float  # 0.0 to 1.0
    source_url: str
    matched_content_id: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime


class ContentMatcher:
    """
    Lightweight content matcher for local development.
    Implements basic image hashing and exact matching only.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enabled = not os.getenv('DISABLE_AI_PROCESSING', 'false').lower() == 'true'
        
        if not self.enabled:
            self.logger.info("AI processing disabled for local development")
    
    async def match_image(self, image_data: bytes, source_url: str) -> List[ContentMatch]:
        """
        Match image using basic perceptual hashing
        """
        if not self.enabled:
            return []
            
        try:
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate perceptual hash
            phash = imagehash.phash(image)
            
            # For local development, just return a mock match
            # In production, this would search the database
            matches = []
            
            # Basic exact hash match simulation
            matches.append(ContentMatch(
                match_type=MatchType.PERCEPTUAL_HASH,
                confidence=0.8,
                source_url=source_url,
                matched_content_id=f"hash_{str(phash)}",
                metadata={
                    "perceptual_hash": str(phash),
                    "image_size": image.size,
                    "local_testing": True
                },
                timestamp=datetime.utcnow()
            ))
            
            self.logger.info(f"Generated perceptual hash for image: {phash}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Error matching image: {e}")
            return []
    
    async def match_text(self, text: str, source_url: str) -> List[ContentMatch]:
        """
        Match text using simple hashing
        """
        if not self.enabled:
            return []
            
        try:
            # Simple text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            matches = []
            matches.append(ContentMatch(
                match_type=MatchType.TEXT_MATCH,
                confidence=1.0,
                source_url=source_url,
                matched_content_id=f"text_{text_hash}",
                metadata={
                    "text_hash": text_hash,
                    "text_length": len(text),
                    "local_testing": True
                },
                timestamp=datetime.utcnow()
            ))
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error matching text: {e}")
            return []
    
    async def extract_image_features(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract basic image features without AI
        """
        if not self.enabled:
            return {}
            
        try:
            image = Image.open(io.BytesIO(image_data))
            
            return {
                "perceptual_hash": str(imagehash.phash(image)),
                "average_hash": str(imagehash.average_hash(image)),
                "size": image.size,
                "mode": image.mode,
                "format": image.format,
                "local_testing": True
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting image features: {e}")
            return {}
    
    def is_enabled(self) -> bool:
        """Check if content matching is enabled"""
        return self.enabled


# Global instance
content_matcher = ContentMatcher()