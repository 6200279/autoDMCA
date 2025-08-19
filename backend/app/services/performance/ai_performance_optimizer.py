"""
AI Model Performance Optimizer
Advanced optimization system for AI inference with GPU acceleration, quantization, and intelligent batching
"""
import asyncio
import time
import threading
import gc
from collections import deque, defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import logging
import json
import psutil

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.cuda.amp import autocast, GradScaler
import torchvision.transforms as transforms
from torchvision import models
import cv2
import face_recognition
import imagehash
from PIL import Image
import redis.asyncio as redis

from app.core.config import settings
from app.services.monitoring.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class OptimizationLevel(str, Enum):
    """AI optimization levels"""
    SPEED = "speed"           # Maximum speed, lower accuracy
    BALANCED = "balanced"     # Balance of speed and accuracy
    ACCURACY = "accuracy"     # Maximum accuracy, may be slower
    MEMORY = "memory"         # Memory optimized


class ModelType(str, Enum):
    """Supported AI model types"""
    FACE_RECOGNITION = "face_recognition"
    IMAGE_CLASSIFICATION = "image_classification"
    FEATURE_EXTRACTION = "feature_extraction"
    HASH_COMPUTATION = "hash_computation"


@dataclass
class BatchRequest:
    """Batch processing request"""
    id: str
    model_type: ModelType
    data: Any
    callback: Optional[Callable] = None
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_ms: int = 2000


@dataclass
class ModelMetrics:
    """Model performance metrics"""
    total_inferences: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    batch_sizes: List[int] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0


