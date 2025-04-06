#!/usr/bin/env python3
from typing import List, Dict, Any
import math
import re

from sympy import Domain

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
        
        self.logger.debug("Analyzing responsibility groups for relevance...")
        
        # Prepare data for the AI model with simple numeric indices
        group_summaries = []
        name_to_index = {}  # Maps group names to numeric indices
        index_to_name = {}  # Maps numeric indices to group names
        
        for i, (group_name, group_data) in enumerate(responsibility_groups.items(), 1):
            index = str(i)
            name_to_index[group_name] = index
            index_to_name[index] = group_name
            
            # Use the original sentence as the summary
            original_sentence = group_data.get('original_sentence', 'No description available')
            group_summaries.append(f"{index}. {original_sentence}")
        
        # Calculate the minimum number of groups to include (60% of the total, rounded to the nearest integer)
        min_groups = round(len(responsibility_groups) * 0.6)
        
        # Use AI to select relevant groups
        selected_indices = self._select_groups_with_ai(
            group_summaries, 
            list(index_to_name.keys()), 
            job_description, 
            min_groups
        )
        
        # Convert indices back to group names
        selected_groups = [index_to_name[idx] for idx in selected_indices if idx in index_to_name]
        
        # If AI selection failed or returned empty, default to all groups
        if not selected_groups:
            self.logger.warning("AI selection failed or returned empty. Using all groups.")
            return list(responsibility_groups.keys())
        
        self.logger.debug(f"Selected {len(selected_groups)} groups out of {len(responsibility_groups)}")
        return selected_groups
    
    def _select_groups_with_ai(self, group_summaries: List[str], group_indices: List[str], job_description: str, min_groups: int) -> List[str]:
        """
        Use AI to select the most relevant responsibility/accomplishment groups based on the job description.
        
        Args:
            group_summaries (List[str]): Summaries of each group with numeric indices
            group_indices (List[str]): Numeric indices of each group
            job_description (str): The job description
            min_groups (int): Minimum number of groups to select
            
        Returns:
            List[str]: Indices of the selected groups
        """
        prompt = f"""
        Resume Points:
        {chr(10).join(group_summaries)}
        
        Job Description:
        {job_description}
        """
        
        system_message = f"""
        You are a helpful assistant that selects relevant resume work experiences for job applications. 
        For a specific work role, you need to select which responsibilities and accomplishments to include. 
        The user will provide you with numbered resume points, followed by a job description. 
        Some resume points might be nearly identical to each other, in this case only select the most relevant one from between them.
        Select the resume points that should be included based on their relevance to the job description. 
        
        You must select at least {min_groups} resume points but can select more.
        
        Selection can be based on the following factors:
        1. Matches between point and job requirements
        2. Transferable skills and technologies that would be valuable for the position
        3. Accomplishments that demonstrate relevant capabilities
        4. Technical or Domain expertise mentioned in both the point and job description

        Return ONLY the numbers of the selected points, separated by commas.
        For example: 1,3,5,7
        """
        
        content = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if not content:
            return []
            
        # Extract all numbers from the response
        selected_indices = re.findall(r'\b\d+\b', content)
        
        # Validate that all selected indices are in our list of valid indices
        selected_indices = [idx for idx in selected_indices if idx in group_indices]
        
        # Ensure we have at least min_groups selected
        if len(selected_indices) < min_groups and group_indices:
            # Add more groups until we reach the minimum
            remaining = [idx for idx in group_indices if idx not in selected_indices]
            needed = min_groups - len(selected_indices)
            
            # Add up to the needed amount or whatever's left
            additional = remaining[:min(needed, len(remaining))]
            selected_indices.extend(additional)
        
        return selected_indices 