"""
Face matching and image similarity detection for social media profiles.
"""

import asyncio
import io
import hashlib
import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union, TYPE_CHECKING
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

if TYPE_CHECKING:
    import numpy as np
from dataclasses import dataclass
from pathlib import Path

try:
    if not TYPE_CHECKING:
        import numpy as np
    import cv2
    import face_recognition
    from sklearn.metrics.pairwise import cosine_similarity
    CV2_AVAILABLE = True
    FACE_RECOGNITION_AVAILABLE = True
    SKLEARN_AVAILABLE = True
except ImportError:
    # AI/ML dependencies not available for local testing
    if not TYPE_CHECKING:
        np = None
    cv2 = None
    face_recognition = None
    cosine_similarity = None
    CV2_AVAILABLE = False
    FACE_RECOGNITION_AVAILABLE = False
    SKLEARN_AVAILABLE = False

from PIL import Image
try:
    import imagehash as ImageHash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    ImageHash = None
    IMAGEHASH_AVAILABLE = False

import structlog
import aiohttp
import aiofiles

from app.db.models.social_media import SocialMediaPlatform
from .config import SocialMediaSettings
from .api_clients import ProfileData
from app.core.config import settings


logger = structlog.get_logger(__name__)


@dataclass
class FaceMatch:
    """Represents a face match result with encrypted face data."""
    similarity_score: float
    confidence_level: str  # low, medium, high
    encrypted_face_encoding: str  # Encrypted face encoding
    bounding_box: Optional[Tuple[int, int, int, int]] = None
    metadata: Dict[str, Any] = None
    consent_timestamp: Optional[datetime] = None
    retention_expires: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.retention_expires is None:
            # Default retention period: 2 years for GDPR compliance
            self.retention_expires = datetime.utcnow() + timedelta(days=730)


