import os
import uuid
import aiofiles
from typing import Optional
from fastapi import UploadFile
from PIL import Image
import hashlib

from app.core.config import settings


class FileStorage:
    """File storage service for handling uploads."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.UPLOAD_DIR
        os.makedirs(self.base_path, exist_ok=True)
    
    async def save_file(
        self, 
        file: UploadFile, 
        subfolder: str = "general",
        max_size: int = None
    ) -> str:
        """Save uploaded file and return file path."""
        # Create subfolder if it doesn't exist
        folder_path = os.path.join(self.base_path, subfolder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Check file size
        if max_size and file.size and file.size > max_size:
            raise ValueError(f"File size ({file.size}) exceeds maximum ({max_size})")
        
        # Generate unique filename
        file_extension = self._get_file_extension(file.filename)
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(folder_path, unique_filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Return relative path
        return os.path.join(subfolder, unique_filename)
    
    async def save_avatar(self, user_id: int, file: UploadFile) -> str:
        """Save user avatar with image processing."""
        # Validate image
        if not file.content_type.startswith('image/'):
            raise ValueError("File must be an image")
        
        # Create avatars folder
        avatars_folder = os.path.join(self.base_path, "avatars")
        os.makedirs(avatars_folder, exist_ok=True)
        
        # Generate filename based on user ID
        file_extension = self._get_file_extension(file.filename)
        filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = os.path.join(avatars_folder, filename)
        
        # Read and process image
        content = await file.read()
        
        # Resize and optimize image
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Resize to 200x200 while maintaining aspect ratio
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(file_path, "JPEG", quality=85, optimize=True)
        
        except Exception as e:
            # Fallback: save original file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        
        return f"/static/avatars/{filename}"
    
    async def delete_avatar(self, avatar_url: str) -> bool:
        """Delete avatar file."""
        try:
            # Extract filename from URL
            if avatar_url.startswith("/static/avatars/"):
                filename = avatar_url.replace("/static/avatars/", "")
                file_path = os.path.join(self.base_path, "avatars", filename)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
        except Exception as e:
            print(f"Error deleting avatar: {e}")
        
        return False
    
    async def save_reference_image(
        self, 
        profile_id: int, 
        file: UploadFile
    ) -> tuple[str, str]:
        """Save reference image and return path and hash."""
        # Create reference images folder
        ref_folder = os.path.join(self.base_path, "reference_images")
        os.makedirs(ref_folder, exist_ok=True)
        
        # Generate filename
        file_extension = self._get_file_extension(file.filename)
        filename = f"profile_{profile_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(ref_folder, filename)
        
        # Read content and calculate hash
        content = await file.read()
        image_hash = hashlib.sha256(content).hexdigest()
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return f"/static/reference_images/{filename}", image_hash
    
    async def save_evidence_file(
        self, 
        infringement_id: int, 
        file: UploadFile
    ) -> str:
        """Save evidence file for an infringement."""
        # Create evidence folder
        evidence_folder = os.path.join(self.base_path, "evidence")
        os.makedirs(evidence_folder, exist_ok=True)
        
        # Generate filename
        file_extension = self._get_file_extension(file.filename)
        filename = f"evidence_{infringement_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(evidence_folder, filename)
        
        # Save file
        content = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return f"/static/evidence/{filename}"
    
    def _get_file_extension(self, filename: Optional[str]) -> str:
        """Get file extension from filename."""
        if not filename:
            return ""
        
        if "." in filename:
            return "." + filename.rsplit(".", 1)[1].lower()
        return ""
    
    def get_file_path(self, relative_path: str) -> str:
        """Get absolute file path from relative path."""
        return os.path.join(self.base_path, relative_path)
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        full_path = self.get_file_path(relative_path)
        return os.path.exists(full_path)
    
    async def delete_file(self, relative_path: str) -> bool:
        """Delete file by relative path."""
        try:
            full_path = self.get_file_path(relative_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception as e:
            print(f"Error deleting file {relative_path}: {e}")
        
        return False


# Global instance
file_storage = FileStorage()


# Convenience functions
async def save_avatar(user_id: int, file: UploadFile) -> str:
    """Save user avatar."""
    return await file_storage.save_avatar(user_id, file)


async def delete_avatar(avatar_url: str) -> bool:
    """Delete user avatar."""
    return await file_storage.delete_avatar(avatar_url)