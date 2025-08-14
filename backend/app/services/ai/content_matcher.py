"""
AI-Powered Content Matching System
Implements facial recognition, image fingerprinting, and content matching
"""
import hashlib
import io
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from PIL import Image
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

from app.core.config import settings
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
    """Result of content matching"""
    match_type: MatchType
    confidence: float  # 0.0 to 1.0
    source_url: str
    matched_content_id: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime


class ContentMatcher:
    """
    AI-powered content matching engine
    PRD: "AI-based pattern recognition to identify likely infringements"
    """
    
    def __init__(self):
        # Initialize models
        self.face_model = None
        self.image_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load pre-trained models
        self._load_models()
        
        # Cache for face encodings and image features
        self.face_encodings_cache = {}
        self.image_features_cache = {}
        
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
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """
        Main entry point for content analysis
        PRD: "generating a face signature from images...comparing to the creator's face signature"
        """
        matches = []
        
        try:
            # Determine content type
            content_type = self._detect_content_type(content_data)
            
            if content_type == 'image':
                matches = await self._analyze_image(
                    content_url, content_data, profile_data
                )
            elif content_type == 'video':
                matches = await self._analyze_video(
                    content_url, content_data, profile_data
                )
            elif content_type == 'text':
                matches = await self._analyze_text(
                    content_url, content_data, profile_data
                )
                
        except Exception as e:
            logger.error(f"Error analyzing content from {content_url}: {e}")
            
        return matches
        
    async def _analyze_image(
        self,
        url: str,
        image_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """
        Analyze image for matches using multiple techniques
        PRD: "facial recognition AI to spot the creator's images/videos"
        """
        matches = []
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # 1. Face Recognition
            if profile_data.get('face_encodings'):
                face_matches = await self._check_face_match(
                    image, profile_data['face_encodings'], url
                )
                matches.extend(face_matches)
                
            # 2. Perceptual Hash Matching
            hash_match = await self._check_perceptual_hash(
                image, profile_data.get('content_hashes', []), url
            )
            if hash_match:
                matches.append(hash_match)
                
            # 3. Deep Learning Feature Matching
            if profile_data.get('image_features'):
                feature_match = await self._check_feature_match(
                    image, profile_data['image_features'], url
                )
                if feature_match:
                    matches.append(feature_match)
                    
            # 4. Watermark Detection
            if profile_data.get('watermarks'):
                watermark_match = await self._check_watermark(
                    image, profile_data['watermarks'], url
                )
                if watermark_match:
                    matches.append(watermark_match)
                    
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            
        return matches
        
    async def _check_face_match(
        self,
        image: Image.Image,
        known_encodings: List[np.ndarray],
        url: str
    ) -> List[ContentMatch]:
        """
        Check for face matches in image
        PRD: "Crucially, the platform implements facial recognition AI"
        """
        matches = []
        
        try:
            # Convert PIL to numpy array
            image_np = np.array(image)
            
            # Find faces in image
            face_locations = face_recognition.face_locations(image_np)
            
            if face_locations:
                # Get face encodings
                face_encodings = face_recognition.face_encodings(
                    image_np, face_locations
                )
                
                for face_encoding in face_encodings:
                    # Compare with known faces
                    for known_encoding in known_encodings:
                        # Calculate distance
                        distance = face_recognition.face_distance(
                            [known_encoding], face_encoding
                        )[0]
                        
                        # Convert distance to confidence (0-1)
                        confidence = 1.0 - min(distance, 1.0)
                        
                        # Threshold for match (adjustable)
                        if confidence > 0.6:
                            matches.append(ContentMatch(
                                match_type=MatchType.FACE,
                                confidence=confidence,
                                source_url=url,
                                matched_content_id=None,
                                metadata={
                                    "face_count": len(face_locations),
                                    "distance": float(distance)
                                },
                                timestamp=datetime.utcnow()
                            ))
                            break  # One match per face is enough
                            
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            
        return matches
        
    async def _check_perceptual_hash(
        self,
        image: Image.Image,
        known_hashes: List[str],
        url: str
    ) -> Optional[ContentMatch]:
        """
        Check image using perceptual hashing
        PRD: "using perceptual hashing or neural network image matching"
        """
        try:
            # Generate multiple hash types for robustness
            hashes = {
                'average': str(imagehash.average_hash(image)),
                'perceptual': str(imagehash.phash(image)),
                'difference': str(imagehash.dhash(image)),
                'wavelet': str(imagehash.whash(image))
            }
            
            # Check against known hashes
            for known_hash_data in known_hashes:
                for hash_type, current_hash in hashes.items():
                    known_hash = known_hash_data.get(hash_type)
                    
                    if known_hash:
                        # Calculate hamming distance
                        distance = imagehash.hex_to_hash(current_hash) - \
                                 imagehash.hex_to_hash(known_hash)
                        
                        # Threshold for similarity (adjustable)
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
                                    "hash": current_hash
                                },
                                timestamp=datetime.utcnow()
                            )
                            
        except Exception as e:
            logger.error(f"Perceptual hash error: {e}")
            
        return None
        
    async def _check_feature_match(
        self,
        image: Image.Image,
        known_features: List[np.ndarray],
        url: str
    ) -> Optional[ContentMatch]:
        """
        Check image using deep learning feature extraction
        """
        try:
            # Preprocess image for model
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Get image tensor
            image_tensor = preprocess(image).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.image_model(image_tensor)
                features = features.squeeze().cpu().numpy()
                
            # Compare with known features
            for known_feature in known_features:
                # Cosine similarity
                similarity = np.dot(features, known_feature) / (
                    np.linalg.norm(features) * np.linalg.norm(known_feature)
                )
                
                # Threshold for match
                if similarity > 0.85:
                    return ContentMatch(
                        match_type=MatchType.SIMILAR_IMAGE,
                        confidence=float(similarity),
                        source_url=url,
                        matched_content_id=None,
                        metadata={
                            "similarity": float(similarity),
                            "method": "deep_features"
                        },
                        timestamp=datetime.utcnow()
                    )
                    
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            
        return None
        
    async def _check_watermark(
        self,
        image: Image.Image,
        watermarks: List[Dict[str, Any]],
        url: str
    ) -> Optional[ContentMatch]:
        """
        Check for invisible watermarks in image
        PRD: "invisible watermarking tool"
        """
        # This would implement watermark detection
        # For MVP, returning None
        return None
        
    async def _analyze_video(
        self,
        url: str,
        video_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """
        Analyze video content by extracting frames
        """
        matches = []
        
        try:
            # Save video temporarily
            temp_path = f"/tmp/video_{hashlib.md5(url.encode()).hexdigest()}.mp4"
            with open(temp_path, 'wb') as f:
                f.write(video_data)
                
            # Open video with OpenCV
            cap = cv2.VideoCapture(temp_path)
            
            # Sample frames at intervals
            frame_interval = int(cap.get(cv2.CAP_PROP_FPS) * 5)  # Every 5 seconds
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                
                if not ret:
                    break
                    
                if frame_count % frame_interval == 0:
                    # Convert frame to PIL Image
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Analyze frame as image
                    frame_matches = await self._analyze_image(
                        url, 
                        self._image_to_bytes(pil_image),
                        profile_data
                    )
                    
                    # Add frame info to metadata
                    for match in frame_matches:
                        match.metadata['frame_number'] = frame_count
                        match.metadata['video'] = True
                        
                    matches.extend(frame_matches)
                    
                frame_count += 1
                
                # Limit frames analyzed for performance
                if len(matches) > 10 or frame_count > 300:
                    break
                    
            cap.release()
            
            # Clean up temp file
            import os
            os.remove(temp_path)
            
        except Exception as e:
            logger.error(f"Video analysis error: {e}")
            
        return matches
        
    async def _analyze_text(
        self,
        url: str,
        text_data: bytes,
        profile_data: Dict[str, Any]
    ) -> List[ContentMatch]:
        """
        Analyze text content for matches
        """
        matches = []
        
        try:
            text = text_data.decode('utf-8', errors='ignore').lower()
            
            # Check for username mentions
            username = profile_data.get('username', '').lower()
            if username and username in text:
                # Count occurrences
                count = text.count(username)
                confidence = min(1.0, count * 0.2)  # More mentions = higher confidence
                
                matches.append(ContentMatch(
                    match_type=MatchType.TEXT_MATCH,
                    confidence=confidence,
                    source_url=url,
                    matched_content_id=None,
                    metadata={
                        "username_mentions": count,
                        "text_length": len(text)
                    },
                    timestamp=datetime.utcnow()
                ))
                
            # Check for other keywords
            keywords = profile_data.get('keywords', [])
            keyword_matches = []
            
            for keyword in keywords:
                if keyword.lower() in text:
                    keyword_matches.append(keyword)
                    
            if keyword_matches:
                matches.append(ContentMatch(
                    match_type=MatchType.TEXT_MATCH,
                    confidence=min(1.0, len(keyword_matches) * 0.3),
                    source_url=url,
                    matched_content_id=None,
                    metadata={
                        "matched_keywords": keyword_matches,
                        "text_length": len(text)
                    },
                    timestamp=datetime.utcnow()
                ))
                
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            
        return matches
        
    def _detect_content_type(self, content_data: bytes) -> str:
        """Detect content type from bytes"""
        # Check magic bytes
        if content_data.startswith(b'\xff\xd8\xff'):
            return 'image'  # JPEG
        elif content_data.startswith(b'\x89PNG'):
            return 'image'  # PNG
        elif content_data.startswith(b'GIF8'):
            return 'image'  # GIF
        elif b'<html' in content_data[:1000].lower():
            return 'text'  # HTML
        elif content_data[4:8] == b'ftyp':
            return 'video'  # MP4
        else:
            return 'unknown'
            
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to bytes"""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
        
    async def generate_profile_signatures(
        self,
        profile_images: List[bytes]
    ) -> Dict[str, Any]:
        """
        Generate face encodings and image features for a profile
        Used when setting up a new creator profile
        """
        signatures = {
            'face_encodings': [],
            'image_features': [],
            'content_hashes': []
        }
        
        for image_data in profile_images:
            try:
                image = Image.open(io.BytesIO(image_data))
                
                # Extract face encoding
                image_np = np.array(image)
                face_locations = face_recognition.face_locations(image_np)
                
                if face_locations:
                    face_encodings = face_recognition.face_encodings(
                        image_np, face_locations
                    )
                    for encoding in face_encodings:
                        signatures['face_encodings'].append(encoding.tolist())
                        
                # Generate perceptual hashes
                hash_data = {
                    'average': str(imagehash.average_hash(image)),
                    'perceptual': str(imagehash.phash(image)),
                    'difference': str(imagehash.dhash(image)),
                    'wavelet': str(imagehash.whash(image))
                }
                signatures['content_hashes'].append(hash_data)
                
                # Extract deep features
                if self.image_model:
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