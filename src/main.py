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
        """Execute the complete resume customization workflow."""
        log_async_start(self.logger, "run")
        
        # Define the total number of steps in our workflow
        total_steps = 6
        
        # Step 1: Research company and enrich job description
        self.workflow_step(1, total_steps, "Researching company information")
        self.state["enriched_job_description"] = await self.company_researcher.run(self.state["job_description"])
        
        # Step 2: Process resume content
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
        
        # Step 1: Select relevant groups for this role
        selected_groups = self.group_selector.run(
            role["responsibilities_and_accomplishments"],
            self.state["enriched_job_description"]
        )
        
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
        
        # Pre-plan action verbs if needed
        # Keep this synchronous as per requirements
        if not self.sentence_constructor.assigned_action_verbs:
            self.logger.debug("Planning action verbs for all sentences...")
            all_group_data = []
            for role in self.state["resume_data"]["work"]:
                for group_key, group in role["responsibilities_and_accomplishments"].items():
                    all_group_data.append(group)
            # Add project group data if processing projects
            if "projects" in self.state["resume_data"]:
                for project in self.state["resume_data"]["projects"]:
                    for group_key, group in project["responsibilities_and_accomplishments"].items():
                        all_group_data.append(group)
            self.sentence_constructor.plan_action_verbs(all_group_data, self.state["enriched_job_description"])
        
        # Step 1: Construct sentence
        constructed_sentence = await self.sentence_constructor.run(
            group_data, 
            self.state["enriched_job_description"]
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
                feedback
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
        
        # Select relevant groups for this project
        selected_groups = self.group_selector.run(
            project["responsibilities_and_accomplishments"],
            self.state["enriched_job_description"]
        )
        
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


async def check_and_create_modular_resume():
    """
    Check if resume.yaml exists, and run the modularizer if needed.
    
    Returns:
        bool: True if resume.yaml exists or was created, False otherwise
    """
    log_async_start(logger, "check_and_create_modular_resume")
    
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    resume_path = os.path.join(input_dir, "resume.yaml")
    
    if os.path.isfile(resume_path):
        log_async_complete(logger, "check_and_create_modular_resume")
        return True
    
    logger.info("No modular resume file (resume.yaml) found.")
    logger.info("Running resume modularizer to create one...")
    
    # Run modularize_resume.py
    modularizer_path = os.path.join(os.path.dirname(__file__), "modularize_resume.py")
    
    try:
        subprocess.run([sys.executable, modularizer_path], check=True)
        
        # Check if resume.yaml was created
        if os.path.isfile(resume_path):
            log_async_complete(logger, "check_and_create_modular_resume")
            return True
        else:
            logger.error("Failed to create modular resume file.")
            log_async_complete(logger, "check_and_create_modular_resume")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"Error running resume modularizer: {e}")
        log_async_complete(logger, "check_and_create_modular_resume")
        return False


async def async_main():
    log_async_start(logger, "async_main")
    
    parser = argparse.ArgumentParser(description="Customize a resume for a specific job")
    parser.add_argument("--resume", help="Path to the resume YAML file")
    parser.add_argument("--job-description", required=False, help="Path to the job description file")
    parser.add_argument("--output", required=False, help="Path to save the customized resume")
    parser.add_argument("--skip-modularizer", action="store_true", help="Skip resume modularizer check")
    parser.add_argument("--clear-company-cache", action="store_true", help="Clear the cached company research data")
    parser.add_argument("--list-cached-companies", action="store_true", help="List all companies in the research cache")
    args = parser.parse_args()
    
    # Handle company cache commands
    if args.clear_company_cache or args.list_cached_companies:
        from agents import CompanyResearcher
        researcher = CompanyResearcher()
        
        if args.clear_company_cache:
            researcher.clear_cache()
            logger.info("Company research cache cleared.")
            log_async_complete(logger, "async_main")
            return
        
        if args.list_cached_companies:
            companies = researcher.list_cached_companies()
            if companies:
                logger.info("Cached company research data:")
                for company in companies:
                    logger.info(f" - {company}")
            else:
                logger.info("No cached company research data found.")
            log_async_complete(logger, "async_main")
            return
    
    # Get the resume file
    if args.resume:
        resume_path = args.resume
    else:
        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
        resume_path = os.path.join(input_dir, "resume.yaml")
        
        # Check if resume.yaml needs to be created
        if not args.skip_modularizer and not os.path.isfile(resume_path):
            success = await check_and_create_modular_resume()
            if not success:
                logger.error("Could not find or create a modular resume file.")
                logger.error("Please provide a valid resume file with --resume or create one manually.")
                log_async_complete(logger, "async_main")
                return
    
    # Check if the resume file exists
    if not os.path.isfile(resume_path):
        logger.error(f"Resume file not found: {resume_path}")
        logger.error("Please provide a valid resume file with --resume.")
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