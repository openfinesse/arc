#!/usr/bin/env python3
from typing import List, Dict, Any

from .base_agent import Agent

class RoleSelector(Agent):
    """
    Agent responsible for selecting which roles from the resume are most 
    relevant to the job description.
    """
    
    def __init__(self):
        super().__init__(name="RoleSelector")
    
    def run(self, roles: List[Dict[str, Any]], job_description: str) -> List[int]:
        """
        Select the roles that are most relevant to the job description.
        
        Args:
            roles (List[Dict[str, Any]]): List of work experience entries from the resume
            job_description (str): The job description (potentially enriched)
            
        Returns:
            List[int]: Indices of the selected roles
        """
        if not roles:
            return []
            
        if not self.openai_api_key:
            # Default to selecting all roles if no API key
            return list(range(len(roles)))
        
        self.logger.info("Analyzing roles for relevance to job description...")
        
        # Prepare data for the AI model
        role_descriptions = []
        for i, role in enumerate(roles):
            company = ", ".join(role["company"]) if isinstance(role["company"], list) else role["company"]
            
            # Start with the title and company
            role_description = f"Role {i+1}: {role['title_variables'][0]} at {company} ({role['start_date']} - {role['end_date']})\n"
            
            # Add a few responsibilities if available
            if "responsibilities_and_accomplishments" in role:
                role_description += "Sample responsibilities:\n"
                
                # Check if the responsibilities are in the old or new format
                resp = role["responsibilities_and_accomplishments"]
                if isinstance(resp, dict):
                    # New format (dict with group keys)
                    sample_count = 0
                    for group_name, group_data in resp.items():
                        if "original_sentence" in group_data and sample_count < 3:
                            role_description += f"- {group_data['original_sentence']}\n"
                            sample_count += 1
                elif isinstance(resp, list):
                    # Old format (list of strings)
                    for i, r in enumerate(resp[:3]):
                        role_description += f"- {r}\n"
            
            role_descriptions.append(role_description)
            
        # Calculate the minimum number of roles to include (1 role for <3 roles, otherwise half rounded up)
        min_roles = 1 if len(roles) < 3 else (len(roles) + 1) // 2
        
        # Use AI to select relevant roles
        selected_indices = self._select_roles_with_ai(role_descriptions, job_description, min_roles)
        
        # If AI selection failed, default to all roles
        if not selected_indices:
            self.logger.warning("Role selection failed. Using all roles.")
            return list(range(len(roles)))
        
        self.logger.debug(f"Selected {len(selected_indices)} roles out of {len(roles)}")
        return selected_indices
    
    def _select_roles_with_ai(self, role_descriptions: List[str], job_description: str, min_roles: int) -> List[int]:
        """
        Use AI to select the most relevant roles based on the job description.
        
        Args:
            role_descriptions (List[str]): Descriptions of each role
            job_description (str): The job description
            min_roles (int): Minimum number of roles to select
            
        Returns:
            List[int]: Indices of the selected roles
        """
        prompt = f"""
        I'm creating a tailored resume for a job application. Below are my roles/jobs, followed by the job description. 
        Please select which roles are most relevant to include for this job application.
        
        My Roles:
        {chr(10).join(role_descriptions)}
        
        Job Description:
        {job_description}
        
        You must select at least {min_roles} roles, but can select more if they're relevant. Consider factors like:
        - Skills and responsibilities that match the job requirements
        - Recent roles that demonstrate relevant experience
        - Technical expertise or domain knowledge relevant to the position
        
        Return only the numbers of the selected roles, with no additional text.
        """
        
        system_message = "You are a helpful assistant that selects relevant resume entries for job applications."
        
        content = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if not content:
            return []
            
        # Parse the response to get the role indices
        selected_indices = []
        
        # Extract digits, assuming the AI returned something like "1, 3, 4" or "Role 1, Role 3, Role 4"
        import re
        for match in re.finditer(r'\b(\d+)\b', content):
            try:
                index = int(match.group(1)) - 1  # Convert to 0-based index
                if 0 <= index < len(role_descriptions):
                    selected_indices.append(index)
            except ValueError:
                continue
        
        # Remove duplicates and sort
        selected_indices = sorted(list(set(selected_indices)))
        
        return selected_indices 