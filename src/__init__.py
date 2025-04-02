"""
Resume Customizer Package

This package contains the resume customization workflow implementation.
"""

# Import and configure logging
from .logging_config import configure_logging, get_logger

# Configure the root logger
logger = configure_logging()

# Export the logger
__all__ = ['logger'] 