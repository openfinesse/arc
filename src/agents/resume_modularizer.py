#!/usr/bin/env python3
import os
import yaml
import asyncio
from typing import Dict, Any, List, Optional, Union
import copy

from .base_agent import Agent

class ResumeModularizer(Agent):
    """
    Agent responsible for converting a simple resume bullet point into a modular format
    that can be customized for different job applications.
    """
    
    def __init__(self):
        super().__init__(name="ResumeModularizer")
        
        # Load system prompt from Agent_Instruction.md
        self.system_prompt = """
        You will be provided a bullet point from a resume. You are to provide a structured output in YAML. The output will serve as a modular structure that a subsequent LLM will use to customize resume points based on a given job description.

        ## Variable Creation Guidelines

        When deciding what elements to turn into variables versus keeping as static text:

        1. **Action verbs and first words** should become variables to prevent repetition across multiple resume points in the final document.

        2. **Technology terms** that commonly appear with different nomenclatures in job postings (e.g., "Microsoft 365" vs "M365" vs "Office 365" vs etc) should be variables to enable easier matching with job requirements.

        3. **Related technologies** should be split into separate variables when they might appear independently in job postings (e.g., separate "Microsoft 365" and "Entra ID" rather than combining them).

        4. **Avoid potential redundancies** - If a section might create word repetition when combined with other variable choices, make it modular. For example, if one variable option is "Managed," avoid having "managing" in static text, or vice versa.

        5. **Provide context in variable options** - Each modular component should maintain enough context that an AI agent can confidently choose an option.

        6. **Do not overmodularize** - Take the following senetence as an example: "Redesigned 12+ administrative processes using standardized templates and approval workflows, reducing new client onboarding time from 18 days to 4 days and improving customer request response time by 25%." It's not necessary to turn the metrics into seperate modular components. Now that doesn't mean you're not allowed to or shouldn't modularize metrics but the reason should be worthwhile. The point about overmodularizing applies to other parts of a sentence as well, not just metrics.

        7. When creating variable options for action verbs, avoid using overused, clichéd language. For example, "spearheaded" is a clichéd action verb. Streamlined is another clichéd action verb, albiet more acceptable so long as it's used in the right context.
        
        ## Output Format

        ```yaml
        original_sentence: "The original resume bullet point"
        modular_sentence: "A template with {variable} placeholders that maintains proper grammar and flow"
        variables:
        variable_name:
            - "Option 1"
            - "Option 2 (synonym or alternative phrasing)"
            - "Option 3 (may include adjacent terms relevant to job postings)"
        ```

        **Example:**
        Input: "Administered Microsoft 365 and Entra ID, configuring dynamic security groups and conditional access policies, and optimizing license management"

        ```yaml
        original_sentence: "Administered Microsoft 365 and Entra ID, configuring dynamic security groups and conditional access policies, and optimizing license management"
        modular_sentence: "{action} {microsoft} and {cloud_directory}, configuring dynamic security groups and conditional access policies, and {tasks}"
        variables:
        action:
            - "Managed"
            - "Administered"
        microsoft:
            - "Microsoft 365"
            - "M365"
            - "Office 365"
            - "O365"
        cloud_directory:
            - "Entra ID"
            - "Azure AD"
            - "Azure Active Directory"
            - "Microsoft Entra ID"
            - "Microsoft Azure AD"
        tasks:
            - "optimizing license management"
            - "optimizing license assignments"
        ```
        """
    
    async def run(self, bullet_point: str, group_index: int) -> Dict[str, Any]:
        """
        Convert a simple resume bullet point into a modular structure.
        
        Args:
            bullet_point (str): The bullet point to convert
            group_index (int): The group index for organization in the output
            
        Returns:
            Dict[str, Any]: The modular structure for this bullet point
        """
        
        self.logger.info(f"Processing bullet point {group_index}: {bullet_point[:50]}...")
        
        modular_point = await self._convert_bullet_point(bullet_point)
        
        if not modular_point:
            # Return basic structure if conversion failed
            self.logger.warning(f"Conversion failed for bullet point {group_index}. Using basic structure.")
            return {
                "original_sentence": bullet_point,
                "modular_sentence": [bullet_point.replace(".", "")],
                "variables": {},
                "id": f"{group_index:02d}"  # Add a zero-padded ID
            }
        
        # Add a simple sequential ID to the modular structure
        modular_point["id"] = f"{group_index:02d}"  # Format as 01, 02, etc.
        
        return modular_point
    
    async def _convert_bullet_point(self, bullet_point: str) -> Optional[Dict[str, Any]]:
        """
        Use AI to convert a bullet point into a modular structure.
        
        Args:
            bullet_point (str): The bullet point to convert
            
        Returns:
            Optional[Dict[str, Any]]: The modular structure or None if the conversion failed
        """
        prompt = bullet_point
        
        # The 3.7 Sonnet model provides the best results for this task
        # Deepseek V3 0324 and o1-mini has also shown to produce decent results and are a cheaper option
        self.logger.debug(f"Converting bullet point using claude-3-7-sonnet model")
        response = await self.call_llm_api_async(
            prompt=prompt,
            system_message=self.system_prompt,
            model="anthropic/claude-3.7-sonnet",
            temperature=0.5
        )
        
        if not response:
            return None
            
        try:
            # Extract the YAML section from the response (the response might include markdown code block indicators)
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
                
            return parsed_yaml
            
        except Exception as e:
            self.logger.error(f"Error parsing conversion output: {e}")
            self.logger.debug(f"Response: {response}")
            return None
    
    # async def _generate_tags(self, modular_structure: Dict[str, Any]) -> str:
    #     """
    #     Generate tags for a modular structure by extracting technologies and skills from variables.
        
    #     Args:
    #         modular_structure (Dict[str, Any]): The modular structure for a resume point
            
    #     Returns:
    #         str: A string of tags extracted from the variables
    #     """
    #     if not modular_structure or "variables" not in modular_structure:
    #         return ""
            
    #     prompt = f"""
    #     Extract all technology terms, skills, and domain-specific keywords from the following resume point variables.
    #     Return a comma-separated list of these terms that can be used as tags to match with job descriptions.
    #     Do not include the same technology term more than once. For example if "Azure AD", "Azure Active
    #     Directory", and "Microsoft Azure AD" were all present, return only one of them.
        
    #     Original sentence: {modular_structure.get('original_sentence', '')}
        
    #     Variables:
    #     {yaml.dump(modular_structure.get('variables', {}))}
        
    #     Return only the comma-separated list of terms, nothing else.
    #     """
        
    #     system_message = "You are a helpful assistant that extracts relevant technology terms, skills, and keywords from resume data."
        
    #     response = await self.call_llm_api_async(
    #         prompt=prompt,
    #         system_message=system_message,
    #         temperature=0.4
    #     )
        
    #     if not response:
    #         # If LLM call fails, generate basic tags from the original sentence
    #         original = modular_structure.get('original_sentence', '')
    #         words = original.split()
    #         return ", ".join([word for word in words if len(word) > 3 and word[0].isupper()])
            
    #     return response.strip()

    async def process_resume(self, simple_resume_path: str) -> Dict[str, Any]:
        """
        Process an entire resume file, converting bullet points into modular structures.
        Uses asyncio.gather to process multiple bullet points concurrently.
        
        Args:
            simple_resume_path (str): Path to the simple resume YAML file
            
        Returns:
            Dict[str, Any]: The modular resume structure
        """
        self.logger.info(f"Processing resume from {simple_resume_path}...")
        
        try:
            # Load the simple resume
            with open(simple_resume_path, 'r') as file:
                simple_resume = yaml.safe_load(file)
            
            # Create a deep copy to modify for the modular resume
            modular_resume = copy.deepcopy(simple_resume)
            
            # Count total work experiences and projects to process
            total_work_exps = len(modular_resume.get("work", []))
            total_projects = len(modular_resume.get("projects", []))
            total_items = total_work_exps + total_projects
            current_item = 0
            
            # Keep track of the global sentence counter for sequential IDs
            sentence_counter = 1
            
            # Process all work experiences
            for i, work_exp in enumerate(modular_resume.get("work", [])):
                current_item += 1
                company_name = work_exp.get('company', 'Unknown')
                if isinstance(company_name, list):
                    company_name = company_name[0]
                self.progress_update(current_item, total_items, f"Processing work experience: {company_name}")
                
                # Process responsibilities and accomplishments
                resp_and_accom = work_exp.get("responsibilities_and_accomplishments", [])
                if isinstance(resp_and_accom, list):
                    new_resp_and_accom = {}
                    
                    # Create tasks for concurrent processing
                    tasks = []
                    for j, bullet in enumerate(resp_and_accom):
                        # Use the global counter for ID generation
                        tasks.append(self.run(bullet, sentence_counter))
                        sentence_counter += 1
                    
                    # Process all bullets concurrently
                    results = await asyncio.gather(*tasks)
                    
                    # Assign results to the appropriate group
                    for j, result in enumerate(results):
                        group_key = f"group_{j+1}"
                        new_resp_and_accom[group_key] = result
                    
                    work_exp["responsibilities_and_accomplishments"] = new_resp_and_accom
            
            # Process projects if they exist
            for i, project in enumerate(modular_resume.get("projects", [])):
                current_item += 1
                project_name = project.get('name', 'Unknown')
                self.progress_update(current_item, total_items, f"Processing project: {project_name}")
                
                resp_and_accom = project.get("responsibilities_and_accomplishments", [])
                if isinstance(resp_and_accom, list):
                    new_resp_and_accom = {}
                    
                    # Create tasks for concurrent processing
                    tasks = []
                    for j, bullet in enumerate(resp_and_accom):
                        # Use the global counter for ID generation
                        tasks.append(self.run(bullet, sentence_counter))
                        sentence_counter += 1
                    
                    # Process all bullets concurrently
                    results = await asyncio.gather(*tasks)
                    
                    # Assign results to the appropriate group
                    for j, result in enumerate(results):
                        group_key = f"group_{j+1}"
                        new_resp_and_accom[group_key] = result
                    
                    project["responsibilities_and_accomplishments"] = new_resp_and_accom
            
            self.logger.info("Resume processing complete")
            return modular_resume
            
        except Exception as e:
            self.logger.error(f"Error processing resume: {e}")
            return None
    
    def save_modular_resume(self, modular_resume: Dict[str, Any], output_path: str) -> bool:
        """
        Save the modular resume to a YAML file.
        
        Args:
            modular_resume (Dict[str, Any]): The modular resume structure
            output_path (str): Path to save the YAML file
            
        Returns:
            bool: True if the save was successful, False otherwise
        """
        if not modular_resume:
            self.logger.error("No modular resume to save.")
            return False
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the modular resume
            with open(output_path, 'w') as file:
                yaml.dump(modular_resume, file, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Modular resume saved to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving modular resume: {e}")
            return False 