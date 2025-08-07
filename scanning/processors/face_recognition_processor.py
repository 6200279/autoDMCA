"""
Face recognition processor using OpenCV and face_recognition library.
"""

import asyncio
import io
import os
import pickle
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from pathlib import Path
import tempfile

import cv2
import numpy as np
import face_recognition
import aiohttp
import aiofiles
from PIL import Image, ImageEnhance
import structlog

from ..config import ScannerSettings


logger = structlog.get_logger(__name__)


@dataclass
class FaceEncoding:
    """Represents a face encoding with metadata."""
    
    encoding: np.ndarray
    person_id: str
    image_url: Optional[str] = None
    confidence: float = 0.0
    bbox: Optional[Tuple[int, int, int, int]] = None  # (top, right, bottom, left)
    landmarks: Optional[Dict] = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    
    def __post_init__(self):
        """Ensure encoding is numpy array."""
        if not isinstance(self.encoding, np.ndarray):
            self.encoding = np.array(self.encoding)


@dataclass
class FaceMatch:
    """Represents a face match result."""
    
    person_id: str
    confidence: float  # Higher is better match
    distance: float    # Lower is better match
    bbox: Optional[Tuple[int, int, int, int]] = None
    image_url: Optional[str] = None
    reference_encoding: Optional[FaceEncoding] = None
    
    @property
    def is_match(self) -> bool:
        """Check if this is considered a positive match."""
        return self.distance < 0.6 and self.confidence > 0.4


@dataclass
class FaceProcessingResult:
    """Result from processing an image for faces."""
    
    image_url: str
    faces_found: int
    matches: List[FaceMatch] = field(default_factory=list)
    processing_time: float = 0.0
    error: Optional[str] = None
    
    @property
    def has_matches(self) -> bool:
        """Check if any positive matches were found."""
        return any(match.is_match for match in self.matches)
    
    @property
    def best_match(self) -> Optional[FaceMatch]:
        """Get the best face match if any."""
        positive_matches = [m for m in self.matches if m.is_match]
        if not positive_matches:
            return None
        return min(positive_matches, key=lambda x: x.distance)


