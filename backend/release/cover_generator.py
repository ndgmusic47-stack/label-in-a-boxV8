"""
Cover Art Generator for Release Pipeline - PHASE 5
Ensures EXACTLY 3000×3000 output with proper padding and safety checks.
"""

import os
import logging
import random
from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

from backend.release.utils import sanitize_text_input

logger = logging.getLogger(__name__)

# Brand color for padding: #4B0082 (indigo)
BRAND_COLOR = (75, 0, 130)  # RGB for #4B0082
TARGET_SIZE = (3000, 3000)
MAX_PROMPT_LENGTH = 280


class CoverArtGenerator:
    """
    Generates cover art with EXACT 3000×3000 output.
    Never upscales beyond 3000px - pads with brand color instead.
    Always exports PNG with sRGB color space.
    """
    
    def __init__(self):
        self.assets_dir = Path("assets/covers")
        self.assets_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_cover(
        self,
        track_title: str,
        artist_name: str,
        output_path: Path,
        cover_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate cover art with EXACT 3000×3000 dimensions.
        
        Args:
            track_title: Track name (sanitized)
            artist_name: Artist name (sanitized)
            cover_prompt: Optional prompt for cover generation (max 280 chars)
            output_path: Path to save cover.png
            
        Returns:
            Dict with ok, error (if failed)
        """
        try:
            # Safety: Sanitize and validate prompt
            if cover_prompt:
                cover_prompt = sanitize_text_input(cover_prompt, max_length=MAX_PROMPT_LENGTH)
                if len(cover_prompt) > MAX_PROMPT_LENGTH:
                    logger.warning(f"Cover prompt truncated to {MAX_PROMPT_LENGTH} characters")
            
            # Sanitize text inputs
            track_title = sanitize_text_input(track_title, max_length=100)
            artist_name = sanitize_text_input(artist_name, max_length=100)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Try to load a random image from assets/covers/
            cover_files = list(self.assets_dir.glob("*.jpg")) + list(self.assets_dir.glob("*.png"))
            
            if cover_files:
                # Use random cover from assets
                base_image_path = random.choice(cover_files)
                logger.info(f"Using base cover: {base_image_path.name}")
                img = Image.open(base_image_path)
            else:
                # Generate simple gradient if no covers available
                logger.info("No cover assets found, generating gradient")
                img = self._generate_gradient((2000, 2000))  # Start smaller, will be padded
            
            # Resize/pad to EXACTLY 3000×3000
            img = self._resize_and_pad_to_exact_size(img, TARGET_SIZE)
            
            # Add text overlay
            img_with_text = self._add_text_overlay(
                img,
                track_title,
                artist_name
            )
            
            # Ensure sRGB color space and save as PNG
            if img_with_text.mode != 'RGB':
                img_with_text = img_with_text.convert('RGB')
            
            # Save as PNG
            img_with_text.save(output_path, "PNG", optimize=True)
            logger.info(f"Cover saved to {output_path}")
            
            # Verify file exists
            if not output_path.exists():
                raise FileNotFoundError(f"Cover file was not created at {output_path}")
            
            return {
                "ok": True
            }
            
        except Exception as e:
            logger.error(f"Cover generation failed: {e}")
            return {
                "ok": False,
                "error": str(e)
            }
    
    def _resize_and_pad_to_exact_size(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """
        Resize image to fit within target size, then pad to exact dimensions.
        Never upscales beyond target size - pads with brand color instead.
        
        Args:
            img: Input image
            target_size: Target (width, height) tuple
            
        Returns:
            Image exactly matching target_size
        """
        target_width, target_height = target_size
        img_width, img_height = img.size
        
        # Calculate scaling to fit within target (never upscale beyond target)
        scale_w = target_width / img_width
        scale_h = target_height / img_height
        scale = min(scale_w, scale_h, 1.0)  # Never scale > 1.0 (no upscaling beyond target)
        
        # Resize
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create new image with brand color background
        img_final = Image.new('RGB', target_size, BRAND_COLOR)
        
        # Center the resized image
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        img_final.paste(img_resized, (x_offset, y_offset))
        
        return img_final
    
    def _generate_gradient(self, size: tuple) -> Image.Image:
        """Generate a simple gradient background."""
        width, height = size
        img = Image.new('RGB', size)
        draw = ImageDraw.Draw(img)
        
        # Random gradient colors (dark theme)
        gradients = [
            ((30, 20, 50), (90, 60, 130)),  # Purple
            ((50, 20, 30), (150, 60, 80)),  # Crimson
            ((20, 40, 50), (60, 100, 130))  # Cyan
        ]
        
        color1, color2 = random.choice(gradients)
        
        # Draw gradient
        for y in range(height):
            ratio = y / height
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        return img
    
    def _add_text_overlay(
        self,
        img: Image.Image,
        track_title: str,
        artist_name: str
    ) -> Image.Image:
        """Add text overlay with semi-transparent background."""
        # Create a copy to work with
        img_copy = img.copy().convert('RGBA')
        
        # Create semi-transparent overlay
        overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        width, height = img_copy.size
        
        # Add dark rectangle for text background
        rect_height = int(height * 0.3)
        rect_top = int(height * 0.35)
        draw.rectangle(
            [(0, rect_top), (width, rect_top + rect_height)],
            fill=(0, 0, 0, 180)
        )
        
        # Composite overlay
        img_copy = Image.alpha_composite(img_copy, overlay)
        draw = ImageDraw.Draw(img_copy)
        
        # Load fonts (use default if system fonts unavailable)
        try:
            # Try to use larger fonts for 3000px image
            title_font_size = int(height * 0.07)  # ~210px for 3000px
            artist_font_size = int(height * 0.045)  # ~135px for 3000px
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_font_size)
            artist_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", artist_font_size)
        except:
            logger.warning("System fonts not found, using default")
            title_font = ImageFont.load_default()
            artist_font = ImageFont.load_default()
        
        # Draw text (centered)
        title_bbox = draw.textbbox((0, 0), track_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) / 2
        title_y = height * 0.42
        
        artist_bbox = draw.textbbox((0, 0), artist_name, font=artist_font)
        artist_width = artist_bbox[2] - artist_bbox[0]
        artist_x = (width - artist_width) / 2
        artist_y = height * 0.52
        
        # Draw with outline for better visibility
        outline_color = (0, 0, 0, 255)
        text_color = (255, 255, 255, 255)
        
        # Outline
        for offset in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            draw.text((title_x + offset[0], title_y + offset[1]), track_title, font=title_font, fill=outline_color)
            draw.text((artist_x + offset[0], artist_y + offset[1]), artist_name, font=artist_font, fill=outline_color)
        
        # Main text
        draw.text((title_x, title_y), track_title, font=title_font, fill=text_color)
        draw.text((artist_x, artist_y), artist_name, font=artist_font, fill=text_color)
        
        return img_copy.convert('RGB')