class OptimizedModelPool:
    """Advanced model pool with dynamic scaling and optimization"""
    
    def __init__(self, model_factory: Callable, initial_size: int = 2, max_size: int = 4):
        self.model_factory = model_factory
        self.initial_size = initial_size
        self.max_size = max_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Model pool
        self.models = []
        self.model_locks = []
        self.model_usage_counts = []
        self.model_last_used = []
        
        # Performance tracking
        self.load_balancer_stats = defaultdict(int)
        self.warmup_completed = False
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize model pool"""
        logger.info(f"Initializing model pool with {self.initial_size} models on {self.device}")
        
        for i in range(self.initial_size):
            model = self._create_optimized_model()
            lock = threading.Lock()
            
            self.models.append(model)
            self.model_locks.append(lock)
            self.model_usage_counts.append(0)
            self.model_last_used.append(time.time())
        
        # Warmup models
        self._warmup_models()
    
    def _create_optimized_model(self):
        """Create and optimize model"""
        model = self.model_factory()
        model = model.to(self.device)
        model.eval()
        
        # Apply optimizations based on device and settings
        if torch.cuda.is_available():
            # Enable mixed precision
            model.half()
            
            # JIT compilation for faster inference
            try:
                # Dummy input for tracing
                dummy_input = torch.randn(1, 3, 224, 224).half().to(self.device)
                model = torch.jit.trace(model, dummy_input)
                logger.info("Model JIT compiled successfully")
            except Exception as e:
                logger.warning(f"JIT compilation failed: {e}")
        
        # Enable optimizations
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        
        return model
    
    def _warmup_models(self):
        """Warmup all models for optimal performance"""
        logger.info("Warming up model pool...")
        
        dummy_input = torch.randn(4, 3, 224, 224).to(self.device)
        if torch.cuda.is_available():
            dummy_input = dummy_input.half()
        
        for i, model in enumerate(self.models):
            with torch.no_grad():
                for _ in range(5):  # 5 warmup iterations
                    _ = model(dummy_input)
            logger.info(f"Model {i+1} warmed up")
        
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        
        self.warmup_completed = True
        logger.info("Model pool warmup completed")
    
    def get_optimal_model(self, batch_size: int = 1) -> Tuple[Any, threading.Lock, int]:
        """Get optimal model based on current load and batch size"""
        # Try to find immediately available model
        for i, (model, lock) in enumerate(zip(self.models, self.model_locks)):
            if lock.acquire(blocking=False):
                self.model_usage_counts[i] += 1
                self.model_last_used[i] = time.time()
                self.load_balancer_stats['immediate_acquisition'] += 1
                return model, lock, i
        
        # If no immediate model available, scale if possible
        if len(self.models) < self.max_size:
            self._scale_up()
            return self.get_optimal_model(batch_size)
        
        # Wait for least recently used model
        lru_index = min(range(len(self.model_last_used)), 
                       key=lambda i: self.model_last_used[i])
        
        lock = self.model_locks[lru_index]
        lock.acquire()  # This will block
        
        self.model_usage_counts[lru_index] += 1
        self.model_last_used[lru_index] = time.time()
        self.load_balancer_stats['waited_acquisition'] += 1
        
        return self.models[lru_index], lock, lru_index
    
    def _scale_up(self):
        """Add new model to pool"""
        if len(self.models) >= self.max_size:
            return
        
        logger.info(f"Scaling up model pool: {len(self.models)} -> {len(self.models) + 1}")
        
        model = self._create_optimized_model()
        lock = threading.Lock()
        
        self.models.append(model)
        self.model_locks.append(lock)
        self.model_usage_counts.append(0)
        self.model_last_used.append(time.time())
        
        # Warmup new model
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
        if torch.cuda.is_available():
            dummy_input = dummy_input.half()
        
        with torch.no_grad():
            for _ in range(3):
                _ = model(dummy_input)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            'pool_size': len(self.models),
            'max_size': self.max_size,
            'usage_counts': self.model_usage_counts,
            'load_balancer_stats': dict(self.load_balancer_stats),
            'warmup_completed': self.warmup_completed
        }


class IntelligentBatchProcessor:
    """Intelligent batch processor with dynamic optimization"""
    
    def __init__(self, max_batch_size: int = 32, max_wait_ms: int = 50):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        
        # Batch queues for different model types
        self.queues: Dict[ModelType, asyncio.Queue] = {
            model_type: asyncio.Queue() for model_type in ModelType
        }
        
        # Processing tasks
        self.processor_tasks: Dict[ModelType, asyncio.Task] = {}
        
        # Adaptive batch sizing
        self.optimal_batch_sizes: Dict[ModelType, int] = {
            ModelType.FACE_RECOGNITION: 4,
            ModelType.IMAGE_CLASSIFICATION: 16,
            ModelType.FEATURE_EXTRACTION: 8,
            ModelType.HASH_COMPUTATION: 32
        }
        
        # Performance tracking
        self.batch_metrics: Dict[ModelType, List[float]] = defaultdict(list)
        
        # Start processors
        self._start_processors()
    
    def _start_processors(self):
        """Start batch processors for each model type"""
        for model_type in ModelType:
            task = asyncio.create_task(self._process_batches(model_type))
            self.processor_tasks[model_type] = task
    
    async def _process_batches(self, model_type: ModelType):
        """Process batches for specific model type"""
        while True:
            try:
                batch = await self._collect_batch(model_type)
                if batch:
                    await self._execute_batch(model_type, batch)
            except Exception as e:
                logger.error(f"Batch processing error for {model_type}: {e}")
                await asyncio.sleep(0.1)
    
    async def _collect_batch(self, model_type: ModelType) -> List[BatchRequest]:
        """Collect optimal batch for processing"""
        batch = []
        queue = self.queues[model_type]
        optimal_size = self.optimal_batch_sizes[model_type]
        
        # Wait for first item
        try:
            first_item = await asyncio.wait_for(queue.get(), timeout=1.0)
            batch.append(first_item)
        except asyncio.TimeoutError:
            return []
        
        # Collect additional items with timeout
        start_time = time.time()
        while (len(batch) < optimal_size and 
               (time.time() - start_time) * 1000 < self.max_wait_ms):
            
            try:
                timeout = max(0, (self.max_wait_ms - (time.time() - start_time) * 1000) / 1000)
                item = await asyncio.wait_for(queue.get(), timeout=timeout)
                batch.append(item)
            except asyncio.TimeoutError:
                break
        
        return batch
    
    async def _execute_batch(self, model_type: ModelType, batch: List[BatchRequest]):
        """Execute batch processing"""
        if not batch:
            return
        
        start_time = time.time()
        batch_size = len(batch)
        
        try:
            # Process based on model type
            if model_type == ModelType.FACE_RECOGNITION:
                await self._process_face_batch(batch)
            elif model_type == ModelType.IMAGE_CLASSIFICATION:
                await self._process_classification_batch(batch)
            elif model_type == ModelType.FEATURE_EXTRACTION:
                await self._process_feature_batch(batch)
            elif model_type == ModelType.HASH_COMPUTATION:
                await self._process_hash_batch(batch)
            
            # Update performance metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self.batch_metrics[model_type].append(elapsed_ms)
            
            # Adaptive batch size optimization
            self._optimize_batch_size(model_type, batch_size, elapsed_ms)
            
        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            # Notify all requests of failure
            for request in batch:
                if request.callback:
                    try:
                        await request.callback(None, error=e)
                    except Exception:
                        pass
    
    async def _process_face_batch(self, batch: List[BatchRequest]):
        """Process face recognition batch"""
        # Extract images
        images = [req.data for req in batch]
        
        # Process in parallel using thread pool
        loop = asyncio.get_event_loop()
        
        async def process_single_face(image):
            return await loop.run_in_executor(
                None, 
                self._extract_face_encoding, 
                image
            )
        
        # Process all faces
        results = await asyncio.gather(*[process_single_face(img) for img in images])
        
        # Return results to callbacks
        for request, result in zip(batch, results):
            if request.callback:
                await request.callback(result)
    
    def _extract_face_encoding(self, image) -> List[np.ndarray]:
        """Extract face encoding (CPU-bound operation)"""
        try:
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Detect faces
            face_locations = face_recognition.face_locations(
                image, number_of_times_to_upsample=1, model="hog"
            )
            
            # Extract encodings
            if face_locations:
                encodings = face_recognition.face_encodings(image, face_locations)
                return encodings
            
            return []
        except Exception as e:
            logger.error(f"Face encoding error: {e}")
            return []
    
    async def _process_classification_batch(self, batch: List[BatchRequest]):
        """Process image classification batch"""
        # Implementation for image classification batching
        pass
    
    async def _process_feature_batch(self, batch: List[BatchRequest]):
        """Process feature extraction batch"""
        # Implementation for feature extraction batching
        pass
    
    async def _process_hash_batch(self, batch: List[BatchRequest]):
        """Process hash computation batch"""
        images = [req.data for req in batch]
        
        # Compute hashes in parallel
        loop = asyncio.get_event_loop()
        
        async def compute_hashes(image):
            return await loop.run_in_executor(
                None,
                self._compute_all_hashes,
                image
            )
        
        results = await asyncio.gather(*[compute_hashes(img) for img in images])
        
        # Return results
        for request, result in zip(batch, results):
            if request.callback:
                await request.callback(result)
    
    def _compute_all_hashes(self, image) -> Dict[str, str]:
        """Compute all perceptual hashes"""
        try:
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            return {
                'average': str(imagehash.average_hash(image)),
                'perceptual': str(imagehash.phash(image)),
                'difference': str(imagehash.dhash(image)),
                'wavelet': str(imagehash.whash(image))
            }
        except Exception as e:
            logger.error(f"Hash computation error: {e}")
            return {}
    
    def _optimize_batch_size(self, model_type: ModelType, batch_size: int, elapsed_ms: float):
        """Optimize batch size based on performance"""
        metrics = self.batch_metrics[model_type]
        
        # Keep only recent metrics
        if len(metrics) > 20:
            metrics = metrics[-20:]
            self.batch_metrics[model_type] = metrics
        
        if len(metrics) >= 5:
            avg_time = sum(metrics) / len(metrics)
            current_optimal = self.optimal_batch_sizes[model_type]
            
            # If performance is degrading, reduce batch size
            if elapsed_ms > avg_time * 1.2 and current_optimal > 1:
                self.optimal_batch_sizes[model_type] = max(1, current_optimal - 1)
                logger.info(f"Reduced optimal batch size for {model_type}: {current_optimal - 1}")
            
            # If performance is good, try increasing batch size
            elif elapsed_ms < avg_time * 0.8 and current_optimal < self.max_batch_size:
                self.optimal_batch_sizes[model_type] = min(self.max_batch_size, current_optimal + 1)
                logger.info(f"Increased optimal batch size for {model_type}: {current_optimal + 1}")
    
    async def submit_request(self, request: BatchRequest) -> Any:
        """Submit request for batch processing"""
        # Create future for result
        future = asyncio.Future()
        
        # Set callback to resolve future
        async def callback(result, error=None):
            if error:
                future.set_exception(error)
            else:
                future.set_result(result)
        
        request.callback = callback
        
        # Add to queue
        await self.queues[request.model_type].put(request)
        
        # Wait for result with timeout
        try:
            return await asyncio.wait_for(future, timeout=request.timeout_ms / 1000)
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for {request.model_type}")
            raise


class AIPerformanceOptimizer:
    """
    Comprehensive AI performance optimization system
    
    Features:
    - GPU acceleration with mixed precision
    - Dynamic model quantization
    - Intelligent batch processing
    - Memory optimization
    - Cache-aware inference
    - Real-time performance monitoring
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.BALANCED):
        self.optimization_level = optimization_level
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Model pools
        self.model_pools: Dict[str, OptimizedModelPool] = {}
        
        # Batch processor
        self.batch_processor = IntelligentBatchProcessor(
            max_batch_size=32 if optimization_level == OptimizationLevel.SPEED else 16,
            max_wait_ms=30 if optimization_level == OptimizationLevel.SPEED else 50
        )
        
        # Performance metrics
        self.metrics: Dict[str, ModelMetrics] = defaultdict(ModelMetrics)
        
        # Memory management
        self.memory_threshold_mb = 512  # Trigger cleanup at 512MB
        self.last_cleanup = time.time()
        
        # Cache integration
        self.cache_enabled = True
        self.cache_hit_threshold = 0.7  # 70% cache hit rate target
        
        logger.info(f"AI Performance Optimizer initialized with {optimization_level} level on {self.device}")
        
        # Initialize model pools
        self._initialize_model_pools()
    
    def _initialize_model_pools(self):
        """Initialize optimized model pools"""
        # ResNet pool for feature extraction
        self.model_pools['resnet50'] = OptimizedModelPool(
            model_factory=lambda: models.resnet50(pretrained=True),
            initial_size=2,
            max_size=4
        )
        
        # MobileNet pool for fast inference
        self.model_pools['mobilenet'] = OptimizedModelPool(
            model_factory=lambda: models.mobilenet_v3_small(pretrained=True),
            initial_size=3,
            max_size=6
        )
    
    async def optimize_face_recognition(
        self,
        image: Union[Image.Image, np.ndarray],
        profile_encodings: List[np.ndarray],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Optimized face recognition with caching and batching"""
        start_time = time.time()
        
        try:
            # Create batch request
            request = BatchRequest(
                id=f"face_{int(time.time() * 1000000)}",
                model_type=ModelType.FACE_RECOGNITION,
                data=image,
                timeout_ms=1500
            )
            
            # Submit for batch processing
            face_encodings = await self.batch_processor.submit_request(request)
            
            # Match against profile encodings
            matches = []
            if face_encodings and profile_encodings:
                for face_encoding in face_encodings:
                    for i, known_encoding in enumerate(profile_encodings):
                        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                        
                        if distance < 0.6:  # Threshold for match
                            matches.append({
                                'type': 'face_match',
                                'confidence': 1.0 - distance,
                                'distance': float(distance),
                                'profile_index': i
                            })
            
            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_metrics('face_recognition', elapsed_ms, 1, use_cache)
            
            return matches
            
        except Exception as e:
            logger.error(f"Face recognition optimization error: {e}")
            self.metrics['face_recognition'].errors += 1
            return []
    
    async def optimize_image_features(
        self,
        image: Union[Image.Image, np.ndarray],
        model_name: str = 'resnet50',
        use_cache: bool = True
    ) -> Optional[np.ndarray]:
        """Optimized image feature extraction"""
        start_time = time.time()
        
        try:
            # Get model from pool
            pool = self.model_pools.get(model_name)
            if not pool:
                raise ValueError(f"Model pool {model_name} not found")
            
            model, lock, model_idx = pool.get_optimal_model()
            
            try:
                # Prepare input
                if isinstance(image, np.ndarray):
                    image = Image.fromarray(image)
                
                # Transform
                transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
                
                input_tensor = transform(image).unsqueeze(0).to(self.device)
                
                if torch.cuda.is_available():
                    input_tensor = input_tensor.half()
                
                # Inference
                with torch.no_grad():
                    if torch.cuda.is_available():
                        with autocast():
                            features = model(input_tensor)
                    else:
                        features = model(input_tensor)
                
                # Convert to numpy
                features_np = features.cpu().numpy()
                
                # Update metrics
                elapsed_ms = (time.time() - start_time) * 1000
                self._update_metrics(f'features_{model_name}', elapsed_ms, 1, use_cache)
                
                return features_np
                
            finally:
                lock.release()
                
        except Exception as e:
            logger.error(f"Image feature optimization error: {e}")
            self.metrics[f'features_{model_name}'].errors += 1
            return None
    
    async def optimize_hash_computation(
        self,
        image: Union[Image.Image, np.ndarray],
        hash_types: List[str] = None
    ) -> Dict[str, str]:
        """Optimized perceptual hash computation"""
        if hash_types is None:
            hash_types = ['average', 'perceptual', 'difference', 'wavelet']
        
        start_time = time.time()
        
        try:
            # Create batch request
            request = BatchRequest(
                id=f"hash_{int(time.time() * 1000000)}",
                model_type=ModelType.HASH_COMPUTATION,
                data=image,
                timeout_ms=500
            )
            
            # Submit for batch processing
            hashes = await self.batch_processor.submit_request(request)
            
            # Filter requested hash types
            if hash_types:
                hashes = {k: v for k, v in hashes.items() if k in hash_types}
            
            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_metrics('hash_computation', elapsed_ms, 1, False)
            
            return hashes
            
        except Exception as e:
            logger.error(f"Hash computation optimization error: {e}")
            self.metrics['hash_computation'].errors += 1
            return {}
    
    def _update_metrics(self, operation: str, elapsed_ms: float, batch_size: int, cache_used: bool):
        """Update performance metrics"""
        metrics = self.metrics[operation]
        
        metrics.total_inferences += batch_size
        metrics.total_time_ms += elapsed_ms
        metrics.avg_time_ms = metrics.total_time_ms / metrics.total_inferences
        metrics.min_time_ms = min(metrics.min_time_ms, elapsed_ms)
        metrics.max_time_ms = max(metrics.max_time_ms, elapsed_ms)
        metrics.batch_sizes.append(batch_size)
        
        if cache_used:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1
        
        # Update memory usage
        if torch.cuda.is_available():
            metrics.gpu_memory_mb = torch.cuda.memory_allocated() / 1024**2
        
        metrics.memory_usage_mb = psutil.Process().memory_info().rss / 1024**2
        
        # Report to performance monitor
        performance_monitor.track_ai_inference(
            model_name=operation,
            inference_time_ms=elapsed_ms,
            batch_size=batch_size,
            cache_hit=cache_used,
            memory_usage_mb=metrics.memory_usage_mb
        )
    
    async def memory_cleanup(self, force: bool = False):
        """Intelligent memory cleanup"""
        current_time = time.time()
        
        # Check if cleanup is needed
        if not force and current_time - self.last_cleanup < 60:  # Minimum 1 minute between cleanups
            return
        
        # Check memory usage
        if torch.cuda.is_available():
            gpu_memory_mb = torch.cuda.memory_allocated() / 1024**2
            if gpu_memory_mb > self.memory_threshold_mb or force:
                torch.cuda.empty_cache()
                logger.info(f"GPU memory cleanup: {gpu_memory_mb:.1f}MB -> {torch.cuda.memory_allocated() / 1024**2:.1f}MB")
        
        # CPU memory cleanup
        gc.collect()
        
        self.last_cleanup = current_time
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            'optimization_level': self.optimization_level,
            'device': str(self.device),
            'total_operations': sum(m.total_inferences for m in self.metrics.values()),
            'operations': {}
        }
        
        for operation, metrics in self.metrics.items():
            cache_hit_rate = 0.0
            if metrics.cache_hits + metrics.cache_misses > 0:
                cache_hit_rate = metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)
            
            report['operations'][operation] = {
                'total_inferences': metrics.total_inferences,
                'avg_time_ms': metrics.avg_time_ms,
                'min_time_ms': metrics.min_time_ms if metrics.min_time_ms != float('inf') else 0,
                'max_time_ms': metrics.max_time_ms,
                'cache_hit_rate': cache_hit_rate,
                'memory_usage_mb': metrics.memory_usage_mb,
                'gpu_memory_mb': metrics.gpu_memory_mb,
                'errors': metrics.errors,
                'avg_batch_size': sum(metrics.batch_sizes) / len(metrics.batch_sizes) if metrics.batch_sizes else 0
            }
        
        # Add model pool stats
        report['model_pools'] = {
            name: pool.get_stats() for name, pool in self.model_pools.items()
        }
        
        # Add batch processor stats
        report['batch_processing'] = {
            'optimal_batch_sizes': self.batch_processor.optimal_batch_sizes,
            'queue_sizes': {
                str(model_type): queue.qsize() 
                for model_type, queue in self.batch_processor.queues.items()
            }
        }
        
        return report
    
    async def optimize_system_for_load(self, expected_concurrent_users: int):
        """Optimize system for expected load"""
        logger.info(f"Optimizing system for {expected_concurrent_users} concurrent users")
        
        # Scale model pools based on load
        for pool_name, pool in self.model_pools.items():
            target_size = min(pool.max_size, max(2, expected_concurrent_users // 100))
            
            while len(pool.models) < target_size:
                pool._scale_up()
        
        # Adjust batch sizes for higher throughput
        if expected_concurrent_users > 500:
            for model_type in ModelType:
                current = self.batch_processor.optimal_batch_sizes[model_type]
                self.batch_processor.optimal_batch_sizes[model_type] = min(32, current * 2)
        
        # Pre-warm caches if possible
        await self.memory_cleanup(force=True)
        
        logger.info("System optimization for load completed")


# Global optimizer instance
ai_optimizer = AIPerformanceOptimizer(OptimizationLevel.BALANCED)