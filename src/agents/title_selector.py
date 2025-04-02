#!/usr/bin/env python3
from typing import List, Dict, Any, Union

from .base_agent import Agent

class TitleSelector(Agent):
    """
    Agent responsible for selecting the most relevant title from title_variables
    for each role based on the job description.
    """
    
    def __init__(self):
        super().__init__(name="TitleSelector")
    
    def run(self, role: Dict[str, Any], job_description: str) -> str:
        """
        Select the most relevant title for a role based on the job description.
        
        Args:
            role (Dict[str, Any]): A work experience entry from the resume
            job_description (str): The job description (potentially enriched)
            
        Returns:
            str: The selected title
        """
        # If no title variables or only one, return the first one
        if "title_variables" not in role or len(role["title_variables"]) <= 1:
            return role["title_variables"][0] if "title_variables" in role and role["title_variables"] else ""
            
        if not self.openai_api_key:
            # Default to first title if no API key
            return role["title_variables"][0]
        
        print("Selecting the most relevant title for role...")
        
        # Prepare data for the AI model
        title_variables = role["title_variables"]
        company = ", ".join(role["company"]) if isinstance(role["company"], list) else role["company"]
        
        # Get a sample of responsibilities for context
        sample_resp = []
        if "responsibilities_and_accomplishments" in role:
            for group_name, group_data in role["responsibilities_and_accomplishments"].items():
                if "original_sentence" in group_data:
                    sample_resp.append(group_data["original_sentence"])
        
        # Use AI to select relevant title
        selected_title = self._select_title_with_ai(title_variables, company, sample_resp, job_description)
        
        # If AI selection failed, default to first title
        if not selected_title:
            return title_variables[0]
        
        return selected_title
    
    def _select_title_with_ai(self, title_variables: List[str], company: str, responsibilities: List[str], job_description: str) -> str:
        """
        Use AI to select the most relevant title based on the job description.
        
        Args:
            title_variables (List[str]): List of possible title variations
            company (str): Company name
            responsibilities (List[str]): List of responsibilities for context
            job_description (str): The job description
            
        Returns:
            str: The selected title
        """
        # Create a list of title options for the prompt
        title_options = "\n".join([f"{i+1}. {title}" for i, title in enumerate(title_variables)])
        
        # Create a sample of responsibilities for context
        resp_sample = "; ".join(responsibilities[:3]) if responsibilities else "No sample responsibilities available"
        
        prompt = f"""
        I'm tailoring my resume for a job application. I need to select the most appropriate job title variation 
        that best aligns with the job description. Please analyze the following information and recommend 
        the most relevant title.
        
        Title Options:
        {title_options}
        
        Company: {company}
        
        Sample Responsibilities: {resp_sample}
        
        Job Description:
        {job_description}
        
        Please analyze the job description carefully and select the title that best aligns with the terminology,
        skills, and responsibilities mentioned in the job posting. Return only the exact text of the selected 
        title, with no additional commentary.
        """
        
        system_message = "You are a professional resume advisor that helps select the most effective job titles for resumes."
        
        content = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3
        )
        
        if not content:
            return ""
        
        # Try to match the response with one of the title variables
        for title in title_variables:
            if title.lower() in content.lower():
                return title
        
        # If no exact match, try to find the index number in the response (e.g., "Option 1", "Title 2")
        import re
        indices = re.findall(r'\b\d+\b', content)
        for idx in indices:
            try:
                index = int(idx) - 1  # Convert to 0-based index
                if 0 <= index < len(title_variables):
                    return title_variables[index]
            except ValueError:
                continue
        
        # If all else fails, return the first title variable
        return title_variables[0] 