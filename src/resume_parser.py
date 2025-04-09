#!/usr/bin/env python3
"""
Resume Parser Module

This module handles parsing various resume formats (PDF, Markdown, etc.) and
converts them to the structured YAML format required by the resume modularizer.
"""

import os
import yaml
import re
from typing import Dict, Any, Optional, List
import asyncio
import logging

try:
    # Try relative import
    from .logging_config import get_logger
    from .agents import Agent
except ImportError:
    # Try absolute import
    from logging_config import get_logger
    try:
        from agents import Agent
    except ImportError:
        # For standalone usage
        from src.agents import Agent

# Get logger for this module
logger = get_logger()

class ResumeParser:
    """
    Parser for converting various resume formats into the structured YAML format
    required by the resume modularizer.
    """
    
    def __init__(self):
        """Initialize the resume parser."""
        self.logger = get_logger(self.__class__.__name__)
        
        # Additional dependencies will be imported only when needed
        self._pdf_parser_loaded = False
        self._markdown_parser_loaded = False
        self._docx_parser_loaded = False
        
    def _load_pdf_dependencies(self):
        """Load PDF parsing dependencies."""
        try:
            global pypdf, pdfplumber
            import pypdf
            import pdfplumber
            self._pdf_parser_loaded = True
        except ImportError:
            self.logger.error("PDF parsing dependencies not installed. Run: pip install pypdf pdfplumber")
            return False
        return True
    
    def _load_markdown_dependencies(self):
        """Load Markdown parsing dependencies."""
        try:
            global markdown
            import markdown
            self._markdown_parser_loaded = True
        except ImportError:
            self.logger.error("Markdown parsing dependencies not installed. Run: pip install markdown")
            return False
        return True
    
    def _load_docx_dependencies(self):
        """Load DOCX parsing dependencies."""
        try:
            global docx
            import docx
            self._docx_parser_loaded = True
        except ImportError:
            self.logger.error("DOCX parsing dependencies not installed. Run: pip install python-docx")
            return False
        return True
    
    def parse_resume(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a resume file in any supported format and convert it to the
        structured YAML format.
        
        Args:
            file_path (str): Path to the resume file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data in structured format or None if parsing failed
        """
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return None
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            if not self._pdf_parser_loaded and not self._load_pdf_dependencies():
                return None
            return self._parse_pdf(file_path)
        elif file_ext in ['.md', '.markdown']:
            if not self._markdown_parser_loaded and not self._load_markdown_dependencies():
                return None
            return self._parse_markdown(file_path)
        elif file_ext in ['.docx', '.doc']:
            if not self._docx_parser_loaded and not self._load_docx_dependencies():
                return None
            return self._parse_docx(file_path)
        elif file_ext in ['.txt', '.text']:
            return self._parse_text(file_path)
        elif file_ext in ['.yaml', '.yml']:
            # Already in YAML format, just validate it
            return self._parse_yaml(file_path)
        else:
            self.logger.error(f"Unsupported file format: {file_ext}")
            return None
    
    def _parse_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a PDF resume file.
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
        """
        self.logger.info(f"Parsing PDF resume: {file_path}")
        
        try:
            # Extract text from PDF using pdfplumber for better text extraction
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n\n"
            
            # Use AI to convert the extracted text to structured data
            return self._process_with_llm(text)
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            return None
    
    def _parse_markdown(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Markdown resume file.
        
        Args:
            file_path (str): Path to the Markdown file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
        """
        self.logger.info(f"Parsing Markdown resume: {file_path}")
        
        try:
            # Read Markdown content
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            
            # Use AI to convert the Markdown content to structured data
            return self._process_with_llm(md_content)
        except Exception as e:
            self.logger.error(f"Error parsing Markdown: {e}")
            return None
    
    def _parse_docx(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a DOCX resume file.
        
        Args:
            file_path (str): Path to the DOCX file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
        """
        self.logger.info(f"Parsing DOCX resume: {file_path}")
        
        try:
            # Extract text from DOCX
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            
            # Use AI to convert the extracted text to structured data
            return self._process_with_llm(text)
        except Exception as e:
            self.logger.error(f"Error parsing DOCX: {e}")
            return None
    
    def _parse_text(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a plain text resume file.
        
        Args:
            file_path (str): Path to the text file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
        """
        self.logger.info(f"Parsing text resume: {file_path}")
        
        try:
            # Read text content
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
            
            # Use AI to convert the text content to structured data
            return self._process_with_llm(text_content)
        except Exception as e:
            self.logger.error(f"Error parsing text file: {e}")
            return None
    
    def _parse_yaml(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse and validate a YAML resume file.
        
        Args:
            file_path (str): Path to the YAML file
            
        Returns:
            Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
        """
        self.logger.info(f"Parsing YAML resume: {file_path}")
        
        try:
            # Read YAML content
            with open(file_path, 'r', encoding='utf-8') as file:
                yaml_content = yaml.safe_load(file)
            
            # Validate YAML structure
            # TODO: Add more detailed validation
            if not isinstance(yaml_content, dict):
                self.logger.error("YAML file does not contain a dictionary")
                return None
            
            if 'basics' not in yaml_content:
                self.logger.warning("YAML file does not contain 'basics' section")
            
            if 'work' not in yaml_content:
                self.logger.warning("YAML file does not contain 'work' section")
            
            return yaml_content
        except Exception as e:
            self.logger.error(f"Error parsing YAML file: {e}")
            return None
    
    async def _process_with_llm(self, resume_text: str) -> Optional[Dict[str, Any]]:
        """
        Process extracted resume text using an LLM to convert it to structured format.
        
        Args:
            resume_text (str): The extracted text from the resume
            
        Returns:
            Optional[Dict[str, Any]]: Structured resume data or None if processing failed
        """
        self.logger.info("Processing resume text with AI...")
        
        # Create agent for LLM processing
        resume_agent = ResumeParsingAgent()
        
        # Process resume text
        parsed_data = await resume_agent.process_resume_text(resume_text)
        
        if not parsed_data:
            self.logger.error("Failed to process resume with AI")
            return None
        
        return parsed_data
    
    def save_as_yaml(self, resume_data: Dict[str, Any], output_path: str) -> bool:
        """
        Save parsed resume data as YAML file.
        
        Args:
            resume_data (Dict[str, Any]): Parsed resume data
            output_path (str): Path to save the YAML file
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info(f"Saving parsed resume to {output_path}")
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write YAML file
            with open(output_path, 'w', encoding='utf-8') as file:
                yaml.dump(resume_data, file, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving YAML file: {e}")
            return False


class ResumeParsingAgent(Agent):
    """
    Agent responsible for converting raw resume text into structured YAML format
    using LLM capabilities.
    """
    
    def __init__(self):
        super().__init__(name="ResumeParsingAgent")
        
        # Load system prompt
        self.system_prompt = """
        You are an expert resume parser. You will be provided with the raw text from a resume in various formats.
        Your task is to convert this text into a structured YAML format following the schema shown below.
        
        Extract as much information as possible and map it to the correct fields in the schema. If information for
        a particular field is not present, omit that field instead of leaving it blank or with placeholder text.
        
        For work experience and projects, identify bullet points describing responsibilities and accomplishments
        and format them as a list under the "responsibilities_and_accomplishments" field.
        
        When determining "title_variables", create a list of different job titles that could be used for the position
        based on the information provided, including synonyms and similar roles.
        
        Schema:
        ```yaml
        basics:
          name: "Full Name"
          email: "email@example.com"
          phone: "Phone Number with Country Code"
          location: 
            city: "City"
            province: "Province/State"
            country: "Country"
            address: "Street Address" # Only if provided
            postal_code: "Postal Code" # Only if provided
          linkedin: "LinkedIn URL" # Only if provided
          
        work:
          - title_variables:
              - "Job Title"
              - "Alternative Job Title" 
              - "Another Relevant Title"
            start_date: "Start Date" # Format: "MMM YYYY" (e.g., "Jan 2022")
            end_date: "End Date or Present" # Format: "MMM YYYY" or "Present"
            company: "Company Name"
            location: "City, Province/State, Country"
            responsibilities_and_accomplishments:
              - "First bullet point describing a responsibility or accomplishment"
              - "Second bullet point describing another responsibility or accomplishment"
              # Continue for all bullet points
          # Repeat for each work experience
        
        projects: # Optional section
          - name: "Project Name"
            responsibilities_and_accomplishments:
              - "First bullet point describing a responsibility or accomplishment"
              - "Second bullet point describing another responsibility or accomplishment"
              # Continue for all bullet points
          # Repeat for each project
        
        education:
          - institution: "University/School Name"
            degree: "Degree Type" # e.g., BA, BSc, MA, PhD
            field_of_study: "Field of Study"
            start_date: "Start Year" # Just the year is fine
            year_of_completion: "Completion Year" # Just the year is fine
          # Repeat for each education entry
        
        certificates: # Optional section
          - name: "Certificate Name"
            organization: "Issuing Organization"
            date_of_issue: "Issue Year" # Just the year is fine
          # Repeat for each certificate
        ```
        
        Provide only the YAML output with no additional explanations or markdown formatting.
        """
    
    async def process_resume_text(self, resume_text: str) -> Optional[Dict[str, Any]]:
        """
        Process raw resume text to extract structured information.
        
        Args:
            resume_text (str): Raw text extracted from the resume
            
        Returns:
            Optional[Dict[str, Any]]: Structured resume data or None if processing failed
        """
        self.logger.info("Processing resume text with AI...")
        
        # The 3.7 Sonnet model provides the best results for this task
        response = await self.call_llm_api_async(
            prompt=resume_text,
            system_message=self.system_prompt,
            model="anthropic/claude-3.7-sonnet",
            temperature=0.2
        )
        
        if not response:
            return None
            
        try:
            # Extract the YAML section from the response
            yaml_section = response
            if "```yaml" in response:
                yaml_section = response.split("```yaml", 1)[1]
                if "```" in yaml_section:
                    yaml_section = yaml_section.split("```", 1)[0]
            elif "```" in response:
                yaml_section = response.split("```", 1)[1]
                if "```" in yaml_section:
                    yaml_section = yaml_section.split("```", 1)[0]
            
            # Parse the YAML
            parsed_yaml = yaml.safe_load(yaml_section)
            
            # Validate and clean the parsed data
            cleaned_data = self._clean_parsed_data(parsed_yaml)
                
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Error parsing AI output: {e}")
            self.logger.debug(f"Response: {response}")
            return None
    
    def _clean_parsed_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and validate the parsed resume data.
        
        Args:
            parsed_data (Dict[str, Any]): Raw parsed data from AI
            
        Returns:
            Dict[str, Any]: Cleaned and validated data
        """
        # Ensure the data has the required sections
        if not parsed_data:
            return {}
        
        cleaned_data = {}
        
        # Copy basics section if it exists
        if 'basics' in parsed_data:
            cleaned_data['basics'] = parsed_data['basics']
        else:
            cleaned_data['basics'] = {}
        
        # Clean work section
        if 'work' in parsed_data and isinstance(parsed_data['work'], list):
            cleaned_data['work'] = []
            for i, work_exp in enumerate(parsed_data['work']):
                if not isinstance(work_exp, dict):
                    continue
                
                # Add ID to each work experience for better tracking
                work_exp['id'] = f"{i+1:02d}"
                
                # Ensure title_variables is a list
                if 'title_variables' in work_exp and not isinstance(work_exp['title_variables'], list):
                    work_exp['title_variables'] = [work_exp['title_variables']]
                
                # Ensure company is a string
                if 'company' in work_exp and isinstance(work_exp['company'], list):
                    work_exp['company'] = work_exp['company'][0]
                
                cleaned_data['work'].append(work_exp)
        else:
            cleaned_data['work'] = []
        
        # Copy other sections if they exist
        for section in ['projects', 'education', 'certificates']:
            if section in parsed_data and isinstance(parsed_data[section], list):
                cleaned_data[section] = parsed_data[section]
        
        return cleaned_data


async def parse_resume_file(file_path: str, output_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a resume file and optionally save it as YAML.
    
    Args:
        file_path (str): Path to the resume file
        output_path (Optional[str]): Path to save the parsed resume as YAML
        
    Returns:
        Optional[Dict[str, Any]]: Parsed resume data or None if parsing failed
    """
    parser = ResumeParser()
    
    # Determine output path if not provided
    if not output_path:
        # Use the input file's directory and name, but with .yaml extension
        output_dir = os.path.dirname(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{file_name}_parsed.yaml")
    
    # Parse the resume
    parsed_data = await parser.parse_resume(file_path)
    
    if parsed_data:
        # Save as YAML
        success = parser.save_as_yaml(parsed_data, output_path)
        if success:
            logger.info(f"Resume successfully parsed and saved to {output_path}")
        else:
            logger.error(f"Failed to save parsed resume to {output_path}")
    
    return parsed_data


async def main_async():
    """Async main function for testing the resume parser."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse resume files into structured YAML format")
    parser.add_argument("file_path", help="Path to the resume file to parse")
    parser.add_argument("--output", "-o", help="Path to save the parsed YAML file", default=None)
    args = parser.parse_args()
    
    parsed_data = await parse_resume_file(args.file_path, args.output)
    
    if parsed_data:
        print("Resume parsed successfully!")
    else:
        print("Failed to parse resume.")


def main():
    """Main function that sets up and runs the async event loop."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main() 