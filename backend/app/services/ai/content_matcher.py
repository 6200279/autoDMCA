"""
AI-Powered Content Matching System
Implements facial recognition, image fingerprinting, and content matching
"""
import os

# Check if AI processing is disabled at module level
AI_DISABLED = os.getenv('DISABLE_AI_PROCESSING', 'false').lower() == 'true'

if AI_DISABLED:
    # Import lightweight version for local development
    from .content_matcher_local import ContentMatcher, ContentMatch, MatchType, content_matcher
else:
    # Full AI implementation
    import hashlib
    import io
    import os
    import tempfile
    import shutil
    import mimetypes
    import uuid
    import numpy as np
    from typing import List, Dict, Any, Optional, Tuple
    from datetime import datetime
    import logging
    from pathlib import Path
    from PIL import Image, ExifTags
    import imagehash
    import face_recognition
    import cv2
    from dataclasses import dataclass
    from enum import Enum
    import torch
    import torchvision.transforms as transforms
    from torchvision import models
    import pickle
    import base64
    import re

    from app.core.config import settings
    from app.core.security_config import InputValidator, security_monitor
    from app.db.session import get_db

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
        """Result of content matching with security metadata"""
        match_type: MatchType
        confidence: float  # 0.0 to 1.0
        source_url: str
        matched_content_id: Optional[str]
        metadata: Dict[str, Any]
        timestamp: datetime
        security_hash: Optional[str] = None  # Hash of original content for integrity
        processing_time: Optional[float] = None  # Time taken for analysis

    class SecureFileProcessor:
        """Secure file processing with sandboxing and validation."""
        
        def __init__(self):
            self.max_file_size = 50 * 1024 * 1024  # 50MB limit
            self.allowed_mime_types = {
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'video/mp4', 'video/avi', 'video/mov', 'video/webm'
            }
            self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.avi', '.mov', '.webm'}
            self.temp_dir = Path(tempfile.gettempdir()) / "secure_content_processing"
            self.temp_dir.mkdir(exist_ok=True)
            
            # Dangerous file signatures to block
            self.dangerous_signatures = {
                b'\x4D\x5A': 'PE executable',
                b'\x7F\x45\x4C\x46': 'ELF executable', 
                b'\x50\x4B\x03\x04': 'ZIP archive',
                b'\x52\x61\x72\x21': 'RAR archive',
                b'\x1f\x8b\x08': 'GZIP file',
                b'\x42\x5a\x68': 'BZIP2 file',
            }
        
        def validate_and_sanitize_file(self, content_data: bytes, filename: str = None) -> tuple[bool, str, Optional[Path]]:
            """Validate file content and create secure temporary file."""
            try:
                # Security: Check file size
                if len(content_data) > self.max_file_size:
                    return False, f"File too large: {len(content_data)} bytes (max {self.max_file_size})", None
                
                if len(content_data) < 100:
                    return False, "File too small to be valid media", None
                
                # Security: Check for dangerous file signatures
                if self._has_dangerous_signature(content_data):
                    return False, "File contains dangerous signature", None
                
                # Validate MIME type from content
                mime_type = self._detect_mime_type(content_data)
                if mime_type not in self.allowed_mime_types:
                    return False, f"Invalid MIME type: {mime_type}", None
                
                # Sanitize filename
                safe_filename = self._sanitize_filename(filename or f"content_{uuid.uuid4().hex}")
                
                # Create secure temporary file
                temp_file = self.temp_dir / f"{uuid.uuid4().hex}_{safe_filename}"
                
                # Write to temporary file with restricted permissions
                with open(temp_file, 'wb') as f:
                    f.write(content_data)
                
                # Set restrictive permissions (owner read/write only)
                temp_file.chmod(0o600)
                
                # Additional validation based on file type
                if mime_type.startswith('image/'):
                    if not self._validate_image_content(temp_file):
                        temp_file.unlink()
                        return False, "Invalid image content", None
                elif mime_type.startswith('video/'):
                    if not self._validate_video_content(temp_file):
                        temp_file.unlink()
                        return False, "Invalid video content", None
                
                return True, "File validated successfully", temp_file
                
            except Exception as e:
                logger.error("File validation error", error=str(e))
                return False, f"Validation error: {str(e)}", None
        
        def _has_dangerous_signature(self, data: bytes) -> bool:
            """Check for dangerous file signatures."""
            if len(data) < 4:
                return False
            
            header = data[:8]
            for signature in self.dangerous_signatures:
                if header.startswith(signature):
                    logger.warning("Dangerous file signature detected", signature=self.dangerous_signatures[signature])
                    return True
            return False
        
        def _detect_mime_type(self, data: bytes) -> str:
            """Detect MIME type from file content."""
            # Check common image signatures
            if data.startswith(b'\xFF\xD8\xFF'):
                return 'image/jpeg'
            elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'
            elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
                return 'image/gif'
            elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
                return 'image/webp'
            elif data.startswith(b'\x00\x00\x00\x18ftypmp4') or data.startswith(b'\x00\x00\x00\x20ftypiso'):
                return 'video/mp4'
            elif data.startswith(b'RIFF') and b'AVI ' in data[:12]:
                return 'video/avi'
            else:
                return 'application/octet-stream'
        
        def _sanitize_filename(self, filename: str) -> str:
            """Sanitize filename to prevent path traversal."""
            # Remove directory components
            filename = os.path.basename(filename)
            
            # Remove dangerous characters
            filename = re.sub(r'[^\w\-_\.]', '_', filename)
            
            # Limit length
            if len(filename) > 100:
                name, ext = os.path.splitext(filename)
                filename = name[:95] + ext
            
            return filename or "content"
        
        def _validate_image_content(self, file_path: Path) -> bool:
            """Validate image file content."""
            try:
                with Image.open(file_path) as img:
                    # Check image dimensions
                    if img.width > 10000 or img.height > 10000:
                        logger.warning("Image dimensions too large", width=img.width, height=img.height)
                        return False
                    
                    if img.width < 10 or img.height < 10:
                        logger.warning("Image dimensions too small", width=img.width, height=img.height)
                        return False
                    
                    # Verify image integrity
                    img.verify()
                    
                    # Remove EXIF data that might contain malicious content
                    self._strip_exif_data(file_path)
                    
                return True
            except Exception as e:
                logger.warning("Image validation failed", error=str(e))
                return False
        
        def _validate_video_content(self, file_path: Path) -> bool:
            """Validate video file content."""
            try:
                # Basic video validation using OpenCV
                cap = cv2.VideoCapture(str(file_path))
                if not cap.isOpened():
                    return False
                
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration = frame_count / fps if fps > 0 else 0
                
                cap.release()
                
                # Check reasonable limits
                if duration > 3600:  # 1 hour max
                    logger.warning("Video too long", duration=duration)
                    return False
                
                return True
            except Exception as e:
                logger.warning("Video validation failed", error=str(e))
                return False
        
        def _strip_exif_data(self, file_path: Path):
            """Remove EXIF data from image files."""
            try:
                with Image.open(file_path) as img:
                    # Create new image without EXIF data
                    data = list(img.getdata())
                    new_img = Image.new(img.mode, img.size)
                    new_img.putdata(data)
                    new_img.save(file_path)
            except Exception as e:
                logger.debug("EXIF stripping failed", error=str(e))
        
        def cleanup_temp_file(self, file_path: Path):
            """Securely cleanup temporary file."""
            try:
                if file_path.exists():
                    # Overwrite with random data before deletion
                    file_size = file_path.stat().st_size
                    with open(file_path, 'r+b') as f:
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # Delete the file
                    file_path.unlink()
                    logger.debug("Temporary file securely deleted", file_path=str(file_path))
            except Exception as e:
                logger.error("Failed to cleanup temp file", file_path=str(file_path), error=str(e))
    
    class ContentMatcher:
        """
        Secure AI-powered content matching engine with file processing safeguards
        PRD: "AI-based pattern recognition to identify likely infringements"
        """
        
        def __init__(self):
            # Initialize models
            self.face_model = None
            self.image_model = None
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            # Security: Initialize secure file processor
            self.file_processor = SecureFileProcessor()
            
            # Load pre-trained models
            self._load_models()
            
            # Cache for face encodings and image features
            self.face_encodings_cache = {}
            self.image_features_cache = {}
            
            # Security: Rate limiting and monitoring
            self.max_concurrent_operations = 10
            self.current_operations = 0
            
        def _load_models(self):
            """Load AI models for content matching"""
            try:
                # Load ResNet for image feature extraction
                self.image_model = models.resnet50(pretrained=True)
                self.image_model = self.image_model.to(self.device)
                self.image_model.eval()
                
                # Remove the final classification layer to get features
                self.image_model = torch.nn.Sequential(
                    *list(self.image_model.children())[:-1]
                )
                
                logger.info("AI models loaded successfully")
                
            except Exception as e:
                logger.error(f"Error loading AI models: {e}")
                
        async def analyze_content(
            self,
            content_url: str,
            content_data: bytes,
            profile_data: Dict[str, Any],
            user_id: str = "unknown",
            client_ip: str = "unknown"
        ) -> List[ContentMatch]:
            """
            Secure main entry point for content analysis with comprehensive validation
            PRD: "generating a face signature from images...comparing to the creator's face signature"
            """
            import time
            start_time = time.time()
            matches = []
            temp_file = None
            
            # Security: Rate limiting check
            if self.current_operations >= self.max_concurrent_operations:
                security_monitor.log_security_event(
                    event_type="rate_limit_exceeded",
                    severity="medium",
                    details={"operation": "content_analysis", "url": content_url},
                    user_id=user_id,
                    ip_address=client_ip
                )
                raise ValueError("Rate limit exceeded - too many concurrent operations")
            
            self.current_operations += 1
            
            try:
                # Security: Validate URL
                url_valid, url_message = InputValidator.validate_url(content_url)
                if not url_valid:
                    security_monitor.log_security_event(
                        event_type="invalid_url_submitted",
                        severity="medium",
                        details={"url": content_url, "reason": url_message},
                        user_id=user_id,
                        ip_address=client_ip
                    )
                    raise ValueError(f"Invalid URL: {url_message}")
                
                # Security: Validate and sanitize file content
                is_valid, validation_message, temp_file = self.file_processor.validate_and_sanitize_file(
                    content_data, filename=content_url.split('/')[-1]
                )
                
                if not is_valid:
                    security_monitor.log_security_event(
                        event_type="malicious_file_detected",
                        severity="high",
                        details={
                            "url": content_url,
                            "reason": validation_message,
                            "file_size": len(content_data)
                        },
                        user_id=user_id,
                        ip_address=client_ip
                    )
                    raise ValueError(f"File validation failed: {validation_message}")
                
                # Generate security hash for content integrity
                content_hash = hashlib.sha256(content_data).hexdigest()
                
                # Determine content type from validated content
                content_type = self._detect_content_type(content_data)
                
                # Process based on content type
                if content_type == 'image':
                    matches = await self._analyze_image(
                        content_url, temp_file, profile_data, user_id, client_ip
                    )
                elif content_type == 'video':
                    matches = await self._analyze_video(
                        content_url, temp_file, profile_data, user_id, client_ip
                    )
                elif content_type == 'text':
                    matches = await self._analyze_text(
                        content_url, content_data, profile_data, user_id, client_ip
                    )
                else:
                    security_monitor.log_security_event(
                        event_type="unsupported_content_type",
                        severity="low",
                        details={"url": content_url, "content_type": content_type},
                        user_id=user_id,
                        ip_address=client_ip
                    )
                    raise ValueError(f"Unsupported content type: {content_type}")
                
                # Add security metadata to matches
                processing_time = time.time() - start_time
                for match in matches:
                    match.security_hash = content_hash
                    match.processing_time = processing_time
                
                # Log successful analysis
                security_monitor.log_security_event(
                    event_type="content_analyzed",
                    severity="info",
                    details={
                        "url": content_url,
                        "matches_found": len(matches),
                        "processing_time": processing_time,
                        "content_type": content_type
                    },
                    user_id=user_id,
                    ip_address=client_ip
                )
                    
            except Exception as e:
                # Security: Log analysis errors
                security_monitor.log_security_event(
                    event_type="content_analysis_error",
                    severity="high",
                    details={"url": content_url, "error": str(e)[:200]},
                    user_id=user_id,
                    ip_address=client_ip
                )
                logger.error(f"Error analyzing content from {content_url}: {e}")
                raise
            
            finally:
                # Security: Always cleanup temporary files
                if temp_file:
                    self.file_processor.cleanup_temp_file(temp_file)
                
                self.current_operations -= 1
                
            return matches

        def _detect_content_type(self, data: bytes) -> str:
            """Detect content type from data"""
            if data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG'):
                return 'image'
            elif data.startswith(b'GIF'):
                return 'image'
            elif b'video' in data[:50].lower():
                return 'video'
            else:
                return 'text'

        async def _analyze_image(
            self,
            url: str,
            temp_file: Path,
            profile_data: Dict[str, Any],
            user_id: str,
            client_ip: str
        ) -> List[ContentMatch]:
            """Securely analyze image for face matches and similarity"""
            matches = []
            
            try:
                # Load image from secure temporary file
                with Image.open(temp_file) as image:
                    # Security: Validate image dimensions again
                    if image.width > 10000 or image.height > 10000:
                        raise ValueError("Image dimensions exceed safety limits")
                    
                    # Convert to bytes for face recognition (with size limits)
                    max_size = (2048, 2048)  # Resize large images
                    if image.width > max_size[0] or image.height > max_size[1]:
                        image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if needed
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Convert to bytes
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format='JPEG')
                    image_data = img_bytes.getvalue()
                
                # Face recognition analysis with timeout
                face_matches = await asyncio.wait_for(
                    self._detect_faces(image_data, profile_data, user_id, client_ip),
                    timeout=30.0  # 30 second timeout
                )
                matches.extend(face_matches)
                
                # Perceptual hash matching
                with Image.open(temp_file) as image:
                    hash_matches = await self._match_perceptual_hash(image, url)
                    matches.extend(hash_matches)
                    
                    # Image similarity analysis
                    similarity_matches = await self._match_image_similarity(image, url, profile_data)
                    matches.extend(similarity_matches)
                
            except asyncio.TimeoutError:
                security_monitor.log_security_event(
                    event_type="analysis_timeout",
                    severity="medium",
                    details={"url": url, "operation": "image_analysis"},
                    user_id=user_id,
                    ip_address=client_ip
                )
                logger.warning(f"Image analysis timeout for {url}")
            except Exception as e:
                security_monitor.log_security_event(
                    event_type="image_analysis_error",
                    severity="medium",
                    details={"url": url, "error": str(e)[:100]},
                    user_id=user_id,
                    ip_address=client_ip
                )
                logger.error(f"Error analyzing image from {url}: {e}")
                
            return matches

        async def _detect_faces(
            self, 
            image_data: bytes, 
            profile_data: Dict[str, Any],
            user_id: str,
            client_ip: str
        ) -> List[ContentMatch]:
            """Securely detect and match faces with enhanced error handling"""
            matches = []
            
            try:
                # Security: Limit image processing size
                if len(image_data) > 5 * 1024 * 1024:  # 5MB limit for face processing
                    logger.warning("Image too large for face processing", size=len(image_data))
                    return matches
                
                # Convert bytes to numpy array for face_recognition
                image_np = np.frombuffer(image_data, np.uint8)
                image_cv = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                
                if image_cv is None:
                    raise ValueError("Failed to decode image data")
                
                # Security: Check image dimensions
                height, width = image_cv.shape[:2]
                if width > 4096 or height > 4096:
                    # Resize if too large
                    scale = min(4096/width, 4096/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    image_cv = cv2.resize(image_cv, (new_width, new_height))
                
                image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
                
                # Find face encodings with error handling
                try:
                    face_locations = face_recognition.face_locations(
                        image_rgb, 
                        number_of_times_to_upsample=1,  # Limit upsampling for security
                        model="hog"  # Use faster but less accurate model for security
                    )
                    
                    if len(face_locations) > 10:  # Limit number of faces processed
                        logger.warning("Too many faces detected, limiting to 10", count=len(face_locations))
                        face_locations = face_locations[:10]
                    
                    face_encodings = face_recognition.face_encodings(
                        image_rgb, 
                        face_locations,
                        num_jitters=1  # Reduce jitters for faster processing
                    )
                    
                except Exception as face_error:
                    logger.warning("Face recognition processing failed", error=str(face_error))
                    return matches
                
                if face_encodings and profile_data.get('face_encodings'):
                    # Compare with profile face encodings
                    profile_encodings = [
                        np.array(encoding) for encoding in profile_data['face_encodings'][:5]  # Limit comparisons
                    ]
                    
                    for i, face_encoding in enumerate(face_encodings):
                        try:
                            results = face_recognition.compare_faces(
                                profile_encodings, face_encoding, tolerance=0.6
                            )
                            
                            if any(results):
                                # Calculate confidence based on face distance
                                distances = face_recognition.face_distance(
                                    profile_encodings, face_encoding
                                )
                                confidence = 1.0 - min(distances)
                                
                                # Security: Log face match for audit
                                security_monitor.log_security_event(
                                    event_type="face_match_detected",
                                    severity="info",
                                    details={
                                        "confidence": float(confidence),
                                        "face_index": i,
                                        "profile_id": profile_data.get('profile_id')
                                    },
                                    user_id=user_id,
                                    ip_address=client_ip
                                )
                                
                                matches.append(ContentMatch(
                                    match_type=MatchType.FACE,
                                    confidence=confidence,
                                    source_url=profile_data.get('source_url', ''),
                                    matched_content_id=profile_data.get('profile_id'),
                                    metadata={
                                        'face_locations': [list(loc) for loc in face_locations],  # Convert to serializable format
                                        'face_distance': float(min(distances)),
                                        'face_index': i
                                    },
                                    timestamp=datetime.utcnow()
                                ))
                        
                        except Exception as match_error:
                            logger.warning(f"Face matching error for face {i}", error=str(match_error))
                            continue
                            
            except Exception as e:
                security_monitor.log_security_event(
                    event_type="face_detection_error",
                    severity="medium",
                    details={"error": str(e)[:100]},
                    user_id=user_id,
                    ip_address=client_ip
                )
                logger.error(f"Error in face detection: {e}")
                
            return matches

        async def _match_perceptual_hash(self, image: Image.Image, url: str) -> List[ContentMatch]:
            """Match using perceptual hashing"""
            matches = []
            
            try:
                # Calculate different types of hashes
                phash = imagehash.phash(image)
                ahash = imagehash.average_hash(image)
                dhash = imagehash.dhash(image)
                
                # Store in cache for future comparisons
                hash_key = f"{url}_{hash(image.tobytes())}"
                self.image_features_cache[hash_key] = {
                    'phash': str(phash),
                    'ahash': str(ahash),
                    'dhash': str(dhash)
                }
                
                # In a real implementation, we would query the database
                # for similar hashes and compare
                
            except Exception as e:
                logger.error(f"Error calculating perceptual hash: {e}")
                
            return matches

        async def _match_image_similarity(
            self, 
            image: Image.Image, 
            url: str, 
            profile_data: Dict[str, Any]
        ) -> List[ContentMatch]:
            """Match using deep learning image similarity"""
            matches = []
            
            try:
                # Extract image features using ResNet
                preprocess = transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225]
                    )
                ])
                
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                image_tensor = preprocess(image).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    features = self.image_model(image_tensor)
                    features = features.squeeze().cpu().numpy()
                    
                # Store features for comparison
                feature_key = f"{url}_{hash(image.tobytes())}"
                self.image_features_cache[feature_key] = features.tolist()
                
                # Compare with profile image features if available
                if profile_data.get('image_features'):
                    profile_features = np.array(profile_data['image_features'])
                    
                    # Calculate cosine similarity
                    similarity = np.dot(features, profile_features) / (
                        np.linalg.norm(features) * np.linalg.norm(profile_features)
                    )
                    
                    if similarity > 0.8:  # High similarity threshold
                        matches.append(ContentMatch(
                            match_type=MatchType.SIMILAR_IMAGE,
                            confidence=float(similarity),
                            source_url=profile_data.get('source_url', ''),
                            matched_content_id=profile_data.get('profile_id'),
                            metadata={
                                'similarity_score': float(similarity),
                                'feature_vector_size': len(features)
                            },
                            timestamp=datetime.utcnow()
                        ))
                        
            except Exception as e:
                logger.error(f"Error in image similarity matching: {e}")
                
            return matches

        async def _analyze_video(
            self,
            url: str,
            video_data: bytes,
            profile_data: Dict[str, Any]
        ) -> List[ContentMatch]:
            """Analyze video content frame by frame"""
            matches = []
            
            try:
                # Extract frames from video and analyze each
                # This is a simplified implementation
                
                # Save video temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                    tmp.write(video_data)
                    tmp_path = tmp.name
                
                # Extract frames using OpenCV
                cap = cv2.VideoCapture(tmp_path)
                frame_count = 0
                max_frames = 30  # Analyze first 30 frames
                
                while cap.isOpened() and frame_count < max_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    # Convert frame to image bytes
                    _, img_encoded = cv2.imencode('.jpg', frame)
                    frame_bytes = img_encoded.tobytes()
                    
                    # Analyze frame as image
                    frame_matches = await self._analyze_image(
                        f"{url}_frame_{frame_count}", frame_bytes, profile_data
                    )
                    
                    matches.extend(frame_matches)
                    frame_count += 1
                
                cap.release()
                os.unlink(tmp_path)  # Clean up temp file
                
            except Exception as e:
                logger.error(f"Error analyzing video from {url}: {e}")
                
            return matches

        async def _analyze_text(
            self,
            url: str,
            text_data: bytes,
            profile_data: Dict[str, Any]
        ) -> List[ContentMatch]:
            """Analyze text content for matches"""
            matches = []
            
            try:
                text = text_data.decode('utf-8', errors='ignore')
                
                # Simple text matching - in production would use NLP
                if profile_data.get('text_signatures'):
                    for signature in profile_data['text_signatures']:
                        if signature.lower() in text.lower():
                            matches.append(ContentMatch(
                                match_type=MatchType.TEXT_MATCH,
                                confidence=0.9,
                                source_url=profile_data.get('source_url', ''),
                                matched_content_id=profile_data.get('profile_id'),
                                metadata={
                                    'matched_text': signature,
                                    'text_length': len(text)
                                },
                                timestamp=datetime.utcnow()
                            ))
                            
            except Exception as e:
                logger.error(f"Error analyzing text from {url}: {e}")
                
            return matches

        async def generate_profile_signatures(
            self, 
            profile_images: List[bytes],
            profile_texts: List[str]
        ) -> Dict[str, Any]:
            """Generate signatures for a creator profile"""
            signatures = {
                'face_encodings': [],
                'image_features': [],
                'text_signatures': profile_texts,
                'perceptual_hashes': []
            }
            
            try:
                for image_data in profile_images:
                    # Face encoding
                    image_np = np.frombuffer(image_data, np.uint8)
                    image_cv = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                    image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
                    
                    face_encodings = face_recognition.face_encodings(image_rgb)
                    for encoding in face_encodings:
                        signatures['face_encodings'].append(encoding.tolist())
                    
                    # Image features
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Perceptual hash
                    phash = imagehash.phash(image)
                    signatures['perceptual_hashes'].append(str(phash))
                    
                    # Deep features
                    preprocess = transforms.Compose([
                        transforms.Resize(256),
                        transforms.CenterCrop(224),
                        transforms.ToTensor(),
                        transforms.Normalize(
                            mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]
                        )
                    ])
                    
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                        
                    image_tensor = preprocess(image).unsqueeze(0).to(self.device)
                    
                    with torch.no_grad():
                        features = self.image_model(image_tensor)
                        features = features.squeeze().cpu().numpy()
                        signatures['image_features'].append(features.tolist())
                        
            except Exception as e:
                logger.error(f"Error generating signatures: {e}")
                
            return signatures

    # Global instance for production
    content_matcher = ContentMatcher()