#!/usr/bin/env python3
import os
import requests
import json
from typing import List, Dict, Any

class RoleSelector:
    """
    Agent responsible for selecting which roles from the resume are most relevant 
    to the job description.
    """
    
    def __init__(self):
        # Get API key from environment variable for OpenAI (or alternative service)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Using fallback selection method.")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def run(self, work_experience: List[Dict[str, Any]], job_description: str) -> List[int]:
        """
        Select the roles that are most relevant to the job description.
        
        Args:
            work_experience (List[Dict[str, Any]]): List of work experience entries from the resume
            job_description (str): The job description (potentially enriched)
            
        Returns:
            List[int]: Indices of the selected roles
        """
        if not self.api_key:
            # Default to selecting all roles if no API key
            return list(range(len(work_experience)))
        
        print("Analyzing roles for relevance to job description...")
        
        # Prepare data for the AI model
        role_summaries = []
        for i, role in enumerate(work_experience):
            # Create a summary of each role with all title variations
            titles = ", ".join(role["title_variations"])
            companies = ", ".join(role["company"])
            
            # Get a sample of responsibilities for context
            sample_resp = []
            if "responsibilities_and_accomplishments" in role:
                for group_name, group_data in role["responsibilities_and_accomplishments"].items():
                    if "original_sentence" in group_data:
                        sample_resp.append(group_data["original_sentence"])
            
            role_summary = f"Role {i+1}: {titles} at {companies}, {role['start_date']} to {role['end_date']}.\n"
            if sample_resp:
                role_summary += "Sample responsibilities: " + "; ".join(sample_resp[:3]) + "\n"
            
            role_summaries.append(role_summary)
        
        # Use AI to select relevant roles
        selected_indices = self._select_roles_with_ai(role_summaries, job_description)
        
        # If AI selection failed or returned empty, default to all roles
        if not selected_indices:
            return list(range(len(work_experience)))
        
        return selected_indices
    
    def _select_roles_with_ai(self, role_summaries: List[str], job_description: str) -> List[int]:
        """
        Use AI to select the most relevant roles based on the job description.
        
        Args:
            role_summaries (List[str]): Summaries of each role
            job_description (str): The job description
            
        Returns:
            List[int]: Indices of the selected roles (0-based)
        """
        prompt = f"""
        I'm creating a tailored resume for a job application. Below are summaries of my work experience roles, 
        followed by the job description. Please select the roles that should be included in my resume.
        
        Work Experience:
        {"".join(role_summaries)}
        
        Job Description:
        {job_description}
        
        Please analyze the job description and select the roles that match the required skills, experience, 
        and responsibilities. Return only the role numbers of the selected roles, with no additional text. 
        Exclude roles that are irrelevant.
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that selects relevant work experience for job applications."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5  # Lower temperature for more consistent results
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Parse the response to get role indices
                # Remove any non-numeric characters except commas
                content = ''.join(c for c in content if c.isdigit() or c == ',')
                
                # Split by comma and convert to integers, then subtract 1 for 0-based indexing
                selected_indices = [int(idx.strip()) - 1 for idx in content.split(',') if idx.strip()]
                
                # Validate indices are within range
                max_index = len(role_summaries) - 1
                selected_indices = [idx for idx in selected_indices if 0 <= idx <= max_index]
                
                return selected_indices
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return []
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return [] 