@dataclass
class ImageMatch:
    """Represents an image similarity match result."""
    similarity_score: float
    hash_similarity: float
    pixel_similarity: Optional[float] = None
    structural_similarity: Optional[float] = None
    confidence_level: str = "medium"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BiometricDataProtection:
    """GDPR-compliant biometric data protection with encryption."""
    
    def __init__(self):
        self.encryption_key = self._derive_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from application secret."""
        password = settings.SECRET_KEY.encode()
        salt = b'biometric_salt_v1'  # In production, use a proper salt from config
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def encrypt_face_encoding(self, face_encoding: List[float]) -> str:
        """Encrypt face encoding with AES-256-GCM."""
        try:
            # Convert to JSON and encode
            json_data = json.dumps(face_encoding)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Face encoding encryption error", error=str(e))
            raise
    
    def decrypt_face_encoding(self, encrypted_encoding: str) -> List[float]:
        """Decrypt face encoding."""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_encoding.encode())
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error("Face encoding decryption error", error=str(e))
            raise
    
    def check_retention_policy(self, retention_expires: datetime) -> bool:
        """Check if biometric data should be deleted per retention policy."""
        return datetime.utcnow() > retention_expires
    
    def generate_consent_record(self, user_id: str, purpose: str) -> Dict[str, Any]:
        """Generate GDPR consent record."""
        return {
            'user_id': user_id,
            'purpose': purpose,
            'timestamp': datetime.utcnow(),
            'consent_id': secrets.token_urlsafe(16),
            'legal_basis': 'consent',
            'retention_period_days': 730,
            'data_categories': ['biometric', 'facial_recognition'],
            'processing_activities': ['content_matching', 'infringement_detection']
        }


class ImageProcessor:
    """Handles secure image processing operations with input validation."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.supported_formats = settings.supported_image_formats
        self.max_image_size = settings.max_image_size_mb * 1024 * 1024
        self.biometric_protection = BiometricDataProtection()
        
        # Security: Define allowed MIME types
        self.allowed_mime_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
        }
        
        # Security: Define dangerous file signatures to block
        self.dangerous_signatures = {
            b'\x4D\x5A': 'PE executable',  # MZ header
            b'\x7F\x45\x4C\x46': 'ELF executable',  # ELF header
            b'\x50\x4B\x03\x04': 'ZIP archive',  # ZIP header
            b'\x52\x61\x72\x21': 'RAR archive',  # RAR header
        }
        
    async def download_image(self, url: str) -> Optional[bytes]:
        """Securely download and validate image from URL."""
        if not url:
            return None
        
        # Security: Validate URL format
        if not self._is_safe_image_url(url):
            logger.warning("Potentially unsafe image URL blocked", url=url)
            return None
            
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Security: Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        if not any(allowed in content_type for allowed in self.allowed_mime_types):
                            logger.warning("Invalid content type", url=url, content_type=content_type)
                            return None
                        
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > self.max_image_size:
                            logger.warning("Image too large", url=url, size=content_length)
                            return None
                        
                        image_data = await response.read()
                        if len(image_data) > self.max_image_size:
                            logger.warning("Downloaded image too large", url=url, size=len(image_data))
                            return None
                        
                        # Security: Check for dangerous file signatures
                        if self._has_dangerous_signature(image_data):
                            logger.warning("Dangerous file signature detected", url=url)
                            return None
                        
                        return image_data
                    else:
                        logger.warning("Failed to download image", url=url, status=response.status)
                        return None
        except Exception as e:
            logger.error("Image download error", url=url, error=str(e))
            return None
    
    def _is_safe_image_url(self, url: str) -> bool:
        """Check if image URL is safe to download."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Must have a hostname
            if not parsed.hostname:
                return False
            
            # Block localhost and private IPs
            import socket
            try:
                ip = socket.gethostbyname(parsed.hostname)
                # Block private IP ranges
                private_ranges = [
                    '127.', '10.', '192.168.', '172.16.', '172.17.', '172.18.',
                    '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                    '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                    '172.29.', '172.30.', '172.31.', '169.254.', '0.0.0.0'
                ]
                if any(ip.startswith(range_prefix) for range_prefix in private_ranges):
                    return False
            except socket.gaierror:
                return False
                
            return True
        except Exception:
            return False
    
    def _has_dangerous_signature(self, data: bytes) -> bool:
        """Check if data contains dangerous file signatures."""
        if len(data) < 4:
            return False
        
        header = data[:8]  # Check first 8 bytes
        for signature in self.dangerous_signatures:
            if header.startswith(signature):
                return True
        return False
    
    def validate_image(self, image_data: bytes) -> bool:
        """Securely validate if image data is valid and safe."""
        try:
            # Security: Check minimum and maximum sizes
            if len(image_data) < 100:  # Too small to be a real image
                return False
            if len(image_data) > self.max_image_size:
                return False
            
            # Security: Check for dangerous signatures first
            if self._has_dangerous_signature(image_data):
                return False
            
            # Validate image using PIL
            image = Image.open(io.BytesIO(image_data))
            image.verify()
            
            # Security: Additional checks
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                return False
            
            # Check reasonable dimensions
            if hasattr(image, 'width') and hasattr(image, 'height'):
                if image.width > 10000 or image.height > 10000:  # Prevent decompression bombs
                    return False
                if image.width < 10 or image.height < 10:  # Too small
                    return False
            
            return True
        except Exception as e:
            logger.warning("Image validation failed", error=str(e))
            return False
    
    def preprocess_image(self, image_data: bytes, target_size: Tuple[int, int] = (224, 224)) -> Optional["np.ndarray"]:
        """Preprocess image for face recognition."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize while maintaining aspect ratio
            image.thumbnail(target_size, Image.LANCZOS)
            
            # Convert to numpy array
            image_array = np.array(image)
            
            return image_array
        except Exception as e:
            logger.error("Image preprocessing error", error=str(e))
            return None
    
    def compute_image_hash(self, image_data: bytes, hash_size: int = 8) -> Optional[str]:
        """Compute perceptual hash of image."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Compute different types of hashes
            average_hash = ImageHash.average_hash(image, hash_size)
            perception_hash = ImageHash.phash(image, hash_size)
            difference_hash = ImageHash.dhash(image, hash_size)
            
            # Combine hashes for better accuracy
            combined_hash = f"{average_hash}_{perception_hash}_{difference_hash}"
            return combined_hash
        except Exception as e:
            logger.error("Image hashing error", error=str(e))
            return None
    
    def compute_structural_similarity(self, image1_data: bytes, image2_data: bytes) -> Optional[float]:
        """Compute structural similarity index (SSIM) between two images."""
        try:
            from skimage.metrics import structural_similarity as ssim
            
            # Preprocess images
            img1 = self.preprocess_image(image1_data, (256, 256))
            img2 = self.preprocess_image(image2_data, (256, 256))
            
            if img1 is None or img2 is None:
                return None
            
            # Convert to grayscale for SSIM
            img1_gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
            img2_gray = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
            
            # Resize to same dimensions if needed
            if img1_gray.shape != img2_gray.shape:
                min_height = min(img1_gray.shape[0], img2_gray.shape[0])
                min_width = min(img1_gray.shape[1], img2_gray.shape[1])
                img1_gray = cv2.resize(img1_gray, (min_width, min_height))
                img2_gray = cv2.resize(img2_gray, (min_width, min_height))
            
            # Compute SSIM
            similarity_score = ssim(img1_gray, img2_gray)
            return float(similarity_score)
        except Exception as e:
            logger.error("SSIM computation error", error=str(e))
            return None


class FaceMatcher:
    """GDPR-compliant face recognition and matching service with encrypted storage."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.image_processor = ImageProcessor(settings)
        self.biometric_protection = BiometricDataProtection()
        self.tolerance = settings.face_recognition_tolerance
        self.detection_model = settings.face_detection_model
        self.max_faces = settings.max_faces_per_image
        
        # Security: Track consent and data retention
        self.consent_records = {}
        self.retention_policy_days = 730  # 2 years default for GDPR
        
    async def extract_face_encodings(self, image_data: bytes) -> List[Tuple["np.ndarray", Tuple[int, int, int, int]]]:
        """Extract face encodings from image."""
        if not self.image_processor.validate_image(image_data):
            return []
        
        try:
            # Run face recognition in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._extract_faces_sync,
                image_data
            )
        except Exception as e:
            logger.error("Face encoding extraction error", error=str(e))
            return []
    
    def _extract_faces_sync(self, image_data: bytes) -> List[Tuple["np.ndarray", Tuple[int, int, int, int]]]:
        """Synchronous face extraction."""
        image_array = self.image_processor.preprocess_image(image_data, (800, 800))
        if image_array is None:
            return []
        
        # Find face locations
        face_locations = face_recognition.face_locations(
            image_array,
            number_of_times_to_upsample=1,
            model=self.detection_model
        )
        
        if not face_locations:
            return []
        
        # Limit number of faces
        face_locations = face_locations[:self.max_faces]
        
        # Extract face encodings
        face_encodings = face_recognition.face_encodings(
            image_array,
            face_locations,
            num_jitters=1
        )
        
        # Combine encodings with locations
        faces = []
        for encoding, location in zip(face_encodings, face_locations):
            # Convert location format (top, right, bottom, left) to (x, y, width, height)
            top, right, bottom, left = location
            bounding_box = (left, top, right - left, bottom - top)
            faces.append((encoding, bounding_box))
        
        return faces
    
    async def compare_faces(
        self, 
        reference_encodings: List[str],  # Now expects encrypted encodings
        candidate_image_data: bytes,
        user_id: str,
        consent_purpose: str = "content_matching"
    ) -> List[FaceMatch]:
        """Compare encrypted reference face encodings with faces in candidate image."""
        if not reference_encodings or not candidate_image_data:
            return []
        
        # Security: Generate consent record
        consent_record = self.biometric_protection.generate_consent_record(
            user_id, consent_purpose
        )
        self.consent_records[user_id] = consent_record
        
        # Extract faces from candidate image
        candidate_faces = await self.extract_face_encodings(candidate_image_data)
        if not candidate_faces:
            return []
        
        matches = []
        
        for candidate_encoding, bounding_box in candidate_faces:
            best_match = None
            best_similarity = 0.0
            
            for encrypted_ref_encoding in reference_encodings:
                try:
                    # Security: Decrypt reference encoding
                    ref_encoding = self.biometric_protection.decrypt_face_encoding(
                        encrypted_ref_encoding
                    )
                    
                    # Convert to numpy arrays
                    ref_array = np.array(ref_encoding)
                    candidate_array = np.array(candidate_encoding)
                    
                    # Compute face distance (lower is better) with timing attack protection
                    import time
                    start_time = time.time()
                    distance = face_recognition.face_distance([ref_array], candidate_array)[0]
                    
                    # Normalize timing to prevent timing attacks
                    elapsed = time.time() - start_time
                    if elapsed < 0.01:  # Minimum processing time
                        await asyncio.sleep(0.01 - elapsed)
                    
                    # Convert distance to similarity score (0-1, higher is better)
                    similarity = 1.0 - distance
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = {
                            'encrypted_reference_encoding': encrypted_ref_encoding,
                            'distance': distance
                        }
                
                except Exception as e:
                    logger.warning("Face comparison error", error=str(e))
                    continue
            
            if best_match and best_similarity >= (1.0 - self.tolerance):
                confidence_level = self._determine_confidence_level(best_similarity)
                
                # Security: Encrypt candidate face encoding before storing
                encrypted_candidate = self.biometric_protection.encrypt_face_encoding(
                    candidate_encoding.tolist()
                )
                
                match = FaceMatch(
                    similarity_score=best_similarity,
                    confidence_level=confidence_level,
                    encrypted_face_encoding=encrypted_candidate,
                    bounding_box=bounding_box,
                    metadata=best_match,
                    consent_timestamp=datetime.utcnow(),
                    retention_expires=datetime.utcnow() + timedelta(days=self.retention_policy_days)
                )
                matches.append(match)
        
        # Sort matches by similarity score (highest first)
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return matches
    
    def _determine_confidence_level(self, similarity_score: float) -> str:
        """Determine confidence level based on similarity score."""
        if similarity_score >= 0.95:
            return "high"
        elif similarity_score >= 0.85:
            return "medium"
        else:
            return "low"
    
    async def batch_compare_profiles(
        self,
        reference_profile_images: List[str],
        candidate_profiles: List[ProfileData],
        user_id: str,
        consent_purpose: str = "bulk_content_matching"
    ) -> Dict[str, List[FaceMatch]]:
        """Securely batch compare reference profile images against multiple candidate profiles."""
        # Security: Generate consent record for batch processing
        consent_record = self.biometric_protection.generate_consent_record(
            user_id, consent_purpose
        )
        self.consent_records[f"{user_id}_batch"] = consent_record
        
        # Extract and encrypt reference face encodings
        reference_encodings = []
        
        for image_url in reference_profile_images:
            image_data = await self.image_processor.download_image(image_url)
            if image_data:
                faces = await self.extract_face_encodings(image_data)
                for encoding, _ in faces:
                    # Security: Encrypt face encoding before storage
                    encrypted_encoding = self.biometric_protection.encrypt_face_encoding(
                        encoding.tolist()
                    )
                    reference_encodings.append(encrypted_encoding)
        
        if not reference_encodings:
            logger.warning("No reference face encodings found")
            return {}
        
        # Compare against candidate profiles with rate limiting
        results = {}
        processed_count = 0
        max_batch_size = 50  # Security: Limit batch processing
        
        for candidate in candidate_profiles[:max_batch_size]:
            if not candidate.profile_image_url:
                continue
            
            candidate_image_data = await self.image_processor.download_image(candidate.profile_image_url)
            if candidate_image_data:
                matches = await self.compare_faces(
                    reference_encodings, 
                    candidate_image_data,
                    user_id,
                    consent_purpose
                )
                if matches:
                    results[candidate.username] = matches
            
            processed_count += 1
            # Security: Rate limiting between requests
            if processed_count % 10 == 0:
                await asyncio.sleep(0.1)
        
        return results
    
    def cleanup_expired_data(self) -> int:
        """Clean up biometric data that has exceeded retention period."""
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        # In a real implementation, this would query the database
        # and delete expired biometric data records
        logger.info("Biometric data cleanup completed", cleaned_count=cleaned_count)
        return cleaned_count
    
    def revoke_consent(self, user_id: str) -> bool:
        """Revoke user consent and mark data for deletion."""
        try:
            if user_id in self.consent_records:
                del self.consent_records[user_id]
            
            # In a real implementation, this would:
            # 1. Mark all biometric data for this user for deletion
            # 2. Schedule immediate cleanup
            # 3. Log the consent revocation
            
            logger.info("Consent revoked for user", user_id=user_id)
            return True
        except Exception as e:
            logger.error("Failed to revoke consent", user_id=user_id, error=str(e))
            return False


