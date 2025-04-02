#!/usr/bin/env python3
"""
Logging Configuration Module

This module sets up the logging configuration for the entire application.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import inspect

# Make sure the logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Define log file path with timestamp
current_date = datetime.now().strftime("%Y-%m-%d")
log_file = os.path.join(logs_dir, f"resume_customizer_{current_date}.log")

# Configure the root logger
def configure_logging(console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Configure the application-wide logging.
    
    Args:
        console_level: Logging level for console output (default: INFO)
        file_level: Logging level for file output (default: DEBUG)
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set the root logger level to the more verbose of the two
    root_logger.setLevel(min(console_level, file_level))
    
    # Create formatters - simplified console formatter for cleaner output
    console_formatter = logging.Formatter('%(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger

# Create a logger for the application
logger = configure_logging()

def get_logger(name=None):
    """
    Get a logger with the given name. If no name is provided,
    it will use the name of the calling module.
    
    Args:
        name: Optional name for the logger (default: None)
        
    Returns:
        Logger: Configured logger
    """
    if name is None:
        # Get the name of the calling module
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        name = module.__name__ if module else "unknown"
    
    return logging.getLogger(name)

def get_class_logger(cls):
    """
    Get a logger for a class.
    
    Args:
        cls: The class to get a logger for
        
    Returns:
        Logger: Configured logger with the class name
    """
    return logging.getLogger(f"{cls.__module__}.{cls.__name__}")

def log_async_start(logger, func_name):
    """Log the start of an async function execution with proper formatting"""
    logger.debug(f"Starting async function: {func_name}")

def log_async_complete(logger, func_name):
    """Log the completion of an async function execution with proper formatting"""
    logger.debug(f"Completed async function: {func_name}")

# Export needed functions
__all__ = ['configure_logging', 'get_logger', 'get_class_logger', 
           'log_async_start', 'log_async_complete', 'logger'] 