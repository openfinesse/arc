#!/usr/bin/env python3
"""
Resume Modularization Script

This script converts a simple resume format into a modular format that can be customized
for different job applications.
"""

import os
import sys
import yaml
from typing import Optional
import argparse

from agents import ResumeModularizer

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
        print(f"File not found: {user_input}")
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

def create_modular_resume(simple_resume_path: str) -> bool:
    """
    Create a modular resume from a simple resume file.
    
    Args:
        simple_resume_path (str): Path to the simple resume file
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create the resume modularizer agent
    modularizer = ResumeModularizer()
    
    # Process the resume
    modular_resume = modularizer.process_resume(simple_resume_path)
    
    if not modular_resume:
        print("Error processing the resume.")
        return False
    
    # Save the modular resume
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    output_path = os.path.join(input_dir, "resume.yaml")
    
    return modularizer.save_modular_resume(modular_resume, output_path)

def provide_resume_simple_instructions():
    """
    Provide instructions for creating a resume_simple.yaml file.
    """
    print("\nTo create a simple resume file for modularization:")
    print("1. Create a file named 'resume_simple.yaml' in the 'input' directory.")
    print("2. Follow this structure for your file:")
    print("""
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
    """)
    print("\nOnce you've created this file, run this script again to convert it to a modular format.")

def main():
    """
    Main function to handle the resume modularization process.
    """
    parser = argparse.ArgumentParser(description="Convert a simple resume to a modular format")
    parser.add_argument("--simple", help="Path to the simple resume file", default=None)
    parser.add_argument("--force", action="store_true", help="Force processing even if resume.yaml exists")
    args = parser.parse_args()
    
    # Check if resume.yaml exists and handle accordingly
    if check_resume_yaml_exists() and not args.force:
        print("A modular resume file (resume.yaml) already exists.")
        response = input("Would you like to create a new modular resume? (y/N): ").strip().lower()
        
        if response not in ("y", "yes"):
            print("Exiting without making changes.")
            return
    
    # If simple resume path was provided via command line, use it
    if args.simple and os.path.isfile(args.simple):
        simple_resume_path = args.simple
    else:
        # Check if resume_simple.yaml exists
        if check_resume_simple_yaml_exists():
            input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
            default_simple_path = os.path.join(input_dir, "resume_simple.yaml")
        else:
            default_simple_path = None
        
        # Ask if a modular resume file is available
        response = input("Do you have a simple resume file available? (Y/n): ").strip().lower()
        
        if response in ("", "y", "yes"):
            simple_resume_path = get_input_path(
                "Please provide the path to your simple resume file",
                default_simple_path
            )
            
            if not simple_resume_path:
                print("No valid simple resume file provided. Exiting.")
                return
        else:
            # Ask if they want to create a modular version
            response = input("Would you like to create a modular version of your resume? (Y/n): ").strip().lower()
            
            if response in ("", "y", "yes"):
                # Check if resume_simple.yaml exists
                if check_resume_simple_yaml_exists():
                    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
                    simple_resume_path = os.path.join(input_dir, "resume_simple.yaml")
                    print(f"Found simple resume file at: {simple_resume_path}")
                else:
                    # Provide instructions for creating a simple resume file
                    print("No simple resume file found.")
                    provide_resume_simple_instructions()
                    return
            else:
                print("Exiting without making changes.")
                return
    
    # Create the modular resume
    success = create_modular_resume(simple_resume_path)
    
    if success:
        print("\nModular resume created successfully!")
        print("You can now use this modular resume with the main application for job-specific customization.")
    else:
        print("\nFailed to create modular resume. Please check the logs for errors.")

if __name__ == "__main__":
    main() 