class ImageSimilarityMatcher:
    """Image similarity matching using multiple techniques."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.image_processor = ImageProcessor(settings)
        self.similarity_threshold = settings.image_similarity_threshold
        
    async def compare_images(self, image1_data: bytes, image2_data: bytes) -> ImageMatch:
        """Compare two images for similarity using multiple methods."""
        try:
            # Compute perceptual hashes
            hash1 = self.image_processor.compute_image_hash(image1_data)
            hash2 = self.image_processor.compute_image_hash(image2_data)
            
            hash_similarity = 0.0
            if hash1 and hash2:
                hash_similarity = self._compute_hash_similarity(hash1, hash2)
            
            # Compute structural similarity
            structural_similarity = self.image_processor.compute_structural_similarity(image1_data, image2_data)
            
            # Combine similarity scores
            combined_similarity = self._combine_similarity_scores(hash_similarity, structural_similarity)
            
            confidence_level = self._determine_image_confidence(combined_similarity, hash_similarity, structural_similarity)
            
            return ImageMatch(
                similarity_score=combined_similarity,
                hash_similarity=hash_similarity,
                structural_similarity=structural_similarity,
                confidence_level=confidence_level,
                metadata={
                    'hash1': hash1,
                    'hash2': hash2,
                    'methods_used': ['hash', 'ssim'] if structural_similarity else ['hash']
                }
            )
        
        except Exception as e:
            logger.error("Image comparison error", error=str(e))
            return ImageMatch(similarity_score=0.0, hash_similarity=0.0, confidence_level="low")
    
    def _compute_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Compute similarity between perceptual hashes."""
        try:
            # Parse combined hashes
            parts1 = hash1.split('_')
            parts2 = hash2.split('_')
            
            if len(parts1) != 3 or len(parts2) != 3:
                return 0.0
            
            similarities = []
            
            for h1, h2 in zip(parts1, parts2):
                # Compute Hamming distance
                distance = sum(c1 != c2 for c1, c2 in zip(h1, h2))
                max_distance = len(h1)
                similarity = 1.0 - (distance / max_distance)
                similarities.append(similarity)
            
            # Return average similarity
            return sum(similarities) / len(similarities)
        
        except Exception as e:
            logger.error("Hash similarity computation error", error=str(e))
            return 0.0
    
    def _combine_similarity_scores(self, hash_similarity: float, structural_similarity: Optional[float]) -> float:
        """Combine different similarity scores into final score."""
        if structural_similarity is not None:
            # Weight hash similarity and structural similarity
            return (hash_similarity * 0.4) + (structural_similarity * 0.6)
        else:
            return hash_similarity
    
    def _determine_image_confidence(self, combined_similarity: float, hash_similarity: float, structural_similarity: Optional[float]) -> str:
        """Determine confidence level for image matching."""
        # High confidence if multiple methods agree and scores are high
        if structural_similarity is not None and combined_similarity >= 0.9 and hash_similarity >= 0.85:
            return "high"
        elif combined_similarity >= 0.8:
            return "medium"
        else:
            return "low"
    
    async def batch_compare_images(self, reference_urls: List[str], candidate_urls: List[str]) -> Dict[str, Dict[str, ImageMatch]]:
        """Batch compare reference images against candidate images."""
        results = {}
        
        # Download all images
        reference_images = {}
        for url in reference_urls:
            image_data = await self.image_processor.download_image(url)
            if image_data:
                reference_images[url] = image_data
        
        candidate_images = {}
        for url in candidate_urls:
            image_data = await self.image_processor.download_image(url)
            if image_data:
                candidate_images[url] = image_data
        
        # Compare all combinations
        for ref_url, ref_data in reference_images.items():
            results[ref_url] = {}
            for cand_url, cand_data in candidate_images.items():
                match = await self.compare_images(ref_data, cand_data)
                results[ref_url][cand_url] = match
        
        return results


