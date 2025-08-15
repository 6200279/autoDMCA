"""
Optimized AI-Powered Content Matching System
High-performance implementation with batching, caching, and GPU acceleration
"""
import asyncio
import hashlib
import io
import json
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple, Union
import logging

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision import models
import cv2
import face_recognition
import imagehash
from PIL import Image
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    EXACT = "exact"
    FACE = "face"
    SIMILAR_IMAGE = "similar_image"
    PERCEPTUAL_HASH = "perceptual_hash"
    TEXT_MATCH = "text_match"
    WATERMARK = "watermark"


@dataclass
class ContentMatch:
    """Result of content matching with performance metrics"""
    match_type: MatchType
    confidence: float
    source_url: str
    matched_content_id: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    processing_time_ms: float = 0.0


@dataclass
class ProcessingMetrics:
    """Performance metrics for monitoring"""
    total_time_ms: float
    model_inference_time_ms: float
    preprocessing_time_ms: float
    cache_hits: int
    cache_misses: int
    batch_size: int
    memory_used_mb: float


class ImageBatchDataset(Dataset):
    """Custom dataset for batch processing images"""
    
    def __init__(self, images: List[Image.Image], transform=None):
        self.images = images
        self.transform = transform
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        image = self.images[idx]
        if self.transform:
            image = self.transform(image)
        return image


class ModelCache:
    """Optimized model caching with memory management"""
    
    def __init__(self):
        self._models = {}
        self._last_access = {}
        self._max_cache_size = 3
        
    def get_model(self, model_name: str):
        """Get cached model or load if not in cache"""
        if model_name in self._models:
            self._last_access[model_name] = time.time()
            return self._models[model_name]
        
        # Evict oldest model if cache full
        if len(self._models) >= self._max_cache_size:
            oldest_model = min(self._last_access.items(), key=lambda x: x[1])[0]
            del self._models[oldest_model]
            del self._last_access[oldest_model]
            logger.info(f"Evicted model from cache: {oldest_model}")
        
        # Load new model
        model = self._load_model(model_name)
        self._models[model_name] = model
        self._last_access[model_name] = time.time()
        return model
    
    def _load_model(self, model_name: str):
        """Load model with optimizations"""
        if model_name == "resnet50":
            model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
            model = torch.nn.Sequential(*list(model.children())[:-1])
            
            # Optimize for inference
            model.eval()
            for param in model.parameters():
                param.requires_grad = False
            
            # Move to GPU if available
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)
            
            # Compile model for faster inference (PyTorch 2.0+)
            if hasattr(torch, 'compile'):
                model = torch.compile(model)
            
            return model
        
        raise ValueError(f"Unknown model: {model_name}")


