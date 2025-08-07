"""
Content matcher that combines face recognition, image hashing, and text matching.
"""

import asyncio
import time
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse
import re

import structlog

from .face_recognition_processor import FaceRecognitionProcessor, FaceProcessingResult
from .image_hash_processor import ImageHashProcessor, ImageMatch as HashImageMatch
from ..config import ScannerSettings
from ..crawlers.piracy_crawler import InfringingContent


logger = structlog.get_logger(__name__)


@dataclass
class ContentMatch:
    """Represents a comprehensive content match."""
    
    content: InfringingContent
    person_id: str
    confidence_score: float
    match_types: List[str] = field(default_factory=list)
    
    # Face recognition results
    face_matches: List = field(default_factory=list)
    face_confidence: float = 0.0
    
    # Image hash results  
    image_matches: List[HashImageMatch] = field(default_factory=list)
    image_similarity: float = 0.0
    
    # Text matching results
    text_matches: List[str] = field(default_factory=list)
    text_confidence: float = 0.0
    
    # Metadata
    processing_time: float = 0.0
    verified_at: float = field(default_factory=time.time)
    
    @property
    def is_positive_match(self) -> bool:
        """Check if this is considered a positive match."""
        return self.confidence_score >= 0.7
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high confidence match."""
        return self.confidence_score >= 0.9
    
    @property
    def match_summary(self) -> str:
        """Get a summary of match types."""
        if not self.match_types:
            return "No match"
        return ", ".join(self.match_types)


class ContentMatcher:
    """Comprehensive content matcher using multiple AI techniques."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.face_processor = FaceRecognitionProcessor(settings)
        self.image_processor = ImageHashProcessor(settings)
        self._initialized = False
        
    async def initialize(self):
        """Initialize all processors."""
        if self._initialized:
            return
        
        await self.face_processor.initialize()
        await self.image_processor.initialize()
        self._initialized = True
        
        logger.info("Content matcher initialized")
    
    async def close(self):
        """Clean up resources."""
        await self.face_processor.close()
        await self.image_processor.close()
    
    async def add_person_profile(
        self,
        person_id: str,
        reference_images: List[Union[str, bytes]],
        usernames: List[str],
        additional_keywords: List[str] = None
    ) -> bool:
        """Add a person's profile for content matching."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Add face recognition encodings
            face_encodings_added = await self.face_processor.add_person(
                person_id, reference_images, replace_existing=True
            )
            
            # Add image hashes
            image_hashes_added = await self.image_processor.add_reference_images(
                person_id, reference_images, replace_existing=True
            )
            
            # Store text matching data (usernames and keywords)
            if not hasattr(self, 'person_keywords'):
                self.person_keywords = {}
            
            keywords = usernames.copy()
            if additional_keywords:
                keywords.extend(additional_keywords)
            
            # Generate keyword variations
            expanded_keywords = self._generate_keyword_variations(keywords)
            self.person_keywords[person_id] = expanded_keywords
            
            logger.info(
                f"Added person profile: {person_id}",
                face_encodings=face_encodings_added,
                image_hashes=image_hashes_added,
                keywords=len(expanded_keywords)
            )
            
            return face_encodings_added > 0 or image_hashes_added > 0
            
        except Exception as e:
            logger.error(f"Failed to add person profile: {person_id}", error=str(e))
            return False
    
    def _generate_keyword_variations(self, keywords: List[str]) -> List[str]:
        """Generate variations of keywords for text matching."""
        variations = set()
        
        for keyword in keywords:
            if not keyword:
                continue
                
            # Add original
            variations.add(keyword.lower())
            
            # Add common variations
            variations.add(keyword.lower().replace('_', ''))
            variations.add(keyword.lower().replace('-', ''))
            variations.add(keyword.lower().replace(' ', ''))
            
            # Add with common suffixes for leak detection
            leak_suffixes = [
                'leaked', 'leak', 'leaks', 'stolen', 'pirated', 
                'onlyfans', 'of', 'premium', 'exclusive', 'content'
            ]
            
            for suffix in leak_suffixes:
                variations.add(f"{keyword.lower()} {suffix}")
                variations.add(f"{keyword.lower()}_{suffix}")
                variations.add(f"{keyword.lower()}{suffix}")
            
            # Add partial matches (for longer usernames)
            if len(keyword) > 6:
                variations.add(keyword[:6].lower())
                variations.add(keyword[-6:].lower())
        
        return list(variations)
    
    async def match_content(
        self,
        content: InfringingContent,
        person_ids: Optional[List[str]] = None,
        enable_face_recognition: bool = None,
        enable_image_hashing: bool = None,
        enable_text_matching: bool = None
    ) -> List[ContentMatch]:
        """Match content against person profiles using all available methods."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        # Use settings defaults if not specified
        if enable_face_recognition is None:
            enable_face_recognition = self.settings.enable_face_recognition
        if enable_image_hashing is None:
            enable_image_hashing = self.settings.enable_image_hashing  
        if enable_text_matching is None:
            enable_text_matching = self.settings.enable_text_matching
        
        matches = []
        target_persons = person_ids or list(getattr(self, 'person_keywords', {}).keys())
        
        if not target_persons:
            logger.warning("No person profiles available for matching")
            return matches
        
        try:
            # Collect all image URLs to process
            image_urls = []
            if content.thumbnail_url:
                image_urls.append(content.thumbnail_url)
            image_urls.extend(content.download_urls)
            
            # Process each person
            for person_id in target_persons:
                match = await self._match_against_person(
                    content,
                    person_id,
                    image_urls,
                    enable_face_recognition,
                    enable_image_hashing,
                    enable_text_matching
                )
                
                if match and match.confidence_score > 0.3:  # Minimum threshold
                    matches.append(match)
        
        except Exception as e:
            logger.error("Content matching failed", content_url=content.url, error=str(e))
        
        # Sort matches by confidence score
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        processing_time = time.time() - start_time
        
        logger.debug(
            "Content matching completed",
            content_url=content.url,
            matches_found=len(matches),
            processing_time=processing_time
        )
        
        return matches
    
    async def _match_against_person(
        self,
        content: InfringingContent,
        person_id: str,
        image_urls: List[str],
        enable_face_recognition: bool,
        enable_image_hashing: bool,
        enable_text_matching: bool
    ) -> Optional[ContentMatch]:
        """Match content against a specific person's profile."""
        match = ContentMatch(
            content=content,
            person_id=person_id,
            confidence_score=0.0
        )
        
        confidence_scores = []
        
        # Text matching
        if enable_text_matching:
            text_confidence = await self._match_text_content(content, person_id)
            if text_confidence > 0:
                match.text_confidence = text_confidence
                match.match_types.append("text")
                confidence_scores.append(text_confidence)
        
        # Image processing (face recognition and hashing)
        if image_urls and (enable_face_recognition or enable_image_hashing):
            # Process first few images (limit to avoid excessive processing)
            for image_url in image_urls[:3]:  # Limit to first 3 images
                # Face recognition
                if enable_face_recognition:
                    face_confidence = await self._match_face_content(
                        image_url, person_id, match
                    )
                    if face_confidence > 0:
                        confidence_scores.append(face_confidence)
                
                # Image hashing
                if enable_image_hashing:
                    image_confidence = await self._match_image_hash(
                        image_url, person_id, match
                    )
                    if image_confidence > 0:
                        confidence_scores.append(image_confidence)
        
        # Calculate overall confidence score
        if confidence_scores:
            # Use weighted average with higher weight for face recognition
            weights = []
            for score_type in ["text", "face", "image"]:
                if score_type in match.match_types:
                    if score_type == "face":
                        weights.append(0.5)  # Face recognition gets highest weight
                    elif score_type == "image":
                        weights.append(0.3)  # Image hashing gets medium weight
                    else:
                        weights.append(0.2)  # Text matching gets lowest weight
            
            if len(confidence_scores) == len(weights):
                match.confidence_score = sum(
                    score * weight for score, weight in zip(confidence_scores, weights)
                ) / sum(weights)
            else:
                # Fallback to simple average
                match.confidence_score = sum(confidence_scores) / len(confidence_scores)
        
        return match if match.confidence_score > 0 else None
    
    async def _match_text_content(self, content: InfringingContent, person_id: str) -> float:
        """Match text content against person's keywords."""
        if not hasattr(self, 'person_keywords') or person_id not in self.person_keywords:
            return 0.0
        
        keywords = self.person_keywords[person_id]
        
        # Combine all text content
        text_content = f"{content.title} {content.description}".lower()
        
        # Count keyword matches
        matches_found = []
        for keyword in keywords:
            if keyword in text_content:
                matches_found.append(keyword)
        
        if not matches_found:
            return 0.0
        
        # Calculate confidence based on match quality
        confidence = 0.0
        
        # Exact username matches get high score
        exact_matches = [k for k in matches_found if len(k) > 4 and k not in ['leaked', 'leak', 'stolen']]
        if exact_matches:
            confidence += 0.8
        
        # Leak-related terms add moderate confidence
        leak_terms = [k for k in matches_found if k in ['leaked', 'leak', 'stolen', 'pirated']]
        if leak_terms and exact_matches:
            confidence += 0.2
        elif leak_terms:
            confidence += 0.3
        
        # Multiple matches increase confidence
        if len(matches_found) > 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _match_face_content(
        self,
        image_url: str,
        person_id: str,
        match: ContentMatch
    ) -> float:
        """Match face content against person's face encodings."""
        try:
            result = await self.face_processor.process_image(image_url, [person_id])
            
            if result.has_matches:
                best_match = result.best_match
                match.face_matches.append(best_match)
                match.face_confidence = max(match.face_confidence, best_match.confidence)
                
                if "face" not in match.match_types:
                    match.match_types.append("face")
                
                return best_match.confidence
            
        except Exception as e:
            logger.debug(f"Face matching failed for {image_url}", error=str(e))
        
        return 0.0
    
    async def _match_image_hash(
        self,
        image_url: str,
        person_id: str,
        match: ContentMatch
    ) -> float:
        """Match image hash against person's reference images."""
        try:
            hash_matches = await self.image_processor.find_matches(
                image_url, [person_id], self.settings.similarity_threshold
            )
            
            if hash_matches:
                best_hash_match = max(hash_matches, key=lambda x: x.similarity_score)
                match.image_matches.extend(hash_matches)
                match.image_similarity = max(match.image_similarity, best_hash_match.similarity_score)
                
                if "image" not in match.match_types:
                    match.match_types.append("image")
                
                return best_hash_match.similarity_score
            
        except Exception as e:
            logger.debug(f"Image hash matching failed for {image_url}", error=str(e))
        
        return 0.0
    
    async def bulk_match_content(
        self,
        content_items: List[InfringingContent],
        person_ids: Optional[List[str]] = None,
        max_concurrent: int = 5,
        **kwargs
    ) -> Dict[str, List[ContentMatch]]:
        """Match multiple content items concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def match_single(content: InfringingContent) -> Tuple[str, List[ContentMatch]]:
            async with semaphore:
                matches = await self.match_content(content, person_ids, **kwargs)
                return content.url, matches
        
        tasks = [match_single(content) for content in content_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        matched_results = {}
        for result in results:
            if isinstance(result, tuple):
                url, matches = result
                matched_results[url] = matches
            elif isinstance(result, Exception):
                logger.error("Bulk content matching failed", error=str(result))
        
        # Calculate statistics
        total_matches = sum(len(matches) for matches in matched_results.values())
        positive_matches = sum(
            len([m for m in matches if m.is_positive_match])
            for matches in matched_results.values()
        )
        
        logger.info(
            "Bulk content matching completed",
            content_items=len(content_items),
            total_matches=total_matches,
            positive_matches=positive_matches
        )
        
        return matched_results
    
    async def get_person_statistics(self, person_id: str) -> Dict:
        """Get statistics for a person's profile."""
        stats = {
            'person_id': person_id,
            'face_encodings': 0,
            'image_hashes': 0,
            'keywords': 0
        }
        
        # Face recognition stats
        if hasattr(self.face_processor, 'known_encodings'):
            if person_id in self.face_processor.known_encodings:
                stats['face_encodings'] = len(self.face_processor.known_encodings[person_id])
        
        # Image hash stats
        if hasattr(self.image_processor, 'hash_database'):
            if person_id in self.image_processor.hash_database:
                stats['image_hashes'] = len(self.image_processor.hash_database[person_id])
        
        # Keyword stats
        if hasattr(self, 'person_keywords'):
            if person_id in self.person_keywords:
                stats['keywords'] = len(self.person_keywords[person_id])
        
        return stats
    
    async def remove_person(self, person_id: str) -> bool:
        """Remove a person's profile from all processors."""
        success = True
        
        # Remove from face recognition
        try:
            await self.face_processor.remove_person(person_id)
        except Exception as e:
            logger.error(f"Failed to remove person from face processor: {person_id}", error=str(e))
            success = False
        
        # Remove from image hashing
        try:
            await self.image_processor.remove_person(person_id)
        except Exception as e:
            logger.error(f"Failed to remove person from image processor: {person_id}", error=str(e))
            success = False
        
        # Remove keywords
        if hasattr(self, 'person_keywords') and person_id in self.person_keywords:
            del self.person_keywords[person_id]
        
        logger.info(f"Removed person profile: {person_id}", success=success)
        return success
    
    async def validate_match(self, match: ContentMatch) -> bool:
        """Validate a match by re-processing with higher thresholds."""
        try:
            # Re-run matching with stricter thresholds
            stricter_matches = await self.match_content(
                match.content,
                [match.person_id],
                enable_face_recognition=True,
                enable_image_hashing=True,
                enable_text_matching=True
            )
            
            if stricter_matches and stricter_matches[0].confidence_score > 0.8:
                match.verified_at = time.time()
                return True
            
            return False
            
        except Exception as e:
            logger.error("Match validation failed", error=str(e))
            return False