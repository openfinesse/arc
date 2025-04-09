#!/usr/bin/env python3
"""
Resume Modularization Script

This script converts a simple resume format into a modular format that can be customized
for different job applications.
"""

import os
import sys
import yaml
import asyncio
from typing import Optional
import argparse

try:
    # Try relative import
    from .logging_config import get_logger, log_async_start, log_async_complete
    from .agents import ResumeModularizer
    from .resume_parser import ResumeParser, parse_resume_file
except ImportError:
    # Try absolute import
    from logging_config import get_logger, log_async_start, log_async_complete
    from agents import ResumeModularizer
    from resume_parser import ResumeParser, parse_resume_file

# Get logger for this module
logger = get_logger()

def get_input_path(prompt: str, default_path: Optional[str] = None) -> Optional[str]:
    """
    Ask the user for an input file path.
    
    Args:
        prompt (str): The prompt to display to the user
        default_path (Optional[str]): Default path to suggest
        
    Returns:
        Optional[str]: The file path or None if the user wants to cancel
    """
    default_msg = f" [{default_path}]" if default_path else ""
    user_input = input(f"{prompt}{default_msg}: ").strip()
    
    if not user_input and default_path:
        return default_path
    
    if user_input.lower() in ("no", "n", "cancel", "quit", "exit"):
        return None
    
    # Validate the file exists
    if not os.path.isfile(user_input):
        logger.error(f"File not found: {user_input}")
        return get_input_path(prompt, default_path)
    
    return user_input

def check_resume_yaml_exists() -> bool:
    """
    Check if the resume.yaml file exists in the input directory.
    
    Returns:
        bool: True if resume.yaml exists, False otherwise
    """
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    return os.path.isfile(os.path.join(input_dir, "resume.yaml"))

def check_resume_simple_yaml_exists() -> bool:
    """
    Check if the resume_simple.yaml file exists in the input directory.
    
    Returns:
        bool: True if resume_simple.yaml exists, False otherwise
    """
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    return os.path.isfile(os.path.join(input_dir, "resume_simple.yaml"))

async def parse_resume(resume_path: str) -> Optional[str]:
    """
    Parse a resume file in various formats (PDF, Markdown, DOCX, etc.) into the simple YAML format.
    
    Args:
        resume_path (str): Path to the resume file
        
    Returns:
        Optional[str]: Path to the parsed YAML file or None if parsing failed
    """
    log_async_start(logger, "parse_resume")
    
    # Get output path for the parsed YAML
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    output_path = os.path.join(input_dir, "resume_simple.yaml")
    
    logger.info(f"Parsing resume file: {resume_path}")
    parsed_data = await parse_resume_file(resume_path, output_path)
    
    log_async_complete(logger, "parse_resume")
    
    if parsed_data:
        return output_path
    return None

async def create_modular_resume(simple_resume_path: str) -> bool:
    """
    Create a modular resume from a simple resume file.
    
    Args:
        simple_resume_path (str): Path to the simple resume file
        
    Returns:
        bool: True if successful, False otherwise
    """
    log_async_start(logger, "create_modular_resume")
    
    # Create the resume modularizer agent
    modularizer = ResumeModularizer()
    
    # Process the resume
    logger.info("Converting simple resume to modular format...")
    modular_resume = await modularizer.process_resume(simple_resume_path)
    
    if not modular_resume:
        logger.error("Error processing the resume.")
        log_async_complete(logger, "create_modular_resume")
        return False
    
    # Save the modular resume
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    output_path = os.path.join(input_dir, "resume.yaml")
    
    result = modularizer.save_modular_resume(modular_resume, output_path)
    log_async_complete(logger, "create_modular_resume")
    return result

def provide_resume_simple_instructions():
    """
    Provide instructions for creating a resume_simple.yaml file.
    """
    logger.info("\nTo create a simple resume file for modularization:")
    logger.info("1. Create a file named 'resume_simple.yaml' in the 'input' directory.")
    logger.info("2. Follow this structure for your file:")
    
    template = """
basics:
  name: "Your Name"
  email: "your.email@example.com"
  phone: "+1 123 456 7890"
  location: 
    city: "City"
    province: "Province"
    country: "Country"
    address: "Your Address"
    postal_code: "A1B 2C3"
  linkedin: "https://linkedin.com/in/yourusername"
  
work:
  - title_variables:
      - "Job Title 1"
      - "Alternative Job Title"
    start_date: "Jan 2022"
    end_date: "Present"
    company:
      - "Company Name"
    location: "City, Province, Country"
    responsibilities_and_accomplishments:
      - "Your first bullet point describing a responsibility or accomplishment"
      - "Your second bullet point describing another responsibility or accomplishment"

education:
  - institution: "University Name"
    degree: "Your Degree"
    field_of_study: "Your Field"
    start_date: "2016"
    year_of_completion: "2020"
    """
    
    print(template)
    logger.info("\nOnce you've created this file, run this script again to convert it to a modular format.")

