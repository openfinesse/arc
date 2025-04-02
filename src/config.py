#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This will NOT overwrite existing environment variables by default
# We need to set override=True to make .env take precedence
load_dotenv(override=True)

# Import logging after env is loaded but before checking keys
from logging_config import get_logger

# Get a logger for this module
logger = get_logger()

# Export load_dotenv for other modules to use
__all__ = ['load_dotenv', 'OPENAI_API_KEY', 'TAVILY_API_KEY', 'ANTHROPIC_API_KEY', 'PERPLEXITY_API_KEY', 'RESEARCH_API_PROVIDER', 'MAX_RETRIES', 'REQUEST_TIMEOUT']

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

# API Provider Configuration
# Possible values: "tavily" or "perplexity"
RESEARCH_API_PROVIDER = os.environ.get("RESEARCH_API_PROVIDER", "perplexity").lower()

# Check if API keys are set
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set in the environment.")
    logger.warning("Some functionality will be limited.")

if RESEARCH_API_PROVIDER == "tavily" and not TAVILY_API_KEY:
    logger.warning("TAVILY_API_KEY is not set in the environment.")
    logger.warning("Company research capabilities will be limited.")

if RESEARCH_API_PROVIDER == "perplexity" and not PERPLEXITY_API_KEY:
    logger.warning("PERPLEXITY_API_KEY is not set in the environment.")
    logger.warning("Company research capabilities will be limited.")

# Other configurations
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30")) 