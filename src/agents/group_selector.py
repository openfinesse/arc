#!/usr/bin/env python3
from typing import List, Dict, Any
import math

from .base_agent import Agent

class GroupSelector(Agent):
    """
    Agent responsible for selecting which responsibility/accomplishment groups 
    from a role are most relevant to the job description.
    """
    
    def __init__(self):
        super().__init__(name="GroupSelector")
    
    def run(self, responsibility_groups: Dict[str, Any], job_description: str) -> List[str]:
        """
        Select the resume points that are most relevant to the job description.
        
        Args:
            responsibility_groups (Dict[str, Any]): Dict of responsibility/accomplishment groups
            job_description (str): The job description (potentially enriched)
            
        Returns:
            List[str]: Names of the selected points
        """
        if not responsibility_groups:
            return []
            
        if not self.openai_api_key:
            # Default to selecting all groups if no API key
            return list(responsibility_groups.keys())
        
        print("Analyzing responsibility groups for relevance...")
        
        # Prepare data for the AI model
        group_summaries = []
        for group_name, group_data in responsibility_groups.items():
            if "original_sentence" in group_data:
                group_summaries.append(f"Resume point '{group_name}': {group_data['original_sentence']}")
        
        # Calculate the minimum number of groups to include (60% of the total, rounded up to the nearest integer)
        min_groups = math.ceil(len(responsibility_groups) * 0.6)
        
        # Use AI to select relevant groups
        selected_groups = self._select_groups_with_ai(group_summaries, list(responsibility_groups.keys()), job_description, min_groups)
        
        # If AI selection failed or returned empty, default to all groups
        if not selected_groups:
            return list(responsibility_groups.keys())
        
        return selected_groups
    
    def _select_groups_with_ai(self, group_summaries: List[str], group_names: List[str], job_description: str, min_groups: int) -> List[str]:
        """
        Use AI to select the most relevant responsibility/accomplishment groups based on the job description.
        
        Args:
            group_summaries (List[str]): Summaries of each group
            group_names (List[str]): Names of each group
            job_description (str): The job description
            min_groups (int): Minimum number of groups to select
            
        Returns:
            List[str]: Names of the selected groups
        """
        prompt = f"""
        I'm creating a tailored resume for a job application. For a specific work role, I need to select which 
        responsibilities and accomplishments to include. Below are the bullet points, followed by the job description. 
        Select the bullet points that should be included based on their relevance to the job description. 
        You must select at least {min_groups} bullet points but can select more.
        
        Responsibility Groups:
        {chr(10).join(group_summaries)}
        
        Job Description:
        {job_description}
        
        Please carefully analyze the job description and select the points that best match the 
        required skills, experience, and responsibilities. Return only the numbers of the selected points, 
        with no additional text.
        
        Selection can be based on the following factors:
        1. Matches between point and job requirements
        2. Transferable skills that would be valuable for the position
        3. Accomplishments that demonstrate relevant capabilities
        4. Technical or domain expertise mentioned in both the point and job description
        """
        
        system_message = "You are a helpful assistant that selects relevant resume work experiences for job applications."
        
        content = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if not content:
            return []
            
        # Parse the response to get group names
        selected_groups = []
        
        # Extract group names, considering various formats the AI might respond with
        for group_name in group_names:
            # Check if the exact group name appears in the response
            if group_name in content:
                selected_groups.append(group_name)
            # Check for variables like "Group 1" or "Group group_1"
            elif f"Group {group_name}" in content or f"Group '{group_name}'" in content:
                selected_groups.append(group_name)
        
        # If parsing failed, try a more generic approach - looking for the numeric part
        if not selected_groups and any(g.startswith("group_") for g in group_names):
            import re
            numbers = re.findall(r'\d+', content)
            for num in numbers:
                group_candidate = f"group_{num}"
                if group_candidate in group_names:
                    selected_groups.append(group_candidate)
        
        return selected_groups 