async def main_async():
    """
    Async main function to handle the resume modularization process.
    """
    log_async_start(logger, "main_async")
    
    parser = argparse.ArgumentParser(description="Convert a simple resume to a modular format")
    parser.add_argument("--resume", help="Path to any resume file (PDF, DOCX, Markdown, YAML, etc.)", default=None)
    parser.add_argument("--simple", help="Path to the simple resume YAML file", default=None)
    parser.add_argument("--force", action="store_true", help="Force processing even if resume.yaml exists")
    args = parser.parse_args()
    
    # Check if resume.yaml exists and handle accordingly
    if check_resume_yaml_exists() and not args.force:
        logger.info("A modular resume file (resume.yaml) already exists.")
        response = input("Would you like to create a new modular resume? (y/N): ").strip().lower()
        
        if response not in ("y", "yes"):
            logger.info("Exiting without making changes.")
            log_async_complete(logger, "main_async")
            return
    
    # Display welcome message
    logger.info("===== Resume Modularization Tool =====")
    
    # Process any resume format if provided
    if args.resume and os.path.isfile(args.resume):
        # Parse the resume file into simple YAML format
        simple_resume_path = await parse_resume(args.resume)
        if not simple_resume_path:
            logger.error("Failed to parse the provided resume. Please try again or use a simple YAML file.")
            log_async_complete(logger, "main_async")
            return
    # If simple resume path was provided via command line, use it
    elif args.simple and os.path.isfile(args.simple):
        simple_resume_path = args.simple
    else:
        # Check if resume_simple.yaml exists
        if check_resume_simple_yaml_exists():
            input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
            default_simple_path = os.path.join(input_dir, "resume_simple.yaml")
        else:
            default_simple_path = None
        
        # Ask if any resume file is available
        response = input("Do you have a resume file available? (Y/n): ").strip().lower()
        
        if response in ("", "y", "yes"):
            resume_path = get_input_path(
                "Please provide the path to your resume file (PDF, DOCX, Markdown, YAML, etc.)",
                default_simple_path
            )
            
            if not resume_path:
                logger.error("No valid resume file provided. Exiting.")
                log_async_complete(logger, "main_async")
                return
            
            # Check if the file is already in simple YAML format or needs parsing
            if resume_path.lower().endswith(('.yaml', '.yml')) and os.path.basename(resume_path) == "resume_simple.yaml":
                simple_resume_path = resume_path
            else:
                # Parse the resume file into simple YAML format
                simple_resume_path = await parse_resume(resume_path)
                if not simple_resume_path:
                    logger.error("Failed to parse the provided resume. Please try again or use a simple YAML file.")
                    log_async_complete(logger, "main_async")
                    return
        else:
            # Ask if they want to create a modular version
            response = input("Would you like to create a modular version of your resume? (Y/n): ").strip().lower()
            
            if response in ("", "y", "yes"):
                # Check if resume_simple.yaml exists
                if check_resume_simple_yaml_exists():
                    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
                    simple_resume_path = os.path.join(input_dir, "resume_simple.yaml")
                    logger.info(f"Found simple resume file at: {simple_resume_path}")
                else:
                    # Provide instructions for creating a simple resume file
                    logger.warning("No simple resume file found.")
                    provide_resume_simple_instructions()
                    log_async_complete(logger, "main_async")
                    return
            else:
                logger.info("Exiting without making changes.")
                log_async_complete(logger, "main_async")
                return
    
    # Create the modular resume
    logger.info("Starting resume modularization process...")
    success = await create_modular_resume(simple_resume_path)
    
    if success:
        logger.info("\n✅ Modular resume created successfully!")
        logger.info("You can now use this modular resume with the main application for job-specific customization.")
    else:
        logger.error("\n❌ Failed to create modular resume. Please check the logs for errors.")
    
    log_async_complete(logger, "main_async")

def main():
    """
    Main function that sets up and runs the async event loop.
    """
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 