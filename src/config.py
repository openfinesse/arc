#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# Check if API keys are set
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set in the environment.")
    print("Some functionality will be limited.")

if not TAVILY_API_KEY:
    print("Warning: TAVILY_API_KEY is not set in the environment.")
    print("Company research capabilities will be limited.")

# Model configuration
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# Other configurations
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30")) 