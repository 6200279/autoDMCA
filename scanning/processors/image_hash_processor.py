"""
Perceptual image hashing processor for detecting similar/duplicate images.
"""

import asyncio
import hashlib
import io
import time
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from pathlib import Path
import tempfile

import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
import imagehash
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import aiohttp
import aiofiles
import structlog

from ..config import ScannerSettings


logger = structlog.get_logger(__name__)


@dataclass
class ImageHash:
    """Represents a perceptual hash of an image."""
    
    hash_value: str
    hash_type: str  # ahash, phash, dhash, whash, etc.
    image_url: Optional[str] = None
    person_id: Optional[str] = None
    image_size: Optional[Tuple[int, int]] = None
    file_size: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if isinstance(self.hash_value, imagehash.ImageHash):
            self.hash_value = str(self.hash_value)
    
    @property
    def hash_int(self) -> int:
        """Convert hash to integer for distance calculations."""
        try:
            return int(self.hash_value, 16)
        except ValueError:
            return 0
    
    def distance(self, other: 'ImageHash') -> int:
        """Calculate Hamming distance between hashes."""
        if self.hash_type != other.hash_type:
            return float('inf')
        
        try:
            hash1 = imagehash.hex_to_hash(self.hash_value)
            hash2 = imagehash.hex_to_hash(other.hash_value)
            return abs(hash1 - hash2)
        except Exception:
            return float('inf')
    
    def similarity(self, other: 'ImageHash') -> float:
        """Calculate similarity score (0-1, higher is more similar)."""
        distance = self.distance(other)
        if distance == float('inf'):
            return 0.0
        
        # Convert distance to similarity (for 64-bit hashes)
        max_distance = 64  # Assuming 64-bit hashes
        return max(0.0, 1.0 - (distance / max_distance))


@dataclass
class ImageMatch:
    """Represents a match between two images."""
    
    reference_hash: ImageHash
    candidate_hash: ImageHash
    similarity_score: float
    distance: int
    match_type: str = "similar"  # exact, similar, near_duplicate
    
    @property
    def is_exact_match(self) -> bool:
        """Check if this is an exact match."""
        return self.distance == 0
    
    @property
    def is_similar(self) -> bool:
        """Check if this is a similar match."""
        return self.similarity_score >= 0.85
    
    @property
    def is_near_duplicate(self) -> bool:
        """Check if this is a near duplicate."""
        return self.similarity_score >= 0.95


@dataclass
class ProcessingResult:
    """Result from processing an image for hashing."""
    
    image_url: str
    hashes: Dict[str, ImageHash] = field(default_factory=dict)
    processing_time: float = 0.0
    error: Optional[str] = None
    image_info: Dict = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return not self.error and bool(self.hashes)


