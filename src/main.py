#!/usr/bin/env python3
import argparse
import yaml
import os
import json
import sys
from typing import Dict, List, Any
import subprocess

# Add the src directory to the path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import config to ensure environment variables are loaded
try:
    # Try relative import (when used as a module)
    from .config import load_dotenv
    from .agents import (
        Agent,
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator
    )
except ImportError:
    # Fall back to absolute import (when run as a script)
    from config import load_dotenv
    from agents import (
        Agent,
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator
    )

class ResumeCustomizer:
    """Orchestrates the resume customization workflow using multiple agents."""
    
    def __init__(self, resume_path: str, job_description_path: str, output_path: str):
        self.resume_path = resume_path
        self.job_description_path = job_description_path
        self.output_path = output_path
        
        # Load resume data
        with open(resume_path, 'r') as f:
            self.resume_data = yaml.safe_load(f)
            
        # Load job description
        with open(job_description_path, 'r') as f:
            self.job_description = f.read()
            
        # Initialize the state for the workflow
        self.state = {
            "resume_data": self.resume_data,
            "job_description": self.job_description,
            "enriched_job_description": "",
            "selected_roles": [],
            "constructed_sentences": {},
            "final_resume": {}
        }
        
        # Initialize agents
        # Each agent will automatically get API keys from environment variables
        self.company_researcher = CompanyResearcher()
        # self.role_selector = RoleSelector()
        self.group_selector = GroupSelector()
        self.sentence_constructor = SentenceConstructor()
        self.sentence_reviewer = SentenceReviewer()
        self.content_reviewer = ContentReviewer()
        self.summary_generator = SummaryGenerator()
    
    def run(self):
        """Execute the complete resume customization workflow."""
        print("Starting resume customization workflow...")
        
        # Step 1: Research company and enrich job description
        print("Step 1: Researching company and enriching job description...")
        self.state["enriched_job_description"] = self.company_researcher.run(self.state["job_description"])
        
        # Step 2: Select relevant roles from resume
        # print("Step 2: Selecting relevant roles...")
        # self.state["selected_roles"] = self.role_selector.run(
        #     self.state["resume_data"]["work"],
        #     self.state["enriched_job_description"]
        # )
        
        # Step 3-4: For each role, select groups and construct sentences
        print("Step 3-4: Selecting groups and constructing sentences...")
        self.state["constructed_sentences"] = {}
        
        for role_index in range(len(self.state["resume_data"]["work"])):
            role = self.state["resume_data"]["work"][role_index]
            
            # Step 3: Select relevant groups for this role
            selected_groups = self.group_selector.run(
                role["responsibilities_and_accomplishments"],
                self.state["enriched_job_description"]
            )
            
            # Step 4a and 4b: Construct and review sentences for each selected group
            role_sentences = {}
            for group_name in selected_groups:
                group_data = role["responsibilities_and_accomplishments"][group_name]
                
                # Step 4a: Construct sentence
                constructed_sentence = self.sentence_constructor.run(
                    group_data, 
                    self.state["enriched_job_description"]
                )
                
                # Step 4b: Review sentence
                is_approved, feedback = self.sentence_reviewer.run(constructed_sentence)
                
                # If not approved, reconstruct the sentence
                attempts = 1
                while not is_approved and attempts < 3:
                    constructed_sentence = self.sentence_constructor.run(
                        group_data, 
                        self.state["enriched_job_description"],
                        feedback
                    )
                    is_approved, feedback = self.sentence_reviewer.run(constructed_sentence)
                    attempts += 1
                
                if is_approved:
                    role_sentences[group_name] = constructed_sentence
            
            # Add the constructed sentences for this role
            title_index = role_index  # We'll use the same index for simplicity
            self.state["constructed_sentences"][title_index] = {
                "title": role["title_variables"][0],  # Default to first title variation for now
                "company": role["company"],
                "start_date": role["start_date"],
                "end_date": role["end_date"],
                "location": role["location"],
                "sentences": role_sentences
            }
        
        # Step 5: Review overall content for relevance and narrative
        print("Step 5: Reviewing overall content...")
        self.state["content_review"] = self.content_reviewer.run(
            self.state["constructed_sentences"],
            self.state["enriched_job_description"]
        )
        
        # Step 6: Generate resume summary
        print("Step 6: Generating resume summary...")
        self.state["resume_summary"] = self.summary_generator.run(
            self.state["constructed_sentences"],
            self.state["enriched_job_description"]
        )
        
        # Assemble final resume in Markdown format
        self.state["final_resume"] = self._assemble_markdown_resume()
        
        # Save the final resume
        with open(self.output_path, 'w') as f:
            f.write(self.state["final_resume"])
        
        print(f"Resume customization complete!")
        print(f"Markdown version saved to {self.output_path}")
        
        return self.state["final_resume"]
    
    def _assemble_markdown_resume(self) -> str:
        """Create the final Markdown resume from the processed data."""
        basics = self.state["resume_data"]["basics"]
        
        # Start with the resume header
        markdown = f"# {basics['name']}\n\n"
        
        # Contact information
        contact_info = []
        if "email" in basics:
            contact_info.append(f"{basics['email']}")
        if "phone" in basics:
            contact_info.append(f"{basics['phone']}")
        if "location" in basics and "city" in basics["location"] and "province" in basics["location"]:
            contact_info.append(f"{basics['location']['city']}, {basics['location']['province']}")
        if "linkedin" in basics:
            contact_info.append(f"[LinkedIn]({basics['linkedin']})")
            
        markdown += " | ".join(contact_info) + "\n\n"
        
        # Summary
        markdown += "## Summary\n\n"
        markdown += self.state["resume_summary"] + "\n\n"
        
        # Experience
        markdown += "## Experience\n\n"
        
        # Sort roles by start_date (assuming format like "Mar 2023")
        sorted_roles = sorted(
            self.state["constructed_sentences"].values(),
            key=lambda x: self._parse_date(x["start_date"]),
            reverse=True
        )
        
        for role in sorted_roles:
            markdown += f"### {role['title']} | {role['company']}\n"
            markdown += f"*{role['start_date']} - {role['end_date']}* | {role['location']}\n\n"
            
            # Add bullet points for each sentence
            for group_name, sentence in role["sentences"].items():
                markdown += f"- {sentence}\n"
            
            markdown += "\n"

        # Education
        markdown += "## Education\n\n"
        for education in self.state["resume_data"]["education"]:
            markdown += f"### {education['institution']} | {education['degree']} | {education['field_of_study']}\n"
            markdown += f"*{education['year_of_completion']}*\n\n"
        
        # Certificates
        markdown += "## Certificates\n\n"
        for certificate in self.state["resume_data"]["certificates"]:
            markdown += f"### {certificate['name']} | {certificate['organization']}\n"
            markdown += f"*{certificate['date_of_issue']}*\n\n"
        
        return markdown
    
    def _parse_date(self, date_str: str) -> tuple:
        """Simple date parser to help with sorting. Returns a tuple of (year, month_index)."""
        months = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        
        parts = date_str.split()
        if len(parts) == 2 and parts[0] in months and parts[1].isdigit():
            return (int(parts[1]), months[parts[0]])
        return (0, 0)  # Default for unparseable dates