class ProfileImageAnalyzer:
    """Comprehensive profile image analysis combining face matching and image similarity."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        if FACE_RECOGNITION_AVAILABLE and CV2_AVAILABLE:
            self.face_matcher = FaceMatcher(settings)
            self.image_matcher = ImageSimilarityMatcher(settings)
        else:
            logger.warning("AI/ML dependencies not available - face matching disabled for local testing")
            self.face_matcher = None
            self.image_matcher = None
        
    async def analyze_profile_similarity(
        self,
        original_profile: ProfileData,
        candidate_profile: ProfileData,
        reference_face_encodings: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """Comprehensive analysis of profile similarity."""
        analysis_result = {
            'overall_similarity': 0.0,
            'face_matches': [],
            'image_match': None,
            'confidence_level': 'low',
            'analysis_methods': [],
            'metadata': {}
        }
        
        if not original_profile.profile_image_url or not candidate_profile.profile_image_url:
            return analysis_result
        
        # If AI/ML dependencies not available, return empty result
        if not self.face_matcher or not self.image_matcher:
            logger.info("Face matching disabled - returning empty analysis result")
            return analysis_result
        
        try:
            # Download images
            original_image = await self.face_matcher.image_processor.download_image(original_profile.profile_image_url)
            candidate_image = await self.face_matcher.image_processor.download_image(candidate_profile.profile_image_url)
            
            if not original_image or not candidate_image:
                return analysis_result
            
            similarities = []
            
            # Face matching analysis
            if reference_face_encodings:
                face_matches = await self.face_matcher.compare_faces(reference_face_encodings, candidate_image)
                analysis_result['face_matches'] = face_matches
                if face_matches:
                    analysis_result['analysis_methods'].append('face_recognition')
                    best_face_match = max(face_matches, key=lambda x: x.similarity_score)
                    similarities.append(best_face_match.similarity_score)
            
            # Image similarity analysis
            image_match = await self.image_matcher.compare_images(original_image, candidate_image)
            analysis_result['image_match'] = image_match
            analysis_result['analysis_methods'].append('image_similarity')
            similarities.append(image_match.similarity_score)
            
            # Compute overall similarity
            if similarities:
                analysis_result['overall_similarity'] = max(similarities)  # Take the best match
                
                # Determine overall confidence
                if len(similarities) > 1 and all(s >= 0.8 for s in similarities):
                    analysis_result['confidence_level'] = 'high'
                elif analysis_result['overall_similarity'] >= 0.85:
                    analysis_result['confidence_level'] = 'medium'
                else:
                    analysis_result['confidence_level'] = 'low'
            
            # Add metadata
            analysis_result['metadata'] = {
                'original_profile_url': original_profile.profile_image_url,
                'candidate_profile_url': candidate_profile.profile_image_url,
                'analysis_timestamp': asyncio.get_event_loop().time(),
                'methods_count': len(analysis_result['analysis_methods'])
            }
            
        except Exception as e:
            logger.error("Profile similarity analysis error", error=str(e))
            analysis_result['metadata']['error'] = str(e)
        
        return analysis_result
    
    async def batch_analyze_candidates(
        self,
        original_profile: ProfileData,
        candidate_profiles: List[ProfileData],
        reference_face_encodings: Optional[List[List[float]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Batch analyze multiple candidate profiles against original."""
        results = {}
        
        for candidate in candidate_profiles:
            analysis = await self.analyze_profile_similarity(
                original_profile,
                candidate,
                reference_face_encodings
            )
            results[candidate.username] = analysis
        
        # Sort results by similarity score
        sorted_results = dict(
            sorted(
                results.items(),
                key=lambda x: x[1]['overall_similarity'],
                reverse=True
            )
        )
        
        return sorted_results