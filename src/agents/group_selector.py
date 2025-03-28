#!/usr/bin/env python3
import os
import requests
import json
from typing import List, Dict, Any
import math
class GroupSelector:
    """
    Agent responsible for selecting which responsibility/accomplishment groups 
    from a role are most relevant to the job description.
    """
    
    def __init__(self):
        # Get API key from environment variable for OpenAI (or alternative service)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Using fallback selection method for groups.")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
        # self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
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
            
        if not self.api_key:
            # Default to selecting all groups if no API key
            return list(responsibility_groups.keys())
        
        print("Analyzing responsibility groups for relevance...")
        
        # Prepare data for the AI model
        group_summaries = []
        for group_name, group_data in responsibility_groups.items():
            if "original_sentence" in group_data:
                group_summaries.append(f"Resume point '{group_name}': {group_data['original_sentence']}")
        
        # Calulate the minimum number of groups to include (60% of the total, rounded up to the nearest integer)
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
            
        Returns:
            List[str]: Names of the selected groups
        """
        prompt = f"""
        I'm creating a tailored resume for a job application. For a specific work role, I need to select which 
        responsibilities and accomplishments to include. Below are summaries of different responsibility groups, 
        followed by the job description. Select relevant groups that should be included. You must select at least 
        {min_groups} groups.
        
        Responsibility Groups:
        {chr(10).join(group_summaries)}
        
        Job Description:
        {job_description}
        
        Please carefully analyze the job description and select the responsibility point groups that best match the 
        required skills, experience, and responsibilities. Return only the group names of the selected groups, 
        with no additional text.
        
        Selection can be based on the following factors:
        1. Matches between point groups and job requirements
        2. Transferable skills that would be valuable for the position
        3. Accomplishments that demonstrate relevant capabilities
        4. Technical or domain expertise mentioned in both the group and job description
        
        """
        
        # print(f"Prompt: {prompt}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            # "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that selects relevant work responsibilities for job applications."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4  # Lower temperature for more consistent results
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Parse the response to get group names
                selected_groups = []
                
                # Extract group names, considering various formats the AI might respond with
                for group_name in group_names:
                    # Check if the exact group name appears in the response
                    if group_name in content:
                        selected_groups.append(group_name)
                    # Check for variations like "Group 1" or "Group group_1"
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
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return []
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return [] 