def check_and_create_modular_resume():
    """
    Check if resume.yaml exists, and run the modularizer if needed.
    
    Returns:
        bool: True if resume.yaml exists or was created, False otherwise
    """
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    resume_path = os.path.join(input_dir, "resume.yaml")
    
    if os.path.isfile(resume_path):
        return True
    
    print("No modular resume file (resume.yaml) found.")
    print("Running resume modularizer to create one...")
    
    # Run modularize_resume.py
    modularizer_path = os.path.join(os.path.dirname(__file__), "modularize_resume.py")
    
    try:
        subprocess.run([sys.executable, modularizer_path], check=True)
        
        # Check if resume.yaml was created
        if os.path.isfile(resume_path):
            return True
        else:
            print("Failed to create modular resume file.")
            return False
    except subprocess.SubprocessError as e:
        print(f"Error running resume modularizer: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Customize a resume for a specific job")
    parser.add_argument("--resume", help="Path to the resume YAML file")
    parser.add_argument("--job-description", required=True, help="Path to the job description file")
    parser.add_argument("--output", required=True, help="Path to save the customized resume")
    parser.add_argument("--skip-modularizer", action="store_true", help="Skip resume modularizer check")
    args = parser.parse_args()
    
    # Check for resume.yaml if not specified
    if not args.resume:
        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
        default_resume_path = os.path.join(input_dir, "resume.yaml")
        
        if not args.skip_modularizer and not os.path.isfile(default_resume_path):
            # Run the modularizer to create resume.yaml
            if not check_and_create_modular_resume():
                print("Unable to find or create resume.yaml. Please provide a resume file with --resume.")
                sys.exit(1)
        
        args.resume = default_resume_path
    
    # Check if the resume file exists
    if not os.path.isfile(args.resume):
        print(f"Resume file not found: {args.resume}")
        sys.exit(1)
    
    # Check if the job description file exists
    if not os.path.isfile(args.job_description):
        print(f"Job description file not found: {args.job_description}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run the resume customizer
    customizer = ResumeCustomizer(args.resume, args.job_description, args.output)
    customizer.run()


if __name__ == "__main__":
    # Ensure environment variables are loaded
    load_dotenv()
    main() 