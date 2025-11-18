"""
Release utilities for filename sanitization and safe text handling.
"""

import re
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use in filenames.
    
    Rules:
    - Strip special characters
    - Convert spaces to underscores
    - Lowercase
    - Remove trailing dots
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized filename-safe string
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces with underscores
    text = text.replace(" ", "_")
    
    # Remove special characters (keep alphanumeric, underscores, hyphens)
    text = re.sub(r'[^a-z0-9_-]', '', text)
    
    # Remove trailing dots
    text = text.rstrip('.')
    
    # Remove multiple consecutive underscores
    text = re.sub(r'_+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    return text


def sanitize_text_input(text: str, max_length: int = 280) -> str:
    """
    Sanitize text input for safe use in prompts and metadata.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Text truncated to {max_length} characters")
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Replace unsafe characters
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    
    return text.strip()