class OptimizedContentMatcher:
    """
    High-performance AI content matching with advanced optimizations
    - Batch processing for improved throughput
    - Multi-level caching (Redis + in-memory)
    - GPU acceleration and model optimization
    - Async processing with connection pooling
    - Memory management and resource cleanup
    """
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_cache = ModelCache()
        self.redis_client: Optional[redis.Redis] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Performance settings
        self.batch_size = getattr(settings, 'AI_BATCH_SIZE', 8)
        self.cache_ttl = getattr(settings, 'AI_CACHE_TTL', 3600)  # 1 hour
        self.enable_gpu = torch.cuda.is_available()
        
        # In-memory caches with LRU eviction
        self._face_encoding_cache = {}
        self._image_feature_cache = {}
        self._hash_cache = {}
        
        # Cache size limits
        self._max_cache_items = 1000
        
        # Performance tracking
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_processing_time': 0.0,
            'gpu_memory_usage': 0.0
        }
        
        logger.info(f"Initialized OptimizedContentMatcher with device: {self.device}")
        if self.enable_gpu:
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    
    async def initialize(self):
        """Initialize async components"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Warm up models
            await self._warmup_models()
            
        except Exception as e:
            logger.error(f"Failed to initialize OptimizedContentMatcher: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        self.executor.shutdown(wait=True)
        
        # Clear GPU memory
        if self.enable_gpu:
            torch.cuda.empty_cache()
    
    async def _warmup_models(self):
        """Warm up models for better first-request performance"""
        try:
            # Create dummy batch
            dummy_image = Image.new('RGB', (224, 224), color='red')
            dummy_batch = [dummy_image] * 2
            
            # Warm up ResNet
            await self._extract_features_batch(dummy_batch)
            
            # Warm up face recognition
            dummy_array = np.array(dummy_image)
            face_recognition.face_locations(dummy_array)
            
            logger.info("Model warmup completed")
            
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    async def analyze_content_batch(
        self,
        content_items: List[Tuple[str, bytes, Dict[str, Any]]]
    ) -> List[List[ContentMatch]]:
        """
        Analyze multiple content items in batch for optimal performance
        Args:
            content_items: List of (url, content_data, profile_data) tuples
        Returns:
            List of ContentMatch lists for each item
        """
        start_time = time.time()
        batch_metrics = ProcessingMetrics(
            total_time_ms=0.0,
            model_inference_time_ms=0.0,
            preprocessing_time_ms=0.0,
            cache_hits=0,
            cache_misses=0,
            batch_size=len(content_items),
            memory_used_mb=0.0
        )
        
        try:
            # Group by content type for optimized processing
            image_items = []
            video_items = []
            text_items = []
            
            for i, (url, content_data, profile_data) in enumerate(content_items):
                content_type = self._detect_content_type(content_data)
                if content_type == 'image':
                    image_items.append((i, url, content_data, profile_data))
                elif content_type == 'video':
                    video_items.append((i, url, content_data, profile_data))
                elif content_type == 'text':
                    text_items.append((i, url, content_data, profile_data))
            
            # Process each type in optimized batches
            results = [[] for _ in content_items]
            
            # Process images in batch
            if image_items:
                image_results = await self._process_image_batch(image_items, batch_metrics)
                for (i, _, _, _), matches in zip(image_items, image_results):
                    results[i] = matches
            
            # Process videos (can be parallelized)
            if video_items:
                video_tasks = [
                    self._analyze_video_optimized(url, content_data, profile_data)
                    for _, url, content_data, profile_data in video_items
                ]
                video_results = await asyncio.gather(*video_tasks, return_exceptions=True)
                for (i, _, _, _), matches in zip(video_items, video_results):
                    if isinstance(matches, list):
                        results[i] = matches
                    else:
                        logger.error(f"Video processing error: {matches}")
                        results[i] = []
            
            # Process text items
            if text_items:
                text_tasks = [
                    self._analyze_text(url, content_data, profile_data)
                    for _, url, content_data, profile_data in text_items
                ]
                text_results = await asyncio.gather(*text_tasks)
                for (i, _, _, _), matches in zip(text_items, text_results):
                    results[i] = matches
            
            # Update metrics
            batch_metrics.total_time_ms = (time.time() - start_time) * 1000
            batch_metrics.memory_used_mb = self._get_memory_usage()
            
            self._update_global_metrics(batch_metrics)
            
            logger.info(f"Batch processed: {len(content_items)} items in {batch_metrics.total_time_ms:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return [[] for _ in content_items]
    
    async def _process_image_batch(
        self,
        image_items: List[Tuple[int, str, bytes, Dict[str, Any]]],
        metrics: ProcessingMetrics
    ) -> List[List[ContentMatch]]:
        """Process multiple images in an optimized batch"""
        preprocessing_start = time.time()
        
        # Load and preprocess images
        images = []
        valid_indices = []
        
        for i, (_, url, image_data, profile_data) in enumerate(image_items):
            try:
                image = Image.open(io.BytesIO(image_data))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                images.append(image)
                valid_indices.append(i)
            except Exception as e:
                logger.error(f"Failed to load image {url}: {e}")
        
        if not images:
            return [[] for _ in image_items]
        
        metrics.preprocessing_time_ms += (time.time() - preprocessing_start) * 1000
        
        # Batch feature extraction
        inference_start = time.time()
        features_batch = await self._extract_features_batch(images)
        metrics.model_inference_time_ms += (time.time() - inference_start) * 1000
        
        # Process each image with extracted features
        results = []
        for idx, (orig_idx, url, image_data, profile_data) in enumerate(image_items):
            if idx in valid_indices:
                feature_idx = valid_indices.index(idx)
                image = images[feature_idx]
                features = features_batch[feature_idx] if features_batch else None
                
                matches = await self._analyze_single_image_with_features(
                    url, image, image_data, profile_data, features, metrics
                )
                results.append(matches)
            else:
                results.append([])
        
        return results
    
    async def _extract_features_batch(self, images: List[Image.Image]) -> Optional[np.ndarray]:
        """Extract deep learning features for batch of images"""
        try:
            if not images:
                return None
            
            # Get model
            model = self.model_cache.get_model("resnet50")
            
            # Prepare transforms
            transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            # Create dataset and dataloader
            dataset = ImageBatchDataset(images, transform)
            dataloader = DataLoader(
                dataset,
                batch_size=min(self.batch_size, len(images)),
                shuffle=False,
                num_workers=0,  # Keep 0 for Windows compatibility
                pin_memory=self.enable_gpu
            )
            
            features_list = []
            
            with torch.no_grad():
                for batch in dataloader:
                    batch = batch.to(self.device, non_blocking=True)
                    
                    # Extract features
                    batch_features = model(batch)
                    batch_features = batch_features.squeeze().cpu().numpy()
                    
                    if batch_features.ndim == 1:
                        batch_features = batch_features.reshape(1, -1)
                    
                    features_list.append(batch_features)
            
            return np.vstack(features_list) if features_list else None
            
        except Exception as e:
            logger.error(f"Batch feature extraction error: {e}")
            return None
    
    async def _analyze_single_image_with_features(
        self,
        url: str,
        image: Image.Image,
        image_data: bytes,
        profile_data: Dict[str, Any],
        features: Optional[np.ndarray],
        metrics: ProcessingMetrics
    ) -> List[ContentMatch]:
        """Analyze single image with pre-extracted features"""
        matches = []
        
        try:
            # 1. Face Recognition (cached)
            if profile_data.get('face_encodings'):
                cache_key = f"face:{hashlib.md5(image_data).hexdigest()}"
                cached_faces = await self._get_from_cache(cache_key)
                
                if cached_faces is not None:
                    face_matches = cached_faces
                    metrics.cache_hits += 1
                else:
                    face_matches = await self._check_face_match_optimized(image, profile_data['face_encodings'], url)
                    await self._set_cache(cache_key, face_matches, ttl=self.cache_ttl)
                    metrics.cache_misses += 1
                
                matches.extend(face_matches)
            
            # 2. Perceptual Hash (cached)
            if profile_data.get('content_hashes'):
                cache_key = f"hash:{hashlib.md5(image_data).hexdigest()}"
                cached_hash_match = await self._get_from_cache(cache_key)
                
                if cached_hash_match is not None:
                    if cached_hash_match:
                        matches.append(cached_hash_match)
                    metrics.cache_hits += 1
                else:
                    hash_match = await self._check_perceptual_hash_optimized(image, profile_data['content_hashes'], url)
                    await self._set_cache(cache_key, hash_match, ttl=self.cache_ttl)
                    if hash_match:
                        matches.append(hash_match)
                    metrics.cache_misses += 1
            
            # 3. Deep Learning Features (use pre-extracted)
            if features is not None and profile_data.get('image_features'):
                feature_match = await self._check_feature_match_optimized(features, profile_data['image_features'], url)
                if feature_match:
                    matches.append(feature_match)
            
            # 4. Watermark Detection
            if profile_data.get('watermarks'):
                watermark_match = await self._check_watermark_optimized(image, profile_data['watermarks'], url)
                if watermark_match:
                    matches.append(watermark_match)
        
        except Exception as e:
            logger.error(f"Error analyzing image {url}: {e}")
        
        return matches
    
    async def _check_face_match_optimized(
        self,
        image: Image.Image,
        known_encodings: List[np.ndarray],
        url: str
    ) -> List[ContentMatch]:
        """Optimized face matching with threading"""
        matches = []
        
        try:
            # Convert to numpy array in thread pool
            image_np = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: np.array(image)
            )
            
            # Face detection in thread pool
            face_locations = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                face_recognition.face_locations,
                image_np
            )
            
            if face_locations:
                # Face encoding in thread pool
                face_encodings = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    face_recognition.face_encodings,
                    image_np,
                    face_locations
                )
                
                # Compare encodings
                for face_encoding in face_encodings:
                    for known_encoding in known_encodings:
                        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                        confidence = 1.0 - min(distance, 1.0)
                        
                        if confidence > settings.FACE_RECOGNITION_TOLERANCE:
                            matches.append(ContentMatch(
                                match_type=MatchType.FACE,
                                confidence=confidence,
                                source_url=url,
                                matched_content_id=None,
                                metadata={
                                    "face_count": len(face_locations),
                                    "distance": float(distance),
                                    "optimized": True
                                },
                                timestamp=datetime.utcnow()
                            ))
                            break
        
        except Exception as e:
            logger.error(f"Optimized face recognition error: {e}")
        
        return matches
    
    async def _check_perceptual_hash_optimized(
        self,
        image: Image.Image,
        known_hashes: List[str],
        url: str
    ) -> Optional[ContentMatch]:
        """Optimized perceptual hashing"""
        try:
            # Generate hashes in thread pool
            hashes = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._generate_all_hashes,
                image
            )
            
            # Check against known hashes
            for known_hash_data in known_hashes:
                for hash_type, current_hash in hashes.items():
                    known_hash = known_hash_data.get(hash_type)
                    
                    if known_hash:
                        distance = imagehash.hex_to_hash(current_hash) - imagehash.hex_to_hash(known_hash)
                        
                        if distance < 10:
                            confidence = 1.0 - (distance / 64.0)
                            
                            return ContentMatch(
                                match_type=MatchType.PERCEPTUAL_HASH,
                                confidence=confidence,
                                source_url=url,
                                matched_content_id=known_hash_data.get('content_id'),
                                metadata={
                                    "hash_type": hash_type,
                                    "distance": distance,
                                    "hash": current_hash,
                                    "optimized": True
                                },
                                timestamp=datetime.utcnow()
                            )
        
        except Exception as e:
            logger.error(f"Optimized perceptual hash error: {e}")
        
        return None
    
    def _generate_all_hashes(self, image: Image.Image) -> Dict[str, str]:
        """Generate all hash types for an image"""
        return {
            'average': str(imagehash.average_hash(image)),
            'perceptual': str(imagehash.phash(image)),
            'difference': str(imagehash.dhash(image)),
            'wavelet': str(imagehash.whash(image))
        }
    
    async def _check_feature_match_optimized(
        self,
        features: np.ndarray,
        known_features: List[np.ndarray],
        url: str
    ) -> Optional[ContentMatch]:
        """Optimized feature matching using vectorized operations"""
        try:
            # Vectorized similarity computation
            similarities = []
            for known_feature in known_features:
                similarity = np.dot(features, known_feature) / (
                    np.linalg.norm(features) * np.linalg.norm(known_feature)
                )
                similarities.append(similarity)
            
            max_similarity = max(similarities) if similarities else 0.0
            
            if max_similarity > settings.CONTENT_SIMILARITY_THRESHOLD:
                return ContentMatch(
                    match_type=MatchType.SIMILAR_IMAGE,
                    confidence=float(max_similarity),
                    source_url=url,
                    matched_content_id=None,
                    metadata={
                        "similarity": float(max_similarity),
                        "method": "optimized_deep_features",
                        "feature_dim": len(features)
                    },
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            logger.error(f"Optimized feature matching error: {e}")
        
        return None
    
    async def _check_watermark_optimized(
        self,
        image: Image.Image,
        watermarks: List[Dict[str, Any]],
        url: str
    ) -> Optional[ContentMatch]:
        """Optimized watermark detection"""
        # Placeholder for watermark detection optimization
        return None
    
    async def _analyze_video_optimized(
        self,
        url: str,
        video_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """Optimized video analysis with frame sampling and parallel processing"""
        matches = []
        
        try:
            # Save video temporarily
            temp_path = f"/tmp/video_{hashlib.md5(url.encode()).hexdigest()}.mp4"
            with open(temp_path, 'wb') as f:
                f.write(video_data)
            
            # Smart frame sampling
            cap = cv2.VideoCapture(temp_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Sample frames more intelligently
            sample_interval = max(1, int(fps * 3))  # Every 3 seconds
            max_frames = 20  # Limit total frames processed
            
            frame_indices = list(range(0, total_frames, sample_interval))[:max_frames]
            
            # Extract frames
            frames = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append((frame_idx, pil_image))
            
            cap.release()
            
            # Process frames in batch
            if frames:
                frame_images = [img for _, img in frames]
                frame_bytes_list = [self._image_to_bytes(img) for img in frame_images]
                
                # Create batch items
                batch_items = [
                    (i, url, frame_bytes, profile_data) 
                    for i, frame_bytes in enumerate(frame_bytes_list)
                ]
                
                # Process batch
                frame_results = await self._process_image_batch(batch_items, ProcessingMetrics(
                    total_time_ms=0, model_inference_time_ms=0, preprocessing_time_ms=0,
                    cache_hits=0, cache_misses=0, batch_size=len(batch_items), memory_used_mb=0
                ))
                
                # Collect matches with frame info
                for i, frame_matches in enumerate(frame_results):
                    frame_idx = frames[i][0] if i < len(frames) else 0
                    for match in frame_matches:
                        match.metadata.update({
                            'frame_number': frame_idx,
                            'video': True,
                            'total_frames_sampled': len(frames)
                        })
                        matches.append(match)
            
            # Clean up
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        except Exception as e:
            logger.error(f"Optimized video analysis error: {e}")
        
        return matches
    
    async def _analyze_text(
        self,
        url: str,
        text_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """Optimized text analysis"""
        matches = []
        
        try:
            text = text_data.decode('utf-8', errors='ignore').lower()
            
            # Vectorized keyword matching
            username = profile_data.get('username', '').lower()
            keywords = [kw.lower() for kw in profile_data.get('keywords', [])]
            
            all_terms = [username] + keywords if username else keywords
            
            for term in all_terms:
                if term and term in text:
                    count = text.count(term)
                    confidence = min(1.0, count * 0.2)
                    
                    matches.append(ContentMatch(
                        match_type=MatchType.TEXT_MATCH,
                        confidence=confidence,
                        source_url=url,
                        matched_content_id=None,
                        metadata={
                            "term": term,
                            "occurrences": count,
                            "text_length": len(text),
                            "optimized": True
                        },
                        timestamp=datetime.utcnow()
                    ))
        
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
        
        return matches
    
    async def _get_from_cache(self, key: str) -> Any:
        """Get item from Redis cache with fallback to in-memory"""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    return pickle.loads(cached_data)
            
            # Fallback to in-memory cache
            return self._face_encoding_cache.get(key)
        
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def _set_cache(self, key: str, value: Any, ttl: int = 3600):
        """Set item in Redis cache with fallback to in-memory"""
        try:
            if self.redis_client:
                await self.redis_client.setex(key, ttl, pickle.dumps(value))
            
            # Also store in memory cache (with size limit)
            if len(self._face_encoding_cache) >= self._max_cache_items:
                # Remove oldest item
                oldest_key = next(iter(self._face_encoding_cache))
                del self._face_encoding_cache[oldest_key]
            
            self._face_encoding_cache[key] = value
        
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def _detect_content_type(self, content_data: bytes) -> str:
        """Optimized content type detection"""
        if not content_data:
            return 'unknown'
        
        # Check first few bytes for magic numbers
        header = content_data[:12]
        
        if header.startswith(b'\xff\xd8\xff'):
            return 'image'  # JPEG
        elif header.startswith(b'\x89PNG'):
            return 'image'  # PNG
        elif header.startswith(b'GIF8'):
            return 'image'  # GIF
        elif header.startswith(b'RIFF') and b'WEBP' in header:
            return 'image'  # WebP
        elif header[4:8] == b'ftyp' or header.startswith(b'\x00\x00\x00\x18ftypmp4'):
            return 'video'  # MP4
        elif header.startswith(b'\x1aE\xdf\xa3'):
            return 'video'  # WebM
        elif b'<html' in content_data[:1000].lower():
            return 'text'  # HTML
        else:
            return 'unknown'
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to bytes efficiently"""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', optimize=True)
        return img_byte_arr.getvalue()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _update_global_metrics(self, batch_metrics: ProcessingMetrics):
        """Update global performance metrics"""
        self.metrics['total_requests'] += batch_metrics.batch_size
        self.metrics['cache_hits'] += batch_metrics.cache_hits
        self.metrics['cache_misses'] += batch_metrics.cache_misses
        
        # Update average processing time
        current_avg = self.metrics['average_processing_time']
        new_avg = (current_avg + batch_metrics.total_time_ms) / 2
        self.metrics['average_processing_time'] = new_avg
        
        if self.enable_gpu:
            try:
                self.metrics['gpu_memory_usage'] = torch.cuda.memory_allocated() / 1024**3  # GB
            except:
                pass
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        cache_hit_rate = 0.0
        total_cache_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total_cache_requests > 0:
            cache_hit_rate = self.metrics['cache_hits'] / total_cache_requests
        
        return {
            'total_requests': self.metrics['total_requests'],
            'cache_hit_rate': cache_hit_rate,
            'average_processing_time_ms': self.metrics['average_processing_time'],
            'gpu_memory_usage_gb': self.metrics['gpu_memory_usage'],
            'device': str(self.device),
            'batch_size': self.batch_size,
            'models_cached': len(self.model_cache._models)
        }

    # Legacy compatibility method
    async def analyze_content(
        self,
        content_url: str,
        content_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """
        Legacy single-item analysis method for backward compatibility
        Internally uses batch processing for optimization
        """
        results = await self.analyze_content_batch([(content_url, content_data, profile_data)])
        return results[0] if results else []