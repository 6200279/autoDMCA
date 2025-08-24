import os
import uuid
import hashlib
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class WatermarkType:
    VISIBLE = "visible"
    INVISIBLE = "invisible"
    TEXT = "text"
    IMAGE = "image"
    DIGITAL_SIGNATURE = "digital_signature"

class ContentWatermarkingService:
    """
    Advanced content watermarking service supporting multiple watermark types
    PRD: "Content Watermarking" - Invisible and visible watermarks for content protection
    """
    
    def __init__(self):
        self.temp_dir = "/tmp/watermarking"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def generate_watermark_id(self, content: bytes) -> str:
        """Generate unique watermark ID based on content hash"""
        content_hash = hashlib.sha256(content).hexdigest()
        return f"wm_{content_hash[:16]}_{uuid.uuid4().hex[:8]}"
    
    def add_visible_text_watermark(
        self, 
        image_path: str, 
        text: str, 
        position: str = "bottom_right",
        opacity: float = 0.7,
        font_size: int = 36,
        font_color: str = "white"
    ) -> str:
        """Add visible text watermark to image"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGBA if not already
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create transparent overlay
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # Load font (use default if custom font not available)
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Get text size
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Calculate position
                if position == "bottom_right":
                    x = img.width - text_width - 20
                    y = img.height - text_height - 20
                elif position == "bottom_left":
                    x = 20
                    y = img.height - text_height - 20
                elif position == "top_right":
                    x = img.width - text_width - 20
                    y = 20
                elif position == "top_left":
                    x = 20
                    y = 20
                else:  # center
                    x = (img.width - text_width) // 2
                    y = (img.height - text_height) // 2
                
                # Convert color string to RGBA
                color_alpha = int(255 * opacity)
                if font_color == "white":
                    color = (255, 255, 255, color_alpha)
                elif font_color == "black":
                    color = (0, 0, 0, color_alpha)
                else:
                    color = (255, 255, 255, color_alpha)  # Default to white
                
                # Draw text on overlay
                draw.text((x, y), text, font=font, fill=color)
                
                # Composite the overlay onto the image
                watermarked = Image.alpha_composite(img, overlay)
                
                # Convert back to RGB if needed
                if watermarked.mode == 'RGBA':
                    watermarked = watermarked.convert('RGB')
                
                # Save watermarked image
                output_path = os.path.join(self.temp_dir, f"watermarked_{uuid.uuid4().hex}.jpg")
                watermarked.save(output_path, format='JPEG', quality=95)
                
                return output_path
                
        except Exception as e:
            logger.error(f"Error adding visible text watermark: {e}")
            raise e
    
    def add_invisible_watermark(
        self, 
        image_path: str, 
        watermark_data: str,
        strength: float = 0.1
    ) -> str:
        """Add invisible watermark using LSB steganography"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not load image")
            
            # Convert watermark data to binary
            watermark_binary = ''.join(format(ord(char), '08b') for char in watermark_data)
            watermark_binary += '1111111111111110'  # End delimiter
            
            # Check if image can hold the watermark
            max_bytes = img.shape[0] * img.shape[1] * 3 // 8
            if len(watermark_data) > max_bytes - 2:  # -2 for delimiter
                raise ValueError("Watermark data too large for image")
            
            # Embed watermark
            data_index = 0
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    if data_index < len(watermark_binary):
                        # Modify the least significant bit of blue channel
                        img[i][j][0] = (img[i][j][0] & 0xFE) | int(watermark_binary[data_index])
                        data_index += 1
                    else:
                        break
                if data_index >= len(watermark_binary):
                    break
            
            # Save watermarked image
            output_path = os.path.join(self.temp_dir, f"invisible_wm_{uuid.uuid4().hex}.png")
            cv2.imwrite(output_path, img)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding invisible watermark: {e}")
            raise e
    
    def extract_invisible_watermark(self, image_path: str) -> Optional[str]:
        """Extract invisible watermark from image"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Extract binary data from LSB
            binary_data = ""
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    # Get LSB of blue channel
                    binary_data += str(img[i][j][0] & 1)
            
            # Look for end delimiter
            delimiter = '1111111111111110'
            delimiter_index = binary_data.find(delimiter)
            
            if delimiter_index == -1:
                return None
            
            # Extract watermark data
            watermark_binary = binary_data[:delimiter_index]
            
            # Convert binary to text
            watermark_text = ""
            for i in range(0, len(watermark_binary), 8):
                byte = watermark_binary[i:i+8]
                if len(byte) == 8:
                    watermark_text += chr(int(byte, 2))
            
            return watermark_text
            
        except Exception as e:
            logger.error(f"Error extracting invisible watermark: {e}")
            return None
    
    def add_image_watermark(
        self, 
        base_image_path: str, 
        watermark_image_path: str,
        position: str = "bottom_right",
        scale: float = 0.1,
        opacity: float = 0.7
    ) -> str:
        """Add image watermark to base image"""
        try:
            with Image.open(base_image_path) as base_img:
                with Image.open(watermark_image_path) as watermark_img:
                    # Convert to RGBA
                    base_img = base_img.convert('RGBA')
                    watermark_img = watermark_img.convert('RGBA')
                    
                    # Scale watermark
                    wm_width = int(base_img.width * scale)
                    wm_height = int(watermark_img.height * (wm_width / watermark_img.width))
                    watermark_img = watermark_img.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
                    
                    # Apply opacity
                    watermark_img = self._apply_opacity(watermark_img, opacity)
                    
                    # Calculate position
                    if position == "bottom_right":
                        x = base_img.width - wm_width - 20
                        y = base_img.height - wm_height - 20
                    elif position == "bottom_left":
                        x = 20
                        y = base_img.height - wm_height - 20
                    elif position == "top_right":
                        x = base_img.width - wm_width - 20
                        y = 20
                    elif position == "top_left":
                        x = 20
                        y = 20
                    else:  # center
                        x = (base_img.width - wm_width) // 2
                        y = (base_img.height - wm_height) // 2
                    
                    # Paste watermark
                    base_img.paste(watermark_img, (x, y), watermark_img)
                    
                    # Convert back to RGB
                    result = base_img.convert('RGB')
                    
                    # Save result
                    output_path = os.path.join(self.temp_dir, f"img_watermarked_{uuid.uuid4().hex}.jpg")
                    result.save(output_path, format='JPEG', quality=95)
                    
                    return output_path
                    
        except Exception as e:
            logger.error(f"Error adding image watermark: {e}")
            raise e
    
    def _apply_opacity(self, image: Image.Image, opacity: float) -> Image.Image:
        """Apply opacity to an image"""
        # Create a copy to avoid modifying original
        img_copy = image.copy()
        
        # Get alpha channel
        if img_copy.mode == 'RGBA':
            # Modify alpha channel
            data = list(img_copy.getdata())
            new_data = []
            for item in data:
                new_alpha = int(item[3] * opacity)
                new_data.append((item[0], item[1], item[2], new_alpha))
            img_copy.putdata(new_data)
        
        return img_copy
    
    def create_digital_signature(
        self, 
        content_path: str, 
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Create digital signature for content"""
        try:
            # Read content
            with open(content_path, 'rb') as f:
                content = f.read()
            
            # Create signature data
            signature_data = {
                "user_id": user_id,
                "timestamp": str(int(time.time())),
                "content_hash": hashlib.sha256(content).hexdigest(),
                "metadata": metadata or {}
            }
            
            # Create signature string
            signature_string = json.dumps(signature_data, sort_keys=True)
            
            # Create watermark ID
            watermark_id = self.generate_watermark_id(content)
            
            # Store signature (in production, this would go to database)
            signature_file = os.path.join(self.temp_dir, f"{watermark_id}_signature.json")
            with open(signature_file, 'w') as f:
                json.dump(signature_data, f)
            
            return {
                "watermark_id": watermark_id,
                "signature": signature_string,
                "signature_file": signature_file
            }
            
        except Exception as e:
            logger.error(f"Error creating digital signature: {e}")
            raise e
    
    def verify_digital_signature(
        self, 
        content_path: str, 
        watermark_id: str
    ) -> Dict[str, Any]:
        """Verify digital signature of content"""
        try:
            # Load signature
            signature_file = os.path.join(self.temp_dir, f"{watermark_id}_signature.json")
            if not os.path.exists(signature_file):
                return {"verified": False, "error": "Signature not found"}
            
            with open(signature_file, 'r') as f:
                stored_signature = json.load(f)
            
            # Verify content hash
            with open(content_path, 'rb') as f:
                content = f.read()
            
            current_hash = hashlib.sha256(content).hexdigest()
            stored_hash = stored_signature.get("content_hash")
            
            if current_hash != stored_hash:
                return {
                    "verified": False, 
                    "error": "Content has been modified",
                    "original_hash": stored_hash,
                    "current_hash": current_hash
                }
            
            return {
                "verified": True,
                "user_id": stored_signature.get("user_id"),
                "timestamp": stored_signature.get("timestamp"),
                "metadata": stored_signature.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Error verifying digital signature: {e}")
            return {"verified": False, "error": str(e)}
    
    def batch_watermark_images(
        self, 
        image_paths: List[str], 
        watermark_config: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Apply watermarks to multiple images in batch"""
        results = []
        
        for image_path in image_paths:
            try:
                watermark_type = watermark_config.get("type", "visible")
                
                if watermark_type == "visible":
                    output_path = self.add_visible_text_watermark(
                        image_path,
                        watermark_config.get("text", "© Protected Content"),
                        watermark_config.get("position", "bottom_right"),
                        watermark_config.get("opacity", 0.7),
                        watermark_config.get("font_size", 36),
                        watermark_config.get("font_color", "white")
                    )
                elif watermark_type == "invisible":
                    output_path = self.add_invisible_watermark(
                        image_path,
                        watermark_config.get("data", f"Protected by AutoDMCA - {uuid.uuid4().hex[:8]}"),
                        watermark_config.get("strength", 0.1)
                    )
                else:
                    raise ValueError(f"Unsupported watermark type: {watermark_type}")
                
                results.append({
                    "input_path": image_path,
                    "output_path": output_path,
                    "status": "success"
                })
                
            except Exception as e:
                results.append({
                    "input_path": image_path,
                    "output_path": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """Clean up temporary watermarked files"""
        try:
            import time
            current_time = time.time()
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    # Check file age
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > (older_than_hours * 3600):
                        os.remove(file_path)
                        logger.info(f"Cleaned up old temp file: {filename}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

# Import required modules at the top of the file
import time
import json