class ImageHashProcessor:
    """Advanced image hashing processor for duplicate detection."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.hash_database: Dict[str, List[ImageHash]] = {}  # person_id -> hashes
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        
        # Hash algorithms to use
        self.hash_algorithms = {
            'ahash': imagehash.average_hash,
            'phash': imagehash.phash,
            'dhash': imagehash.dhash,
            'whash': imagehash.whash
        }
        
    async def initialize(self):
        """Initialize the processor."""
        await self._setup_http_session()
        logger.info("Image hash processor initialized")
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def _setup_http_session(self):
        """Setup HTTP session for downloading images."""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'AutoDMCA Image Hash Processor/1.0'
            }
        )
    
    async def add_reference_images(
        self,
        person_id: str,
        image_sources: List[Union[str, bytes, np.ndarray]],
        replace_existing: bool = False
    ) -> int:
        """Add reference images for a person to the hash database."""
        async with self._lock:
            if replace_existing or person_id not in self.hash_database:
                self.hash_database[person_id] = []
            
            hashes_added = 0
            
            for image_source in image_sources:
                try:
                    result = await self.process_image(image_source)
                    
                    if result.is_success:
                        for hash_type, image_hash in result.hashes.items():
                            image_hash.person_id = person_id
                            self.hash_database[person_id].append(image_hash)
                            hashes_added += 1
                            
                except Exception as e:
                    logger.error(f"Failed to process reference image for {person_id}", error=str(e))
                    continue
            
            logger.info(
                f"Added reference images for {person_id}",
                hashes_added=hashes_added,
                total_hashes=len(self.hash_database[person_id])
            )
            
            return hashes_added
    
    async def process_image(
        self,
        image_source: Union[str, bytes, np.ndarray, Image.Image]
    ) -> ProcessingResult:
        """Process an image and generate perceptual hashes."""
        start_time = time.time()
        image_url = image_source if isinstance(image_source, str) else "unknown"
        
        try:
            # Load image
            pil_image = await self._load_image(image_source)
            if pil_image is None:
                return ProcessingResult(
                    image_url=image_url,
                    error="Failed to load image"
                )
            
            # Get image info
            image_info = {
                'size': pil_image.size,
                'mode': pil_image.mode,
                'format': getattr(pil_image, 'format', None)
            }
            
            # Generate multiple hash types
            hashes = {}
            
            # Standard hashes
            for hash_name, hash_func in self.hash_algorithms.items():
                try:
                    hash_value = hash_func(pil_image, hash_size=self.settings.hash_size)
                    
                    image_hash = ImageHash(
                        hash_value=str(hash_value),
                        hash_type=hash_name,
                        image_url=image_url,
                        image_size=pil_image.size
                    )
                    
                    hashes[hash_name] = image_hash
                    
                except Exception as e:
                    logger.debug(f"Failed to generate {hash_name} hash", error=str(e))
            
            # Generate color histogram hash
            try:
                color_hash = await self._generate_color_hash(pil_image)
                if color_hash:
                    hashes['color'] = color_hash
            except Exception as e:
                logger.debug("Failed to generate color hash", error=str(e))
            
            # Generate wavelet hash if available
            try:
                wavelet_hash = await self._generate_wavelet_hash(pil_image)
                if wavelet_hash:
                    hashes['wavelet'] = wavelet_hash
            except Exception as e:
                logger.debug("Failed to generate wavelet hash", error=str(e))
            
            processing_time = time.time() - start_time
            
            logger.debug(
                "Image hashing completed",
                image_url=image_url,
                hash_types=list(hashes.keys()),
                processing_time=processing_time
            )
            
            return ProcessingResult(
                image_url=image_url,
                hashes=hashes,
                processing_time=processing_time,
                image_info=image_info
            )
            
        except Exception as e:
            logger.error("Image hashing failed", image_url=image_url, error=str(e))
            return ProcessingResult(
                image_url=image_url,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _load_image(self, image_source: Union[str, bytes, np.ndarray, Image.Image]) -> Optional[Image.Image]:
        """Load image from various sources."""
        try:
            if isinstance(image_source, Image.Image):
                return image_source.convert('RGB')
            
            elif isinstance(image_source, np.ndarray):
                # Convert numpy array to PIL
                if len(image_source.shape) == 3:
                    # Assume RGB
                    return Image.fromarray(image_source).convert('RGB')
                else:
                    # Grayscale
                    return Image.fromarray(image_source).convert('RGB')
            
            elif isinstance(image_source, bytes):
                # Load from bytes
                return Image.open(io.BytesIO(image_source)).convert('RGB')
            
            elif isinstance(image_source, str):
                if image_source.startswith(('http://', 'https://')):
                    # Download from URL
                    return await self._download_image(image_source)
                else:
                    # Load from file
                    return Image.open(image_source).convert('RGB')
            
            return None
            
        except Exception as e:
            logger.error("Failed to load image", source=str(image_source)[:100], error=str(e))
            return None
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    return None
                
                image_bytes = await response.read()
                return Image.open(io.BytesIO(image_bytes)).convert('RGB')
                
        except Exception as e:
            logger.error("Failed to download image", url=url, error=str(e))
            return None
    
    async def _generate_color_hash(self, image: Image.Image) -> Optional[ImageHash]:
        """Generate a color histogram-based hash."""
        try:
            # Convert to smaller size for efficiency
            small_image = image.resize((32, 32), Image.LANCZOS)
            
            # Calculate color histogram
            hist_r = small_image.getchannel(0).histogram()
            hist_g = small_image.getchannel(1).histogram()
            hist_b = small_image.getchannel(2).histogram()
            
            # Combine histograms
            combined_hist = hist_r + hist_g + hist_b
            
            # Create hash from histogram
            hist_array = np.array(combined_hist)
            normalized = hist_array / np.sum(hist_array)
            
            # Quantize to create hash
            quantized = (normalized * 255).astype(np.uint8)
            hash_bytes = quantized.tobytes()
            hash_value = hashlib.md5(hash_bytes).hexdigest()[:16]
            
            return ImageHash(
                hash_value=hash_value,
                hash_type='color',
                metadata={'histogram_size': len(combined_hist)}
            )
            
        except Exception as e:
            logger.debug("Color hash generation failed", error=str(e))
            return None
    
    async def _generate_wavelet_hash(self, image: Image.Image) -> Optional[ImageHash]:
        """Generate a wavelet-based hash."""
        try:
            # Convert to grayscale and resize
            gray_image = image.convert('L').resize((64, 64), Image.LANCZOS)
            img_array = np.array(gray_image, dtype=np.float32)
            
            # Simple wavelet-like transform (using DCT as approximation)
            from scipy.fft import dct
            dct_coeffs = dct(dct(img_array.T, norm='ortho').T, norm='ortho')
            
            # Take low-frequency components
            low_freq = dct_coeffs[:8, :8].flatten()
            
            # Create binary hash
            median_val = np.median(low_freq)
            binary_hash = (low_freq > median_val).astype(int)
            
            # Convert to hex string
            hash_int = 0
            for i, bit in enumerate(binary_hash):
                hash_int |= bit << i
            
            hash_value = f"{hash_int:016x}"
            
            return ImageHash(
                hash_value=hash_value,
                hash_type='wavelet'
            )
            
        except Exception as e:
            logger.debug("Wavelet hash generation failed", error=str(e))
            return None
    
    async def find_matches(
        self,
        candidate_image: Union[str, bytes, np.ndarray, Image.Image],
        person_ids: Optional[List[str]] = None,
        similarity_threshold: float = None
    ) -> List[ImageMatch]:
        """Find matching images in the database."""
        if similarity_threshold is None:
            similarity_threshold = self.settings.similarity_threshold
        
        # Process candidate image
        result = await self.process_image(candidate_image)
        if not result.is_success:
            return []
        
        matches = []
        target_persons = person_ids or list(self.hash_database.keys())
        
        async with self._lock:
            for person_id in target_persons:
                if person_id not in self.hash_database:
                    continue
                
                person_hashes = self.hash_database[person_id]
                
                # Compare each hash type
                for hash_type, candidate_hash in result.hashes.items():
                    for reference_hash in person_hashes:
                        if reference_hash.hash_type != hash_type:
                            continue
                        
                        similarity = candidate_hash.similarity(reference_hash)
                        distance = candidate_hash.distance(reference_hash)
                        
                        if similarity >= similarity_threshold:
                            match_type = "exact" if distance == 0 else "similar"
                            if similarity >= 0.95:
                                match_type = "near_duplicate"
                            
                            match = ImageMatch(
                                reference_hash=reference_hash,
                                candidate_hash=candidate_hash,
                                similarity_score=similarity,
                                distance=distance,
                                match_type=match_type
                            )
                            
                            matches.append(match)
        
        # Sort by similarity score (best matches first)
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Remove duplicate matches for same person/hash_type
        unique_matches = []
        seen = set()
        
        for match in matches:
            key = (match.reference_hash.person_id, match.candidate_hash.hash_type)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        logger.debug(
            "Image matching completed",
            candidate_url=result.image_url,
            total_matches=len(matches),
            unique_matches=len(unique_matches),
            exact_matches=len([m for m in unique_matches if m.is_exact_match])
        )
        
        return unique_matches
    
    async def bulk_process_images(
        self,
        image_sources: List[Union[str, bytes, np.ndarray]],
        max_concurrent: int = 5
    ) -> Dict[str, ProcessingResult]:
        """Process multiple images concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(source) -> Tuple[str, ProcessingResult]:
            async with semaphore:
                result = await self.process_image(source)
                key = source if isinstance(source, str) else f"image_{id(source)}"
                return key, result
        
        tasks = [process_single(source) for source in image_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = {}
        for result in results:
            if isinstance(result, tuple):
                key, processing_result = result
                processed_results[key] = processing_result
        
        return processed_results
    
    async def find_duplicates_in_set(
        self,
        image_sources: List[Union[str, bytes, np.ndarray]],
        similarity_threshold: float = 0.9
    ) -> List[List[Tuple[str, ImageHash]]]:
        """Find duplicate images within a set of images."""
        # Process all images
        results = await self.bulk_process_images(image_sources)
        
        # Extract hashes
        all_hashes = []
        for source, result in results.items():
            if result.is_success:
                for hash_type, image_hash in result.hashes.items():
                    all_hashes.append((source, image_hash))
        
        # Group by hash type and find clusters
        duplicate_groups = []
        
        for hash_type in ['phash', 'ahash', 'dhash']:  # Focus on main perceptual hashes
            type_hashes = [(src, h) for src, h in all_hashes if h.hash_type == hash_type]
            
            if len(type_hashes) < 2:
                continue
            
            # Calculate distance matrix
            n = len(type_hashes)
            distance_matrix = np.zeros((n, n))
            
            for i in range(n):
                for j in range(i + 1, n):
                    distance = type_hashes[i][1].distance(type_hashes[j][1])
                    similarity = 1.0 - (distance / 64.0)  # Assuming 64-bit hashes
                    distance_matrix[i][j] = distance_matrix[j][i] = 1.0 - similarity
            
            # Use DBSCAN clustering to find groups
            clustering = DBSCAN(
                eps=1.0 - similarity_threshold,
                min_samples=2,
                metric='precomputed'
            ).fit(distance_matrix)
            
            # Group results by cluster
            clusters = {}
            for idx, label in enumerate(clustering.labels_):
                if label != -1:  # -1 means noise (no cluster)
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(type_hashes[idx])
            
            # Add non-trivial clusters to results
            for cluster_items in clusters.values():
                if len(cluster_items) > 1:
                    duplicate_groups.append(cluster_items)
        
        logger.info(
            "Duplicate detection completed",
            total_images=len(image_sources),
            duplicate_groups=len(duplicate_groups)
        )
        
        return duplicate_groups
    
    async def get_hash_statistics(self) -> Dict:
        """Get statistics about the hash database."""
        async with self._lock:
            stats = {
                'total_persons': len(self.hash_database),
                'total_hashes': sum(len(hashes) for hashes in self.hash_database.values()),
                'hash_types': {},
                'persons': {}
            }
            
            # Count by hash type
            for person_id, hashes in self.hash_database.items():
                stats['persons'][person_id] = len(hashes)
                
                for image_hash in hashes:
                    hash_type = image_hash.hash_type
                    if hash_type not in stats['hash_types']:
                        stats['hash_types'][hash_type] = 0
                    stats['hash_types'][hash_type] += 1
            
            return stats
    
    async def remove_person(self, person_id: str) -> bool:
        """Remove all hashes for a person."""
        async with self._lock:
            if person_id in self.hash_database:
                del self.hash_database[person_id]
                logger.info(f"Removed hashes for person: {person_id}")
                return True
            return False
    
    async def clear_database(self):
        """Clear all hashes from database."""
        async with self._lock:
            self.hash_database.clear()
            logger.info("Hash database cleared")