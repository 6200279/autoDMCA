"""
Content Watermarking System
Implements invisible watermarks to trace content leaks
"""
import hashlib
import io
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import logging
from PIL import Image, ImageDraw, ImageFont
import cv2
import random
import base64
import json
from cryptography.fernet import Fernet
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WatermarkData:
    """Watermark information"""
    watermark_id: str
    creator_id: int
    subscriber_id: Optional[int]
    content_type: str
    creation_date: datetime
    metadata: Dict[str, Any]


class InvisibleWatermarker:
    """
    Invisible watermarking system to trace content leaks
    PRD: "invisible watermarking tool for creators"
    """
    
    def __init__(self):
        # Generate or load encryption key
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for watermarks"""
        # In production, this would be stored securely
        key_string = os.getenv('WATERMARK_KEY', 'default_key_for_development_only')
        key_hash = hashlib.sha256(key_string.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)
        
    async def create_watermarked_image(
        self,
        image_data: bytes,
        creator_id: int,
        subscriber_id: Optional[int] = None,
        watermark_strength: float = 0.1
    ) -> Tuple[bytes, str]:
        """
        Create watermarked version of image
        Returns (watermarked_image_bytes, watermark_id)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Generate unique watermark ID
            watermark_id = self._generate_watermark_id(creator_id, subscriber_id)
            
            # Create watermark data
            watermark_data = WatermarkData(
                watermark_id=watermark_id,
                creator_id=creator_id,
                subscriber_id=subscriber_id,
                content_type='image',
                creation_date=datetime.utcnow(),
                metadata={}
            )
            
            # Apply invisible watermark using multiple techniques
            watermarked_image = await self._apply_invisible_watermark(
                image, watermark_data, watermark_strength
            )
            
            # Convert back to bytes
            img_byte_arr = io.BytesIO()
            watermarked_image.save(img_byte_arr, format=image.format or 'PNG')
            watermarked_bytes = img_byte_arr.getvalue()
            
            # Store watermark info
            await self._store_watermark_info(watermark_data)
            
            logger.info(f"Created watermarked image: {watermark_id}")
            return watermarked_bytes, watermark_id
            
        except Exception as e:
            logger.error(f"Error creating watermarked image: {e}")
            raise
            
    async def create_watermarked_video(
        self,
        video_data: bytes,
        creator_id: int,
        subscriber_id: Optional[int] = None,
        watermark_strength: float = 0.1
    ) -> Tuple[bytes, str]:
        """
        Create watermarked version of video
        Returns (watermarked_video_bytes, watermark_id)
        """
        try:
            watermark_id = self._generate_watermark_id(creator_id, subscriber_id)
            
            # Save video temporarily
            temp_input = f"/tmp/input_{watermark_id}.mp4"
            temp_output = f"/tmp/output_{watermark_id}.mp4"
            
            with open(temp_input, 'wb') as f:
                f.write(video_data)
                
            # Create watermark data
            watermark_data = WatermarkData(
                watermark_id=watermark_id,
                creator_id=creator_id,
                subscriber_id=subscriber_id,
                content_type='video',
                creation_date=datetime.utcnow(),
                metadata={}
            )
            
            # Apply watermark to video
            await self._apply_video_watermark(
                temp_input, temp_output, watermark_data, watermark_strength
            )
            
            # Read watermarked video
            with open(temp_output, 'rb') as f:
                watermarked_bytes = f.read()
                
            # Clean up temp files
            import os
            os.remove(temp_input)
            os.remove(temp_output)
            
            # Store watermark info
            await self._store_watermark_info(watermark_data)
            
            logger.info(f"Created watermarked video: {watermark_id}")
            return watermarked_bytes, watermark_id
            
        except Exception as e:
            logger.error(f"Error creating watermarked video: {e}")
            raise
            
    async def _apply_invisible_watermark(
        self,
        image: Image.Image,
        watermark_data: WatermarkData,
        strength: float
    ) -> Image.Image:
        """Apply invisible watermark using multiple techniques"""
        
        # Convert to numpy array for processing
        img_array = np.array(image)
        
        # Technique 1: LSB (Least Significant Bit) Steganography
        watermarked_array = await self._apply_lsb_watermark(
            img_array, watermark_data, strength
        )
        
        # Technique 2: DCT (Discrete Cosine Transform) watermarking
        watermarked_array = await self._apply_dct_watermark(
            watermarked_array, watermark_data, strength
        )
        
        # Technique 3: Spatial Domain watermarking
        watermarked_array = await self._apply_spatial_watermark(
            watermarked_array, watermark_data, strength
        )
        
        # Convert back to PIL Image
        watermarked_image = Image.fromarray(watermarked_array.astype('uint8'))
        return watermarked_image
        
    async def _apply_lsb_watermark(
        self,
        img_array: np.ndarray,
        watermark_data: WatermarkData,
        strength: float
    ) -> np.ndarray:
        """Apply LSB steganography watermark"""
        
        # Create watermark message
        message = json.dumps({
            'id': watermark_data.watermark_id,
            'creator': watermark_data.creator_id,
            'subscriber': watermark_data.subscriber_id,
            'timestamp': watermark_data.creation_date.timestamp()
        })
        
        # Encrypt message
        encrypted_message = self.cipher_suite.encrypt(message.encode())
        
        # Convert to binary
        binary_message = ''.join(format(byte, '08b') for byte in encrypted_message)
        
        # Add end marker
        binary_message += '1111111111111110'  # End marker
        
        # Embed in LSBs
        flat_array = img_array.flatten()
        
        for i, bit in enumerate(binary_message):
            if i >= len(flat_array):
                break
                
            # Modify LSB based on strength
            if random.random() < strength:
                flat_array[i] = (flat_array[i] & 0xFE) | int(bit)
                
        return flat_array.reshape(img_array.shape)
        
    async def _apply_dct_watermark(
        self,
        img_array: np.ndarray,
        watermark_data: WatermarkData,
        strength: float
    ) -> np.ndarray:
        """Apply DCT domain watermark"""
        
        if len(img_array.shape) == 3:
            # Work with luminance channel for color images
            height, width, channels = img_array.shape
            
            # Convert to YUV
            yuv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2YUV)
            y_channel = yuv_img[:, :, 0].astype(np.float32)
            
        else:
            y_channel = img_array.astype(np.float32)
            height, width = img_array.shape
            channels = 1
            
        # Apply DCT in 8x8 blocks
        watermarked_y = y_channel.copy()
        
        # Generate pseudo-random sequence from watermark ID
        np.random.seed(hash(watermark_data.watermark_id) % (2**32))
        
        for i in range(0, height - 8, 8):
            for j in range(0, width - 8, 8):
                # Extract 8x8 block
                block = y_channel[i:i+8, j:j+8]
                
                # Apply DCT
                dct_block = cv2.dct(block)
                
                # Embed watermark in mid-frequency coefficients
                watermark_bit = np.random.randint(0, 2)
                
                # Modify coefficient based on watermark bit and strength
                if watermark_bit == 1:
                    dct_block[2, 3] += strength * 10
                else:
                    dct_block[2, 3] -= strength * 10
                    
                # Apply inverse DCT
                watermarked_block = cv2.idct(dct_block)
                watermarked_y[i:i+8, j:j+8] = watermarked_block
                
        # Convert back to original color space
        if channels == 3:
            yuv_img[:, :, 0] = np.clip(watermarked_y, 0, 255)
            watermarked_img = cv2.cvtColor(yuv_img, cv2.COLOR_YUV2RGB)
        else:
            watermarked_img = np.clip(watermarked_y, 0, 255)
            
        return watermarked_img.astype(np.uint8)
        
    async def _apply_spatial_watermark(
        self,
        img_array: np.ndarray,
        watermark_data: WatermarkData,
        strength: float
    ) -> np.ndarray:
        """Apply spatial domain watermark"""
        
        # Generate watermark pattern from ID
        pattern_seed = hash(watermark_data.watermark_id) % (2**32)
        np.random.seed(pattern_seed)
        
        height, width = img_array.shape[:2]
        
        # Create pseudo-random watermark pattern
        watermark_pattern = np.random.normal(0, strength * 255, (height, width))
        
        # Apply to each channel
        watermarked_img = img_array.copy().astype(np.float32)
        
        if len(img_array.shape) == 3:
            for channel in range(img_array.shape[2]):
                watermarked_img[:, :, channel] += watermark_pattern
        else:
            watermarked_img += watermark_pattern
            
        # Clip values to valid range
        watermarked_img = np.clip(watermarked_img, 0, 255)
        
        return watermarked_img.astype(np.uint8)
        
    async def _apply_video_watermark(
        self,
        input_path: str,
        output_path: str,
        watermark_data: WatermarkData,
        strength: float
    ):
        """Apply watermark to video file"""
        
        cap = cv2.VideoCapture(input_path)
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
                
            # Apply watermark to frame
            watermarked_frame = await self._apply_frame_watermark(
                frame, watermark_data, strength, frame_count
            )
            
            out.write(watermarked_frame)
            frame_count += 1
            
        cap.release()
        out.release()
        
    async def _apply_frame_watermark(
        self,
        frame: np.ndarray,
        watermark_data: WatermarkData,
        strength: float,
        frame_number: int
    ) -> np.ndarray:
        """Apply watermark to a single video frame"""
        
        # Use frame number to create temporal variation
        frame_seed = hash(f"{watermark_data.watermark_id}_{frame_number}") % (2**32)
        np.random.seed(frame_seed)
        
        # Apply spatial watermark
        watermarked_frame = await self._apply_spatial_watermark(
            frame, watermark_data, strength
        )
        
        return watermarked_frame
        
    async def detect_watermark(
        self,
        content_data: bytes,
        content_type: str = 'image'
    ) -> Optional[WatermarkData]:
        """
        Detect and extract watermark from content
        Returns watermark data if found, None otherwise
        """
        try:
            if content_type == 'image':
                return await self._detect_image_watermark(content_data)
            elif content_type == 'video':
                return await self._detect_video_watermark(content_data)
            else:
                logger.warning(f"Unsupported content type for watermark detection: {content_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error detecting watermark: {e}")
            return None
            
    async def _detect_image_watermark(self, image_data: bytes) -> Optional[WatermarkData]:
        """Detect watermark in image"""
        try:
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            
            # Try LSB detection first
            watermark_data = await self._detect_lsb_watermark(img_array)
            if watermark_data:
                return watermark_data
                
            # Try DCT detection
            watermark_data = await self._detect_dct_watermark(img_array)
            if watermark_data:
                return watermark_data
                
            # Try spatial detection
            watermark_data = await self._detect_spatial_watermark(img_array)
            if watermark_data:
                return watermark_data
                
            return None
            
        except Exception as e:
            logger.error(f"Error in image watermark detection: {e}")
            return None
            
    async def _detect_lsb_watermark(self, img_array: np.ndarray) -> Optional[WatermarkData]:
        """Detect LSB steganography watermark"""
        try:
            # Extract LSBs
            flat_array = img_array.flatten()
            binary_data = ''.join(str(pixel & 1) for pixel in flat_array)
            
            # Look for end marker
            end_marker = '1111111111111110'
            end_pos = binary_data.find(end_marker)
            
            if end_pos == -1:
                return None
                
            # Extract message
            message_binary = binary_data[:end_pos]
            
            # Convert to bytes
            if len(message_binary) % 8 != 0:
                return None
                
            message_bytes = bytes(
                int(message_binary[i:i+8], 2) 
                for i in range(0, len(message_binary), 8)
            )
            
            # Decrypt message
            try:
                decrypted_message = self.cipher_suite.decrypt(message_bytes)
                watermark_info = json.loads(decrypted_message.decode())
                
                return WatermarkData(
                    watermark_id=watermark_info['id'],
                    creator_id=watermark_info['creator'],
                    subscriber_id=watermark_info.get('subscriber'),
                    content_type='image',
                    creation_date=datetime.fromtimestamp(watermark_info['timestamp']),
                    metadata={'detection_method': 'lsb'}
                )
                
            except Exception:
                return None
                
        except Exception as e:
            logger.error(f"LSB detection error: {e}")
            return None
            
    async def _detect_dct_watermark(self, img_array: np.ndarray) -> Optional[WatermarkData]:
        """Detect DCT domain watermark"""
        # DCT watermark detection is complex and would require
        # correlation with known watermark patterns
        # This is a placeholder implementation
        return None
        
    async def _detect_spatial_watermark(self, img_array: np.ndarray) -> Optional[WatermarkData]:
        """Detect spatial domain watermark"""
        # Spatial watermark detection would require correlation analysis
        # This is a placeholder implementation
        return None
        
    async def _detect_video_watermark(self, video_data: bytes) -> Optional[WatermarkData]:
        """Detect watermark in video"""
        # Video watermark detection would extract frames and analyze them
        # This is a placeholder implementation
        return None
        
    def _generate_watermark_id(self, creator_id: int, subscriber_id: Optional[int]) -> str:
        """Generate unique watermark ID"""
        timestamp = datetime.utcnow().timestamp()
        data = f"{creator_id}_{subscriber_id}_{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
        
    async def _store_watermark_info(self, watermark_data: WatermarkData):
        """Store watermark information in database"""
        # In production, this would store in database
        logger.info(f"Storing watermark info: {watermark_data.watermark_id}")
        
    async def get_watermark_info(self, watermark_id: str) -> Optional[WatermarkData]:
        """Get watermark information by ID"""
        # In production, this would query database
        return None
        
    async def trace_leak_source(
        self,
        leaked_content: bytes,
        content_type: str = 'image'
    ) -> Optional[Dict[str, Any]]:
        """
        Trace the source of leaked content using watermarks
        PRD: "watermark can be read by our system to trace the source"
        """
        try:
            # Detect watermark
            watermark_data = await self.detect_watermark(leaked_content, content_type)
            
            if not watermark_data:
                return None
                
            # Get additional info from database
            watermark_info = await self.get_watermark_info(watermark_data.watermark_id)
            
            return {
                'watermark_id': watermark_data.watermark_id,
                'creator_id': watermark_data.creator_id,
                'subscriber_id': watermark_data.subscriber_id,
                'leak_traced': True,
                'creation_date': watermark_data.creation_date,
                'detection_method': watermark_data.metadata.get('detection_method'),
                'confidence': 0.95  # High confidence for successful detection
            }
            
        except Exception as e:
            logger.error(f"Error tracing leak source: {e}")
            return None


import os