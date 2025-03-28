#!/usr/bin/env python3
"""
Entry point for the resume customizer when run as a module.
Example: python -m src --resume resume.yaml --job-description job.txt --output resume.md
"""

import os
import sys

# Add the parent directory to the path so we can import the main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from main.py
from src.main import main

if __name__ == "__main__":
    main() 