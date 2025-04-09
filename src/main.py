#!/usr/bin/env python3
import argparse
import yaml
import os
import json
import sys
import asyncio
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
    from .logging_config import get_logger, log_async_start, log_async_complete
    from .agents import (
        Agent,
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator,
        TitleSelector
    )
    from .resume_parser import parse_resume_file
except ImportError:
    # Fall back to absolute import (when run as a script)
    from config import load_dotenv
    from logging_config import get_logger, log_async_start, log_async_complete
    from agents import (
        Agent,
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator,
        TitleSelector
    )
    from resume_parser import parse_resume_file

# Get logger for this module
logger = get_logger()

class ResumeCustomizer:
    """Orchestrates the resume customization workflow using multiple agents."""
    
    def __init__(self, resume_path: str, job_description_path: str, output_path: str):
        """
        Initialize the resume customizer with paths to the resume, job description, and output file.
        
        Args:
            resume_path (str): Path to the resume file (YAML)
            job_description_path (str): Path to the job description file (TXT)
            output_path (str): Path to save the customized resume
        """
        # Set up logger
        self.logger = get_logger(self.__class__.__name__)
        
        # Store paths
        self.resume_path = resume_path
        self.job_description_path = job_description_path
        self.output_path = output_path
        
        # Load resume and job description
        self.state = {}
        self._load_resume()
        self._load_job_description()
        
        # Initialize agents
        self.company_researcher = CompanyResearcher()
        self.group_selector = GroupSelector()
        self.sentence_constructor = SentenceConstructor()
        self.sentence_reviewer = SentenceReviewer()
        self.content_reviewer = ContentReviewer()
        self.summary_generator = SummaryGenerator()
        self.title_selector = TitleSelector()
        
        # Add workflow step method from Agent base class
        self.workflow_step = lambda step_num, total_steps, message: self.logger.info(f"[{step_num}/{total_steps}] {message}")
        self.progress_update = lambda current, total, operation: self.logger.info(f"{operation}... ({current}/{total} complete)") if current == 1 or current == total or current % max(1, (total // 4)) == 0 else self.logger.debug(f"{operation}... ({current}/{total} complete)")
    
    def _load_resume(self):
        with open(self.resume_path, 'r') as f:
            self.resume_data = yaml.safe_load(f)
    
    def _load_job_description(self):
        with open(self.job_description_path, 'r') as f:
            self.job_description = f.read()
        
        # Initialize the state for the workflow
        self.state = {
            "resume_data": self.resume_data,
            "job_description": self.job_description,
            "enriched_job_description": "",
            "selected_roles": [],
            "constructed_sentences": {},
            "constructed_project_sentences": {},
            "final_resume": {}
        }
    
    async def run(self):
        """Run the resume customization workflow."""
        log_async_start(self.logger, "run")
        
        total_steps = 6
        
        # Step 1: Enrich job description
        self.workflow_step(1, total_steps, "Researching company information")
        self.state["enriched_job_description"] = await self.company_researcher.run(self.state["job_description"])
        
        # Do group selection first for all roles and projects
        self.logger.info("Pre-selecting all relevant groups before processing...")
        selected_groups_data = []
        
        # Store selected groups to avoid duplicate selection
        self.state["selected_role_groups"] = {}
        self.state["selected_project_groups"] = {}
        
        # Select groups for work experiences
        for role_index, role in enumerate(self.state["resume_data"]["work"]):
            selected_role_groups = self.group_selector.run(
                role["responsibilities_and_accomplishments"],
                self.state["enriched_job_description"]
            )
            self.state["selected_role_groups"][role_index] = selected_role_groups
            for group_name in selected_role_groups:
                group_data = role["responsibilities_and_accomplishments"][group_name]
                selected_groups_data.append(group_data)
        
        # Select groups for projects if they exist
        if "projects" in self.state["resume_data"] and self.state["resume_data"]["projects"]:
            for project_index, project in enumerate(self.state["resume_data"]["projects"]):
                selected_project_groups = self.group_selector.run(
                    project["responsibilities_and_accomplishments"],
                    self.state["enriched_job_description"]
                )
                self.state["selected_project_groups"][project_index] = selected_project_groups
                for group_name in selected_project_groups:
                    group_data = project["responsibilities_and_accomplishments"][group_name]
                    selected_groups_data.append(group_data)
        
        # Plan action verbs for only selected groups
        self.logger.info(f"Planning action verbs for {len(selected_groups_data)} selected groups...")
        self.state["planned_action_verbs"] = self.sentence_constructor.plan_action_verbs(selected_groups_data, self.state["enriched_job_description"])
        
        # Step 2: Process resume experiences
        self.workflow_step(2, total_steps, "Processing resume experiences")
        self.state["constructed_sentences"] = {}
        
        # Process all roles concurrently
        role_tasks = []
        for role_index in range(len(self.state["resume_data"]["work"])):
            role_tasks.append(self._process_role(role_index))
        
        # Log progress for roles
        total_items = len(role_tasks)
        self.logger.info(f"Processing {total_items} work experiences...")
        
        role_results = await asyncio.gather(*role_tasks)
        
        # Add role results to state
        for role_index, role_data in enumerate(role_results):
            self.state["constructed_sentences"][role_index] = role_data
            
        # Step 3: Process projects if they exist
        self.workflow_step(3, total_steps, "Processing projects")
        if "projects" in self.state["resume_data"] and self.state["resume_data"]["projects"]:
            self.state["constructed_project_sentences"] = {}
            
            # Process all projects concurrently
            project_tasks = []
            for project_index in range(len(self.state["resume_data"]["projects"])):
                project_tasks.append(self._process_project(project_index))
            
            # Log progress for projects
            total_projects = len(project_tasks)
            self.logger.info(f"Processing {total_projects} projects...")
            
            project_results = await asyncio.gather(*project_tasks)
            
            # Add project results to state
            for project_index, project_data in enumerate(project_results):
                self.state["constructed_project_sentences"][project_index] = project_data
        else:
            self.logger.info("No projects to process")
        
        # Step 4: Review overall content for relevance and narrative
        self.workflow_step(4, total_steps, "Reviewing overall resume content")
        self.state["content_review"] = self.content_reviewer.run(
            self.state["constructed_sentences"],
            self.state["enriched_job_description"]
        )
        
        # Step 5: Generate resume summary
        self.workflow_step(5, total_steps, "Generating tailored resume summary")
        self.state["resume_summary"] = self.summary_generator.run(
            self.state["constructed_sentences"],
            self.state["enriched_job_description"]
        )
        
        # Step 6: Assemble final resume
        self.workflow_step(6, total_steps, "Assembling and saving final resume")
        self.state["final_resume"] = self._assemble_markdown_resume()
        
        # Save the final resume
        with open(self.output_path, 'w') as f:
            f.write(self.state["final_resume"])
        
        self.logger.info(f"Resume customization complete!")
        self.logger.info(f"Markdown version saved to {self.output_path}")
        
        log_async_complete(self.logger, "run")
        return self.state["final_resume"]

    async def _process_role(self, role_index):
        """Process a single role concurrently."""
        func_name = f"_process_role({role_index})"
        log_async_start(self.logger, func_name)
        
        role = self.state["resume_data"]["work"][role_index]
        company_name = role["company"]
        if isinstance(company_name, list):
            company_name = company_name[0]
            
        self.logger.debug(f"Processing role at {company_name}")
        
        # Use the pre-selected groups instead of selecting again
        selected_groups = self.state["selected_role_groups"][role_index]
        
        # Step 2: Construct and review sentences for each selected group
        self.logger.debug(f"Selected {len(selected_groups)} groups for {company_name}")
        
        # Process multiple sentences concurrently
        sentence_tasks = []
        for group_name in selected_groups:
            sentence_tasks.append(self._process_sentence(role, group_name))
        
        sentence_results = await asyncio.gather(*sentence_tasks)
        
        # Combine results
        role_sentences = {}
        for group_name, sentence in zip(selected_groups, sentence_results):
            role_sentences[group_name] = sentence
        
        # Now that we have all the sentences, select the most relevant title
        self.logger.debug(f"Selecting title for {company_name}")
        selected_title = await self.title_selector.run(role, self.state["enriched_job_description"])
        
        result = {
            "title": selected_title,
            "company": role["company"],
            "start_date": role["start_date"],
            "end_date": role["end_date"],
            "location": role["location"],
            "sentences": role_sentences
        }
        
        log_async_complete(self.logger, func_name)
        return result
    
    async def _process_sentence(self, role, group_name):
        """Process a single sentence concurrently."""
        # Handle both role and project data by checking for 'company' key
        identifier = role.get('company', role.get('name', 'unknown'))
        if isinstance(identifier, list):
            identifier = identifier[0]
            
        func_name = f"_process_sentence({identifier}, {group_name})"
        log_async_start(self.logger, func_name)
        
        group_data = role["responsibilities_and_accomplishments"][group_name]
        
        # Step 1: Construct sentence - only pass action verbs on first call
        constructed_sentence = await self.sentence_constructor.run(
            group_data, 
            self.state["enriched_job_description"],
            feedback=None,
            # Only pass planned_action_verbs on first sentence construction
            planned_action_verbs=self.state["planned_action_verbs"]
        )
        
        # Step 2: Review sentence
        is_approved, feedback = await self.sentence_reviewer.run(constructed_sentence)
        
        # If not approved, reconstruct the sentence
        attempts = 1
        while not is_approved and attempts < 3:
            self.logger.debug(f"Reconstructing sentence (attempt {attempts+1}/3)")
            constructed_sentence = await self.sentence_constructor.run(
                group_data, 
                self.state["enriched_job_description"],
                feedback=feedback,
                # Don't need to pass action verbs again as they're now stored in the SentenceConstructor
                planned_action_verbs=None
            )
            is_approved, feedback = await self.sentence_reviewer.run(constructed_sentence)
            attempts += 1
        
        if not is_approved:
            # Include the sentence even if not approved after 3 attempts
            self.logger.warning(f"Using imperfect sentence after 3 attempts: {feedback}")
        
        log_async_complete(self.logger, func_name)
        return constructed_sentence
    
    async def _process_project(self, project_index):
        """Process a single project concurrently."""
        func_name = f"_process_project({project_index})"
        log_async_start(self.logger, func_name)
        
        project = self.state["resume_data"]["projects"][project_index]
        
        # Use the pre-selected groups instead of selecting again
        selected_groups = self.state["selected_project_groups"][project_index]
        
        # Construct and review sentences for each selected group
        # Process multiple sentences concurrently
        sentence_tasks = []
        for group_name in selected_groups:
            sentence_tasks.append(self._process_sentence(
                project, 
                group_name
            ))
        
        sentence_results = await asyncio.gather(*sentence_tasks)
        
        # Combine results
        project_sentences = {}
        for group_name, sentence in zip(selected_groups, sentence_results):
            project_sentences[group_name] = sentence
        
        result = {
            "name": project["name"],
            "sentences": project_sentences
        }
        
        log_async_complete(self.logger, func_name)
        return result
    
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
        
        # Projects (if any)
        if self.state["constructed_project_sentences"]:
            markdown += "## Projects\n\n"
            
            for project_data in self.state["constructed_project_sentences"].values():
                markdown += f"### {project_data['name']}\n\n"
                
                # Add bullet points for each sentence
                for group_name, sentence in project_data["sentences"].items():
                    markdown += f"- {sentence}\n"
                
                markdown += "\n"

        # Education
        markdown += "## Education\n\n"
        for education in self.state["resume_data"]["education"]:
            # Create a list of available education details
            edu_details = []
            if "institution" in education:
                edu_details.append(education["institution"])
            if "degree" in education:
                edu_details.append(education["degree"])
            if "field_of_study" in education:
                edu_details.append(education["field_of_study"])
            
            # Join available details with pipe separator
            markdown += f"### {' | '.join(edu_details)}\n"
            
            # Add year of completion if available
            if "year_of_completion" in education:
                markdown += f"*{education['year_of_completion']}*\n\n"
            else:
                markdown += "\n"
        
        # Certificates
        markdown += "## Certificates\n\n"
        for certificate in self.state["resume_data"]["certificates"]:
            # Create a list of available certificate details
            cert_details = []
            if "name" in certificate:
                cert_details.append(certificate["name"])
            if "organization" in certificate:
                cert_details.append(certificate["organization"])
            
            # Join available details with pipe separator
            markdown += f"### {' | '.join(cert_details)}\n"
            
            # Add date of issue if available
            if "date_of_issue" in certificate:
                markdown += f"*{certificate['date_of_issue']}*\n\n"
            else:
                markdown += "\n"
        
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


async def check_and_create_modular_resume():
    """
    Check if a modular resume exists, and if not, ask the user to create one.
    
    Returns:
        bool: True if a modular resume exists or was created, False otherwise
    """
    # Check if resume.yaml exists
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    resume_path = os.path.join(input_dir, "resume.yaml")
    
    if os.path.isfile(resume_path):
        return True
    
    logger.warning("No modular resume file found at input/resume.yaml")
    response = input("Would you like to create a modular resume now? (Y/n): ").lower()
    
    if response in ["", "y", "yes"]:
        # First, check if the user has an existing resume in any format
        response = input("Do you have an existing resume in PDF, Word, Markdown, or other format? (Y/n): ").lower()
        
        if response in ["", "y", "yes"]:
            # Ask for the resume file
            file_path = input("Please provide the path to your resume file: ").strip()
            
            if not os.path.isfile(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Parse the resume into simple YAML format
            logger.info(f"Parsing resume file: {file_path}")
            input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
            simple_resume_path = os.path.join(input_dir, "resume_simple.yaml")
            
            parsed_data = await parse_resume_file(file_path, simple_resume_path)
            if not parsed_data:
                logger.error("Failed to parse the resume file.")
                return False
            
            logger.info(f"Resume parsed and saved to {simple_resume_path}")
        else:
            # Check if resume_simple.yaml exists, and if not, tell the user to create one
            simple_resume_path = os.path.join(input_dir, "resume_simple.yaml")
            if not os.path.isfile(simple_resume_path):
                logger.warning("No simple resume file found at input/resume_simple.yaml")
                
                # Import the provide_resume_simple_instructions function from modularize_resume
                try:
                    from src.modularize_resume import provide_resume_simple_instructions
                except ImportError:
                    try:
                        from .modularize_resume import provide_resume_simple_instructions
                    except ImportError:
                        from modularize_resume import provide_resume_simple_instructions
                
                provide_resume_simple_instructions()
                logger.info("Please create a simple resume file and run the program again.")
                return False
        
        # Import the create_modular_resume function from modularize_resume
        try:
            from src.modularize_resume import create_modular_resume
        except ImportError:
            try:
                from .modularize_resume import create_modular_resume
            except ImportError:
                from modularize_resume import create_modular_resume
        
        # Create a modular resume
        success = await create_modular_resume(simple_resume_path)
        
        if success:
            logger.info("Modular resume created successfully!")
            return True
        else:
            logger.error("Failed to create modular resume.")
            return False
    else:
        logger.info("Skipping modular resume creation.")
        return False


async def async_main():
    """
    Asynchronous main function to run the resume customization workflow.
    """
    log_async_start(logger, "async_main")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Customize a resume for a specific job")
    parser.add_argument("--resume", help="Path to the resume file", default=None)
    parser.add_argument("--job-description", help="Path to the job description file", required=True)
    parser.add_argument("--output", help="Path to save the customized resume", required=True)
    parser.add_argument("--skip-modularizer", action="store_true", help="Skip the modularizer check")
    parser.add_argument("--clear-company-cache", action="store_true", help="Clear the company research cache")
    parser.add_argument("--list-cached-companies", action="store_true", help="List all cached companies")
    args = parser.parse_args()
    
    # Check if we're just listing cached companies
    if args.list_cached_companies:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "company_research")
        if os.path.exists(cache_dir):
            companies = [f.split(".")[0] for f in os.listdir(cache_dir) if f.endswith(".json")]
            if companies:
                logger.info("Cached companies:")
                for company in sorted(companies):
                    logger.info(f"- {company}")
            else:
                logger.info("No cached companies found.")
        else:
            logger.info("No company cache exists yet.")
        log_async_complete(logger, "async_main")
        return
    
    # Check if we're clearing the company cache
    if args.clear_company_cache:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "company_research")
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f.endswith(".json"):
                    os.remove(os.path.join(cache_dir, f))
            logger.info("Company research cache cleared.")
        else:
            logger.info("No company cache exists to clear.")
        log_async_complete(logger, "async_main")
        return
    
    # Set up paths
    resume_path = args.resume
    job_description_path = args.job_description
    output_path = args.output
    
    # If resume path is not provided, use the default path
    if not resume_path:
        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
        resume_path = os.path.join(input_dir, "resume.yaml")
    
    # Check if the provided resume is not in YAML format and needs parsing
    if resume_path and not resume_path.lower().endswith(('.yaml', '.yml')):
        logger.info(f"Detected non-YAML resume format: {resume_path}")
        logger.info("Parsing resume file...")
        
        # Parse the resume into YAML format
        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
        yaml_resume_path = os.path.join(input_dir, "resume.yaml")
        
        # First convert to simple format
        simple_resume_path = os.path.join(input_dir, "resume_simple.yaml")
        parsed_data = await parse_resume_file(resume_path, simple_resume_path)
        
        if not parsed_data:
            logger.error("Failed to parse the resume file. Please provide a YAML resume file or create one first.")
            log_async_complete(logger, "async_main")
            return
        
        logger.info(f"Resume parsed and saved to {simple_resume_path}")
        
        # Now convert to modular format
        try:
            from src.modularize_resume import create_modular_resume
        except ImportError:
            try:
                from .modularize_resume import create_modular_resume
            except ImportError:
                from modularize_resume import create_modular_resume
        
        success = await create_modular_resume(simple_resume_path)
        
        if not success:
            logger.error("Failed to create modular resume from parsed file.")
            log_async_complete(logger, "async_main")
            return
        
        # Update resume path to the created YAML file
        resume_path = yaml_resume_path
    
    # Check for the modular resume if using the default path and not skipping the modularizer
    if not args.skip_modularizer and (not resume_path or resume_path == os.path.join(os.path.dirname(os.path.dirname(__file__)), "input", "resume.yaml")):
        logger.info("Checking for modular resume...")
        if not await check_and_create_modular_resume():
            logger.error("Cannot proceed without a modular resume. Please create one and try again.")
            log_async_complete(logger, "async_main")
            return
    
    # Get the job description file
    if args.job_description:
        job_description_path = args.job_description
    else:
        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
        job_description_path = os.path.join(input_dir, "job_description.txt")
    
    # Check if the job description file exists
    if not os.path.isfile(job_description_path):
        logger.error(f"Job description file not found: {job_description_path}")
        logger.error("Please provide a valid job description file with --job-description.")
        log_async_complete(logger, "async_main")
        return
    
    # Get the output file
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "customized_resume.md")
    
    # Create the resume customizer and run it
    customizer = ResumeCustomizer(resume_path, job_description_path, output_path)
    await customizer.run()
    
    log_async_complete(logger, "async_main")

def main():
    # Ensure environment variables are loaded
    load_dotenv()
    
    # Run the async main function
    asyncio.run(async_main())

if __name__ == "__main__":
    main() 