#!/usr/bin/env python3
"""
AI-Powered Content Matching Service for AutoDMCA Platform
Based on RULTA's approach to minimize human intervention
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np
from pathlib import Path

# Core ML Libraries
import cv2
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image, ImageHash
import imagehash
from sentence_transformers import SentenceTransformer
import librosa
from transformers import CLIPModel, CLIPProcessor
import whisper

# Async HTTP
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Content types for matching"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"

class MatchConfidenceLevel(Enum):
    """Match confidence levels for decision making"""
    VERY_LOW = "very_low"      # < 60%
    LOW = "low"                # 60-70%
    MEDIUM = "medium"          # 70-80%
    HIGH = "high"              # 80-90%
    VERY_HIGH = "very_high"    # 90-95%
    EXACT = "exact"            # > 95%

@dataclass
class ContentFingerprint:
    """Content fingerprint containing multiple hashing methods"""
    content_id: str
    content_type: ContentType
    
    # Hash-based fingerprints
    perceptual_hash: str
    average_hash: str
    difference_hash: str
    wavelet_hash: str
    color_hash: str
    
    # Feature-based fingerprints
    deep_features: Optional[np.ndarray] = None
    text_embeddings: Optional[np.ndarray] = None
    audio_features: Optional[np.ndarray] = None
    
    # Metadata
    file_size: int = 0
    duration: float = 0.0
    resolution: Optional[Tuple[int, int]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class SimilarityMatch:
    """Result of content similarity comparison"""
    original_content_id: str
    matched_content_id: str
    confidence_score: float
    confidence_level: MatchConfidenceLevel
    
    # Match details
    match_type: str  # "exact", "near_duplicate", "derivative", "similar"
    similarity_scores: Dict[str, float]  # breakdown by method
    
    # AI reasoning
    ai_reasoning: str
    decision_recommendation: str  # "auto_approve", "manual_review", "auto_reject"
    
    # Evidence
    visual_diff_url: Optional[str] = None
    match_regions: List[Dict[str, Any]] = None
    
    matched_at: datetime = None
    
    def __post_init__(self):
        if self.matched_at is None:
            self.matched_at = datetime.utcnow()
        
        # Determine confidence level from score
        if self.confidence_score >= 0.95:
            self.confidence_level = MatchConfidenceLevel.EXACT
        elif self.confidence_score >= 0.90:
            self.confidence_level = MatchConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 0.80:
            self.confidence_level = MatchConfidenceLevel.HIGH
        elif self.confidence_score >= 0.70:
            self.confidence_level = MatchConfidenceLevel.MEDIUM
        elif self.confidence_score >= 0.60:
            self.confidence_level = MatchConfidenceLevel.LOW
        else:
            self.confidence_level = MatchConfidenceLevel.VERY_LOW

class ContentFingerprintService:
    """Service for generating content fingerprints"""
    
    def __init__(self, device: str = "cpu"):
        self.device = device
        
        # Initialize ML models
        self._init_models()
        
        # Configuration
        self.config = {
            "image_size": (224, 224),
            "video_sample_rate": 1.0,  # frames per second for analysis
            "audio_sample_rate": 22050,
            "text_max_length": 512,
            "hash_size": 16,
        }
    
    def _init_models(self):
        """Initialize ML models for feature extraction"""
        try:
            # CLIP for multimodal embeddings
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model.to(self.device)
            
            # Sentence transformer for text embeddings
            self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Whisper for audio transcription and analysis
            self.whisper_model = whisper.load_model("base")
            
            logger.info("AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML models: {str(e)}")
            raise
    
    async def generate_fingerprint(
        self, 
        content_path: str, 
        content_type: ContentType,
        content_id: str = None
    ) -> ContentFingerprint:
        """Generate comprehensive fingerprint for content"""
        
        if content_id is None:
            content_id = hashlib.md5(content_path.encode()).hexdigest()
        
        try:
            if content_type == ContentType.IMAGE:
                return await self._fingerprint_image(content_path, content_id)
            elif content_type == ContentType.VIDEO:
                return await self._fingerprint_video(content_path, content_id)
            elif content_type == ContentType.AUDIO:
                return await self._fingerprint_audio(content_path, content_id)
            elif content_type == ContentType.TEXT:
                return await self._fingerprint_text(content_path, content_id)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
                
        except Exception as e:
            logger.error(f"Fingerprint generation failed for {content_path}: {str(e)}")
            raise
    
    async def _fingerprint_image(self, image_path: str, content_id: str) -> ContentFingerprint:
        """Generate fingerprint for image content"""
        
        # Load image
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Generate hash-based fingerprints
        perceptual_hash = str(imagehash.phash(image, hash_size=self.config["hash_size"]))
        average_hash = str(imagehash.average_hash(image, hash_size=self.config["hash_size"]))
        difference_hash = str(imagehash.dhash(image, hash_size=self.config["hash_size"]))
        wavelet_hash = str(imagehash.whash(image, hash_size=self.config["hash_size"]))
        color_hash = str(imagehash.colorhash(image, binbits=3))
        
        # Generate deep features using CLIP
        inputs = self.clip_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
            deep_features = image_features.cpu().numpy().flatten()
        
        # Get file metadata
        file_size = Path(image_path).stat().st_size
        resolution = image.size
        
        return ContentFingerprint(
            content_id=content_id,
            content_type=ContentType.IMAGE,
            perceptual_hash=perceptual_hash,
            average_hash=average_hash,
            difference_hash=difference_hash,
            wavelet_hash=wavelet_hash,
            color_hash=color_hash,
            deep_features=deep_features,
            file_size=file_size,
            resolution=resolution
        )
    
    async def _fingerprint_video(self, video_path: str, content_id: str) -> ContentFingerprint:
        """Generate fingerprint for video content"""
        
        # Extract key frames using OpenCV
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Sample frames at regular intervals
        sample_interval = max(1, int(fps / self.config["video_sample_rate"]))
        frames = []
        
        frame_idx = 0
        while frame_idx < frame_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))
            frame_idx += sample_interval
            
            # Limit to prevent memory issues
            if len(frames) >= 100:
                break
        
        cap.release()
        
        if not frames:
            raise ValueError("Could not extract frames from video")
        
        # Use middle frame as representative
        representative_frame = frames[len(frames) // 2]
        
        # Generate hashes from representative frame
        perceptual_hash = str(imagehash.phash(representative_frame))
        average_hash = str(imagehash.average_hash(representative_frame))
        difference_hash = str(imagehash.dhash(representative_frame))
        wavelet_hash = str(imagehash.whash(representative_frame))
        color_hash = str(imagehash.colorhash(representative_frame))
        
        # Generate deep features from multiple frames
        frame_features = []
        for frame in frames[::max(1, len(frames) // 10)]:  # Sample up to 10 frames
            inputs = self.clip_processor(images=frame, return_tensors="pt").to(self.device)
            with torch.no_grad():
                features = self.clip_model.get_image_features(**inputs)
                frame_features.append(features.cpu().numpy().flatten())
        
        # Average frame features
        deep_features = np.mean(frame_features, axis=0) if frame_features else None
        
        file_size = Path(video_path).stat().st_size
        resolution = (representative_frame.width, representative_frame.height)
        
        return ContentFingerprint(
            content_id=content_id,
            content_type=ContentType.VIDEO,
            perceptual_hash=perceptual_hash,
            average_hash=average_hash,
            difference_hash=difference_hash,
            wavelet_hash=wavelet_hash,
            color_hash=color_hash,
            deep_features=deep_features,
            file_size=file_size,
            duration=duration,
            resolution=resolution
        )
    
    async def _fingerprint_audio(self, audio_path: str, content_id: str) -> ContentFingerprint:
        """Generate fingerprint for audio content"""
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=self.config["audio_sample_rate"])
        duration = len(y) / sr
        
        # Extract audio features
        # Mel-frequency cepstral coefficients
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)
        
        # Combine features
        audio_features = np.concatenate([
            mfcc_mean,
            np.mean(spectral_centroids),
            np.mean(spectral_rolloff),
            np.mean(zero_crossing_rate)
        ])
        
        # Generate hash from audio fingerprint
        audio_hash = hashlib.sha256(audio_features.tobytes()).hexdigest()[:32]
        
        # Transcribe for text analysis
        transcription = ""
        try:
            result = self.whisper_model.transcribe(audio_path)
            transcription = result["text"]
        except Exception as e:
            logger.warning(f"Audio transcription failed: {str(e)}")
        
        # Generate text embeddings if transcription available
        text_embeddings = None
        if transcription.strip():
            text_embeddings = self.text_model.encode(transcription)
        
        file_size = Path(audio_path).stat().st_size
        
        return ContentFingerprint(
            content_id=content_id,
            content_type=ContentType.AUDIO,
            perceptual_hash=audio_hash,
            average_hash=audio_hash,
            difference_hash=audio_hash,
            wavelet_hash=audio_hash,
            color_hash=audio_hash,
            audio_features=audio_features,
            text_embeddings=text_embeddings,
            file_size=file_size,
            duration=duration
        )
    
    async def _fingerprint_text(self, text_content: str, content_id: str) -> ContentFingerprint:
        """Generate fingerprint for text content"""
        
        # Handle file path vs direct text
        if Path(text_content).exists():
            async with aiofiles.open(text_content, 'r', encoding='utf-8') as f:
                text = await f.read()
            file_size = Path(text_content).stat().st_size
        else:
            text = text_content
            file_size = len(text.encode('utf-8'))
        
        # Truncate if too long
        if len(text) > self.config["text_max_length"] * 4:  # Rough token estimate
            text = text[:self.config["text_max_length"] * 4]
        
        # Generate text embeddings
        text_embeddings = self.text_model.encode(text)
        
        # Generate hashes
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]
        
        # Normalized text hash (lowercase, remove punctuation)
        normalized_text = ''.join(c.lower() for c in text if c.isalnum() or c.isspace())
        normalized_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()[:32]
        
        return ContentFingerprint(
            content_id=content_id,
            content_type=ContentType.TEXT,
            perceptual_hash=text_hash,
            average_hash=normalized_hash,
            difference_hash=text_hash,
            wavelet_hash=text_hash,
            color_hash=text_hash,
            text_embeddings=text_embeddings,
            file_size=file_size
        )

class SimilarityDetectionService:
    """Service for detecting content similarity using multiple methods"""
    
    def __init__(self, device: str = "cpu"):
        self.device = device
        
        # Similarity thresholds
        self.thresholds = {
            "exact_match": 0.95,
            "near_duplicate": 0.90,
            "derivative": 0.80,
            "similar": 0.70,
            "minimum": 0.60
        }
        
        # Weights for different matching methods
        self.method_weights = {
            "perceptual_hash": 0.25,
            "deep_features": 0.30,
            "average_hash": 0.15,
            "difference_hash": 0.10,
            "wavelet_hash": 0.10,
            "color_hash": 0.05,
            "text_similarity": 0.05
        }
    
    async def compare_content(
        self, 
        original_fp: ContentFingerprint, 
        candidate_fp: ContentFingerprint
    ) -> SimilarityMatch:
        """Compare two content fingerprints for similarity"""
        
        if original_fp.content_type != candidate_fp.content_type:
            return self._create_no_match(original_fp.content_id, candidate_fp.content_id)
        
        try:
            # Calculate similarity scores using different methods
            similarity_scores = await self._calculate_similarity_scores(original_fp, candidate_fp)
            
            # Weighted overall confidence score
            confidence_score = self._calculate_weighted_confidence(similarity_scores)
            
            # Determine match type
            match_type = self._determine_match_type(confidence_score)
            
            # Generate AI reasoning
            ai_reasoning = self._generate_ai_reasoning(similarity_scores, match_type)
            
            # Decision recommendation based on thresholds
            decision_recommendation = self._make_decision_recommendation(confidence_score)
            
            return SimilarityMatch(
                original_content_id=original_fp.content_id,
                matched_content_id=candidate_fp.content_id,
                confidence_score=confidence_score,
                confidence_level=MatchConfidenceLevel.EXACT,  # Will be set in __post_init__
                match_type=match_type,
                similarity_scores=similarity_scores,
                ai_reasoning=ai_reasoning,
                decision_recommendation=decision_recommendation
            )
            
        except Exception as e:
            logger.error(f"Content comparison failed: {str(e)}")
            return self._create_no_match(original_fp.content_id, candidate_fp.content_id)
    
    async def _calculate_similarity_scores(
        self, 
        original_fp: ContentFingerprint, 
        candidate_fp: ContentFingerprint
    ) -> Dict[str, float]:
        """Calculate similarity scores using different methods"""
        
        scores = {}
        
        # Hash-based similarities
        scores["perceptual_hash"] = self._hash_similarity(original_fp.perceptual_hash, candidate_fp.perceptual_hash)
        scores["average_hash"] = self._hash_similarity(original_fp.average_hash, candidate_fp.average_hash)
        scores["difference_hash"] = self._hash_similarity(original_fp.difference_hash, candidate_fp.difference_hash)
        scores["wavelet_hash"] = self._hash_similarity(original_fp.wavelet_hash, candidate_fp.wavelet_hash)
        scores["color_hash"] = self._hash_similarity(original_fp.color_hash, candidate_fp.color_hash)
        
        # Deep feature similarity
        if original_fp.deep_features is not None and candidate_fp.deep_features is not None:
            scores["deep_features"] = self._cosine_similarity(original_fp.deep_features, candidate_fp.deep_features)
        else:
            scores["deep_features"] = 0.0
        
        # Text similarity
        if original_fp.text_embeddings is not None and candidate_fp.text_embeddings is not None:
            scores["text_similarity"] = self._cosine_similarity(original_fp.text_embeddings, candidate_fp.text_embeddings)
        else:
            scores["text_similarity"] = 0.0
        
        # Audio feature similarity
        if original_fp.audio_features is not None and candidate_fp.audio_features is not None:
            scores["audio_features"] = self._cosine_similarity(original_fp.audio_features, candidate_fp.audio_features)
        else:
            scores["audio_features"] = 0.0
        
        return scores
    
    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hashes"""
        if not hash1 or not hash2:
            return 0.0
        
        # Hamming distance for same-length hashes
        if len(hash1) == len(hash2):
            hamming_distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
            similarity = 1.0 - (hamming_distance / len(hash1))
            return max(0.0, similarity)
        
        # String similarity for different lengths
        from difflib import SequenceMatcher
        return SequenceMatcher(None, hash1, hash2).ratio()
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.warning(f"Cosine similarity calculation failed: {str(e)}")
            return 0.0
    
    def _calculate_weighted_confidence(self, similarity_scores: Dict[str, float]) -> float:
        """Calculate weighted overall confidence score"""
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for method, score in similarity_scores.items():
            if method in self.method_weights:
                weight = self.method_weights[method]
                weighted_sum += score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _determine_match_type(self, confidence_score: float) -> str:
        """Determine match type based on confidence score"""
        
        if confidence_score >= self.thresholds["exact_match"]:
            return "exact"
        elif confidence_score >= self.thresholds["near_duplicate"]:
            return "near_duplicate"
        elif confidence_score >= self.thresholds["derivative"]:
            return "derivative"
        elif confidence_score >= self.thresholds["similar"]:
            return "similar"
        else:
            return "no_match"
    
    def _generate_ai_reasoning(self, similarity_scores: Dict[str, float], match_type: str) -> str:
        """Generate AI reasoning for the match decision"""
        
        # Find strongest matching methods
        top_methods = sorted(similarity_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        reasoning_parts = [f"Match classification: {match_type}"]
        
        if match_type == "exact":
            reasoning_parts.append("Strong evidence of identical or nearly identical content.")
        elif match_type == "near_duplicate":
            reasoning_parts.append("High similarity suggests near-duplicate content with minor modifications.")
        elif match_type == "derivative":
            reasoning_parts.append("Significant similarity indicates derivative work or substantial copying.")
        elif match_type == "similar":
            reasoning_parts.append("Moderate similarity suggests partial copying or similar content themes.")
        
        # Add method-specific details
        method_details = []
        for method, score in top_methods:
            if score > 0.7:
                method_name = method.replace('_', ' ').title()
                method_details.append(f"{method_name}: {score:.1%}")
        
        if method_details:
            reasoning_parts.append(f"Strongest matches: {', '.join(method_details)}")
        
        return " ".join(reasoning_parts)
    
    def _make_decision_recommendation(self, confidence_score: float) -> str:
        """Make automated decision recommendation"""
        
        if confidence_score >= 0.90:
            return "auto_approve"
        elif confidence_score < 0.60:
            return "auto_reject"
        else:
            return "manual_review"
    
    def _create_no_match(self, original_id: str, candidate_id: str) -> SimilarityMatch:
        """Create a no-match result"""
        
        return SimilarityMatch(
            original_content_id=original_id,
            matched_content_id=candidate_id,
            confidence_score=0.0,
            confidence_level=MatchConfidenceLevel.VERY_LOW,
            match_type="no_match",
            similarity_scores={},
            ai_reasoning="Content types differ or insufficient similarity detected.",
            decision_recommendation="auto_reject"
        )

class AIContentMatchingService:
    """Main service orchestrating AI-powered content matching"""
    
    def __init__(self, 
                 device: str = "cpu",
                 cache_dir: str = "/tmp/autodmca_cache"):
        
        self.device = device
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sub-services
        self.fingerprint_service = ContentFingerprintService(device)
        self.similarity_service = SimilarityDetectionService(device)
        
        # Performance metrics
        self.metrics = {
            "total_comparisons": 0,
            "exact_matches": 0,
            "near_duplicates": 0,
            "manual_reviews": 0,
            "false_positives": 0,
            "processing_time_ms": []
        }
        
        logger.info("AI Content Matching Service initialized")
    
    async def detect_infringement(
        self, 
        original_content_path: str,
        candidate_content_path: str,
        content_type: ContentType,
        original_id: str = None,
        candidate_id: str = None
    ) -> SimilarityMatch:
        """Detect potential infringement between original and candidate content"""
        
        start_time = datetime.utcnow()
        
        try:
            # Generate fingerprints
            original_fp = await self.fingerprint_service.generate_fingerprint(
                original_content_path, content_type, original_id
            )
            
            candidate_fp = await self.fingerprint_service.generate_fingerprint(
                candidate_content_path, content_type, candidate_id
            )
            
            # Compare content
            match_result = await self.similarity_service.compare_content(original_fp, candidate_fp)
            
            # Update metrics
            self._update_metrics(match_result, start_time)
            
            return match_result
            
        except Exception as e:
            logger.error(f"Infringement detection failed: {str(e)}")
            raise
    
    async def batch_detect_infringement(
        self,
        original_content_path: str,
        candidate_paths: List[str],
        content_type: ContentType,
        original_id: str = None,
        max_concurrent: int = 10
    ) -> List[SimilarityMatch]:
        """Detect infringement across multiple candidate files"""
        
        # Generate fingerprint for original content once
        original_fp = await self.fingerprint_service.generate_fingerprint(
            original_content_path, content_type, original_id
        )
        
        # Process candidates in batches
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_candidate(candidate_path: str) -> SimilarityMatch:
            async with semaphore:
                try:
                    candidate_fp = await self.fingerprint_service.generate_fingerprint(
                        candidate_path, content_type
                    )
                    return await self.similarity_service.compare_content(original_fp, candidate_fp)
                except Exception as e:
                    logger.error(f"Failed to process candidate {candidate_path}: {str(e)}")
                    return self.similarity_service._create_no_match(original_fp.content_id, candidate_path)
        
        # Execute batch processing
        tasks = [process_candidate(path) for path in candidate_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = [r for r in results if isinstance(r, SimilarityMatch)]
        
        return valid_results
    
    async def analyze_platform_content(
        self,
        platform: str,
        content_urls: List[str],
        original_content_path: str,
        content_type: ContentType
    ) -> List[SimilarityMatch]:
        """Analyze content from a specific platform for potential infringement"""
        
        matches = []
        
        # Download and analyze each piece of content
        for url in content_urls:
            try:
                # Download content
                temp_path = await self._download_content(url, platform)
                
                if temp_path:
                    # Detect infringement
                    match = await self.detect_infringement(
                        original_content_path, temp_path, content_type
                    )
                    
                    matches.append(match)
                    
                    # Clean up temp file
                    Path(temp_path).unlink(missing_ok=True)
                    
            except Exception as e:
                logger.error(f"Failed to analyze content from {url}: {str(e)}")
                continue
        
        return matches
    
    async def _download_content(self, url: str, platform: str) -> Optional[str]:
        """Download content from URL for analysis"""
        
        try:
            # Create platform-specific temp directory
            platform_cache = self.cache_dir / platform
            platform_cache.mkdir(exist_ok=True)
            
            # Generate temp filename
            url_hash = hashlib.md5(url.encode()).hexdigest()
            temp_path = platform_cache / f"{url_hash}_{int(datetime.utcnow().timestamp())}"
            
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        async with aiofiles.open(temp_path, 'wb') as f:
                            await f.write(content)
                        
                        return str(temp_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Content download failed from {url}: {str(e)}")
            return None
    
    def _update_metrics(self, match_result: SimilarityMatch, start_time: datetime):
        """Update service metrics"""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        self.metrics["total_comparisons"] += 1
        self.metrics["processing_time_ms"].append(processing_time)
        
        if match_result.match_type == "exact":
            self.metrics["exact_matches"] += 1
        elif match_result.match_type == "near_duplicate":
            self.metrics["near_duplicates"] += 1
        elif match_result.decision_recommendation == "manual_review":
            self.metrics["manual_reviews"] += 1
        
        # Keep only recent processing times
        if len(self.metrics["processing_time_ms"]) > 1000:
            self.metrics["processing_time_ms"] = self.metrics["processing_time_ms"][-1000:]
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        
        processing_times = self.metrics["processing_time_ms"]
        
        return {
            **self.metrics,
            "avg_processing_time_ms": np.mean(processing_times) if processing_times else 0,
            "p95_processing_time_ms": np.percentile(processing_times, 95) if processing_times else 0,
            "accuracy_rate": self._calculate_accuracy_rate(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_accuracy_rate(self) -> float:
        """Calculate estimated accuracy rate based on metrics"""
        
        total = self.metrics["total_comparisons"]
        if total == 0:
            return 0.0
        
        # Estimated accuracy based on exact matches and near duplicates
        accurate = self.metrics["exact_matches"] + self.metrics["near_duplicates"]
        false_positives = self.metrics["false_positives"]
        
        return max(0.0, (accurate - false_positives) / total)
    
    async def report_false_positive(self, match_id: str, reason: str = None):
        """Report a false positive for model improvement"""
        
        self.metrics["false_positives"] += 1
        
        # Log for model retraining
        logger.info(f"False positive reported for match {match_id}: {reason}")
        
        # In production, this would trigger model retraining pipeline
        # For now, just update metrics
    
    async def cleanup_cache(self, max_age_hours: int = 24):
        """Clean up old cached files"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cutoff_timestamp = cutoff_time.timestamp()
        
        for cache_file in self.cache_dir.rglob("*"):
            if cache_file.is_file():
                try:
                    # Extract timestamp from filename
                    if "_" in cache_file.name:
                        timestamp_str = cache_file.name.split("_")[-1]
                        file_timestamp = float(timestamp_str)
                        
                        if file_timestamp < cutoff_timestamp:
                            cache_file.unlink()
                            logger.debug(f"Cleaned up old cache file: {cache_file}")
                            
                except (ValueError, OSError) as e:
                    logger.warning(f"Failed to clean up cache file {cache_file}: {str(e)}")