class FaceRecognitionProcessor:
    """Advanced face recognition processor with OpenCV and face_recognition."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.known_encodings: Dict[str, List[FaceEncoding]] = {}
        self.face_cascade = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._models_loaded = False
        
    async def initialize(self):
        """Initialize the face recognition processor."""
        await self._load_opencv_models()
        await self._setup_http_session()
        self._models_loaded = True
        
        logger.info(
            "Face recognition processor initialized",
            detection_model=self.settings.face_detection_model,
            tolerance=self.settings.face_recognition_tolerance
        )
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def _load_opencv_models(self):
        """Load OpenCV cascade models."""
        try:
            # Load Haar cascade for face detection (fallback method)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                logger.warning("Failed to load OpenCV face cascade")
            else:
                logger.info("OpenCV face cascade loaded successfully")
                
        except Exception as e:
            logger.error("Failed to load OpenCV models", error=str(e))
    
    async def _setup_http_session(self):
        """Setup HTTP session for downloading images."""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'AutoDMCA Face Recognition/1.0'
            }
        )
    
    async def add_person(
        self,
        person_id: str,
        reference_images: List[Union[str, bytes, np.ndarray]],
        replace_existing: bool = False
    ) -> int:
        """Add a person with reference face images."""
        if not self._models_loaded:
            await self.initialize()
        
        async with self._lock:
            if replace_existing or person_id not in self.known_encodings:
                self.known_encodings[person_id] = []
            
            encodings_added = 0
            
            for image in reference_images:
                try:
                    face_encodings = await self._extract_face_encodings(image, person_id)
                    
                    for encoding in face_encodings:
                        self.known_encodings[person_id].append(encoding)
                        encodings_added += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process reference image for {person_id}", error=str(e))
                    continue
            
            logger.info(
                f"Added person to face recognition database",
                person_id=person_id,
                encodings_added=encodings_added,
                total_encodings=len(self.known_encodings[person_id])
            )
            
            return encodings_added
    
    async def remove_person(self, person_id: str) -> bool:
        """Remove a person from the recognition database."""
        async with self._lock:
            if person_id in self.known_encodings:
                del self.known_encodings[person_id]
                logger.info(f"Removed person from database: {person_id}")
                return True
            return False
    
    async def process_image(
        self,
        image_source: Union[str, bytes, np.ndarray],
        person_ids: Optional[List[str]] = None
    ) -> FaceProcessingResult:
        """Process an image and find face matches."""
        if not self._models_loaded:
            await self.initialize()
        
        start_time = asyncio.get_event_loop().time()
        image_url = image_source if isinstance(image_source, str) else "unknown"
        
        try:
            # Load image
            image_array = await self._load_image(image_source)
            if image_array is None:
                return FaceProcessingResult(
                    image_url=image_url,
                    faces_found=0,
                    error="Failed to load image"
                )
            
            # Detect faces
            face_locations = await self._detect_faces(image_array)
            
            if not face_locations:
                return FaceProcessingResult(
                    image_url=image_url,
                    faces_found=0,
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Extract face encodings
            face_encodings = face_recognition.face_encodings(
                image_array, 
                face_locations,
                model='large'  # Use large model for better accuracy
            )
            
            # Match faces against known encodings
            matches = []
            target_persons = person_ids or list(self.known_encodings.keys())
            
            for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
                best_matches = await self._find_best_matches(
                    face_encoding, 
                    target_persons, 
                    face_location,
                    image_url
                )
                matches.extend(best_matches)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = FaceProcessingResult(
                image_url=image_url,
                faces_found=len(face_locations),
                matches=matches,
                processing_time=processing_time
            )
            
            logger.debug(
                "Face processing completed",
                image_url=image_url,
                faces_found=len(face_locations),
                matches_found=len([m for m in matches if m.is_match]),
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Face processing failed", image_url=image_url, error=str(e))
            return FaceProcessingResult(
                image_url=image_url,
                faces_found=0,
                error=str(e),
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def _load_image(self, image_source: Union[str, bytes, np.ndarray]) -> Optional[np.ndarray]:
        """Load image from various sources."""
        try:
            if isinstance(image_source, np.ndarray):
                return image_source
            
            elif isinstance(image_source, bytes):
                # Convert bytes to numpy array
                nparr = np.frombuffer(image_source, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            elif isinstance(image_source, str):
                if image_source.startswith(('http://', 'https://')):
                    # Download from URL
                    return await self._download_and_load_image(image_source)
                else:
                    # Load from file path
                    image = cv2.imread(image_source)
                    if image is not None:
                        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            return None
            
        except Exception as e:
            logger.error("Failed to load image", source=str(image_source)[:100], error=str(e))
            return None
    
    async def _download_and_load_image(self, url: str) -> Optional[np.ndarray]:
        """Download and load image from URL."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download image: HTTP {response.status}", url=url)
                    return None
                
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"Invalid content type: {content_type}", url=url)
                    return None
                
                image_bytes = await response.read()
                
                # Convert to numpy array
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is not None:
                    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                return None
                
        except Exception as e:
            logger.error("Failed to download image", url=url, error=str(e))
            return None
    
    async def _detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in image using face_recognition library."""
        try:
            # Use face_recognition's HOG or CNN model based on settings
            model = self.settings.face_detection_model.lower()
            if model not in ['hog', 'cnn']:
                model = 'hog'  # Default to HOG for speed
            
            # Detect face locations
            face_locations = face_recognition.face_locations(
                image, 
                number_of_times_to_upsample=1,
                model=model
            )
            
            # Limit number of faces processed
            max_faces = self.settings.max_faces_per_image
            if len(face_locations) > max_faces:
                # Sort by face size (larger faces first)
                face_locations = sorted(
                    face_locations,
                    key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]),
                    reverse=True
                )[:max_faces]
            
            return face_locations
            
        except Exception as e:
            logger.error("Face detection failed", error=str(e))
            
            # Fallback to OpenCV if face_recognition fails
            return await self._detect_faces_opencv(image)
    
    async def _detect_faces_opencv(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Fallback face detection using OpenCV Haar cascades."""
        if not self.face_cascade:
            return []
        
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Convert from OpenCV format (x, y, w, h) to face_recognition format (top, right, bottom, left)
            face_locations = []
            for (x, y, w, h) in faces[:self.settings.max_faces_per_image]:
                top, right, bottom, left = y, x + w, y + h, x
                face_locations.append((top, right, bottom, left))
            
            logger.debug(f"OpenCV detected {len(face_locations)} faces")
            return face_locations
            
        except Exception as e:
            logger.error("OpenCV face detection failed", error=str(e))
            return []
    
    async def _extract_face_encodings(
        self, 
        image_source: Union[str, bytes, np.ndarray],
        person_id: str
    ) -> List[FaceEncoding]:
        """Extract face encodings from an image."""
        image_array = await self._load_image(image_source)
        if image_array is None:
            return []
        
        # Enhance image quality for better encoding
        image_array = await self._enhance_image(image_array)
        
        # Detect faces
        face_locations = await self._detect_faces(image_array)
        if not face_locations:
            return []
        
        # Extract encodings
        try:
            encodings = face_recognition.face_encodings(
                image_array,
                face_locations,
                model='large'  # Use large model for reference images
            )
            
            face_encodings = []
            image_url = image_source if isinstance(image_source, str) else None
            
            for encoding, location in zip(encodings, face_locations):
                face_enc = FaceEncoding(
                    encoding=encoding,
                    person_id=person_id,
                    image_url=image_url,
                    bbox=location,
                    confidence=1.0  # Reference images assumed high confidence
                )
                face_encodings.append(face_enc)
            
            return face_encodings
            
        except Exception as e:
            logger.error("Failed to extract face encodings", error=str(e))
            return []
    
    async def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        """Enhance image quality for better face recognition."""
        try:
            # Convert to PIL for enhancement
            pil_image = Image.fromarray(image)
            
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.1)
            
            # Convert back to numpy array
            return np.array(pil_image)
            
        except Exception:
            # Return original image if enhancement fails
            return image
    
    async def _find_best_matches(
        self,
        face_encoding: np.ndarray,
        person_ids: List[str],
        face_location: Tuple[int, int, int, int],
        image_url: str
    ) -> List[FaceMatch]:
        """Find best matches for a face encoding."""
        matches = []
        tolerance = self.settings.face_recognition_tolerance
        
        for person_id in person_ids:
            if person_id not in self.known_encodings:
                continue
            
            person_encodings = self.known_encodings[person_id]
            if not person_encodings:
                continue
            
            # Compare against all encodings for this person
            known_encodings = [enc.encoding for enc in person_encodings]
            
            # Calculate distances
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            if len(distances) == 0:
                continue
            
            # Find best match
            best_distance = float(np.min(distances))
            best_match_index = int(np.argmin(distances))
            
            # Calculate confidence score (inverse of distance)
            confidence = max(0.0, 1.0 - (best_distance / tolerance))
            
            match = FaceMatch(
                person_id=person_id,
                confidence=confidence,
                distance=best_distance,
                bbox=face_location,
                image_url=image_url,
                reference_encoding=person_encodings[best_match_index]
            )
            
            matches.append(match)
        
        # Sort by confidence (best matches first)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches
    
    async def bulk_process_images(
        self,
        image_urls: List[str],
        person_ids: Optional[List[str]] = None,
        max_concurrent: int = 5
    ) -> Dict[str, FaceProcessingResult]:
        """Process multiple images concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(url: str) -> Tuple[str, FaceProcessingResult]:
            async with semaphore:
                result = await self.process_image(url, person_ids)
                return url, result
        
        tasks = [process_single(url) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = {}
        for result in results:
            if isinstance(result, tuple):
                url, processing_result = result
                processed_results[url] = processing_result
            elif isinstance(result, Exception):
                logger.error("Bulk processing failed for image", error=str(result))
        
        logger.info(
            "Bulk face processing completed",
            total_images=len(image_urls),
            successful=len(processed_results),
            with_matches=len([r for r in processed_results.values() if r.has_matches])
        )
        
        return processed_results
    
    async def save_encodings(self, file_path: str) -> bool:
        """Save known face encodings to file."""
        try:
            async with self._lock:
                # Convert encodings to serializable format
                serializable_data = {}
                for person_id, encodings in self.known_encodings.items():
                    serializable_data[person_id] = []
                    for encoding in encodings:
                        serializable_data[person_id].append({
                            'encoding': encoding.encoding.tolist(),
                            'person_id': encoding.person_id,
                            'image_url': encoding.image_url,
                            'confidence': encoding.confidence,
                            'bbox': encoding.bbox,
                            'created_at': encoding.created_at
                        })
                
                # Save to file
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(pickle.dumps(serializable_data))
                
                logger.info(f"Face encodings saved to {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save encodings to {file_path}", error=str(e))
            return False
    
    async def load_encodings(self, file_path: str) -> bool:
        """Load known face encodings from file."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Encodings file not found: {file_path}")
                return False
            
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
                serializable_data = pickle.loads(data)
            
            async with self._lock:
                self.known_encodings.clear()
                
                for person_id, encoding_data in serializable_data.items():
                    self.known_encodings[person_id] = []
                    for data in encoding_data:
                        encoding = FaceEncoding(
                            encoding=np.array(data['encoding']),
                            person_id=data['person_id'],
                            image_url=data.get('image_url'),
                            confidence=data.get('confidence', 1.0),
                            bbox=data.get('bbox'),
                            created_at=data.get('created_at', 0.0)
                        )
                        self.known_encodings[person_id].append(encoding)
            
            total_encodings = sum(len(encs) for encs in self.known_encodings.values())
            logger.info(
                f"Face encodings loaded from {file_path}",
                persons=len(self.known_encodings),
                total_encodings=total_encodings
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load encodings from {file_path}", error=str(e))
            return False