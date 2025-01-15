from PIL import Image
import io
from typing import Optional, Tuple
import base64
from pathlib import Path
import time

class ImageHandler:
    def __init__(self, save_dir: str = "data/images"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, image_data: bytes) -> Tuple[bool, Optional[str]]:
        """Validate image data using Pillow instead of imghdr"""
        try:
            img = Image.open(io.BytesIO(image_data))
            format_name = img.format.lower()
            if format_name not in ['png', 'jpeg', 'jpg', 'gif']:
                return False, "Unsupported image format"
            return True, format_name
        except Exception as e:
            return False, str(e)

    def save_chart_image(self, token_address: str, image_data: bytes) -> str:
        """Save chart image with validation"""
        is_valid, format_info = self.validate_image(image_data)
        if not is_valid:
            raise ValueError(f"Invalid image data: {format_info}")

        # Create unique filename
        filename = f"chart_{token_address}_{int(time.time())}.{format_info}"
        filepath = self.save_dir / filename

        # Save image with Pillow
        img = Image.open(io.BytesIO(image_data))
        img.save(filepath)
        return str(filepath)

    def create_chart_thumbnail(self, image_path: str, size: Tuple[int, int] = (200, 200)) -> str:
        """Create thumbnail from chart image"""
        img = Image.open(image_path)
        img.thumbnail(size)
        
        thumbnail_path = f"{image_path}_thumb.png"
        img.save(thumbnail_path)
        return thumbnail_path

    def image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 for web display"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode() 