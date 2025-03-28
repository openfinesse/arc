#!/usr/bin/env python3
"""
Entrypoint script for the Resume Customizer.
This script sets up the Python path and runs the main module.
"""

import os
import sys
import argparse

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from our package
from src.main import main

if __name__ == "__main__":
    main() 