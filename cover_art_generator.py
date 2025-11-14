"""
Local Cover Art Generator for Label-in-a-Box Production Demo
NO external APIs - uses local Pillow generation only
"""

import os
import logging
import random
from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class CoverArtGenerator:
    """
    Generates cover art locally using Pillow.
    Sources: random image from assets/covers/ OR simple gradient canvas.
    """
    
    def __init__(self):
        self.assets_dir = Path("assets/covers")
        self.assets_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_local_cover(
        self,
        track_title: str,
        artist_name: str,
        session_dir: Path
    ) -> Dict:
        """
        Generate cover art locally with Pillow.
        
        Args:
            track_title: Track name
            artist_name: Artist name
            session_dir: Session directory to save output
            
        Returns:
            Dict with ok, url
        """
        try:
            output_path = session_dir / "cover.jpg"
            
            # Try to load a random image from assets/covers/
            cover_files = list(self.assets_dir.glob("*.jpg")) + list(self.assets_dir.glob("*.png"))
            
            if cover_files:
                # Use random cover from assets
                base_image_path = random.choice(cover_files)
                logger.info(f"Using base cover: {base_image_path.name}")
                img = Image.open(base_image_path)
                img = img.resize((1000, 1000))
            else:
                # Generate simple gradient if no covers available
                logger.info("No cover assets found, generating gradient")
                img = self._generate_gradient((1000, 1000))
            
            # Add text overlay
            img_with_text = self._add_text_overlay(
                img,
                track_title,
                artist_name
            )
            
            # Save
            img_with_text.save(output_path, "JPEG", quality=90)
            logger.info(f"Cover saved to {output_path}")
            
            return {
                "ok": True,
                "url": f"/media/{session_dir.name}/cover.jpg"
            }
            
        except Exception as e:
            logger.error(f"Cover generation failed: {e}")
            return {
                "ok": False,
                "error": str(e)
            }
    
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
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
            artist_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
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


def get_cover_art_generator() -> CoverArtGenerator:
    """Factory function."""
    return CoverArtGenerator()
