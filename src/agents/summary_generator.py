#!/usr/bin/env python3
import os
import requests
import json
from typing import Dict, Any

class SummaryGenerator:
    """
    Agent responsible for creating a resume summary based on the completed points,
    job description, and company information.
    """
    
    def __init__(self):
        # Get API key from environment variable for OpenAI (or alternative service)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Summary generation will be limited.")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
        # self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def run(self, constructed_sentences: Dict[str, Any], job_description: str, company_info: Dict[str, Any]) -> str:
        """
        Create a resume summary based on the completed points, job description, and company information.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description (potentially enriched)
            company_info (Dict[str, Any]): Information about the company
            
        Returns:
            str: The generated resume summary
        """
        if not self.api_key:
            # Return a basic summary if no API key
            return "Professional with experience in IT and systems administration seeking new opportunities."
        
        print("Generating resume summary...")
        
        return self._generate_summary_with_ai(constructed_sentences, job_description, company_info)
    
    def _generate_summary_with_ai(self, constructed_sentences: Dict[str, Any], job_description: str, company_info: Dict[str, Any]) -> str:
        """
        Use AI to generate a resume summary.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description
            company_info (Dict[str, Any]): Information about the company
            
        Returns:
            str: The generated resume summary
        """
        # Prepare the resume content
        resume_content = []
        
        for role_idx, role_data in constructed_sentences.items():
            role_content = f"### {role_data['title']} | {role_data['company']}\n"
            role_content += f"*{role_data['start_date']} - {role_data['end_date']}* | {role_data['location']}\n\n"
            
            for group_name, sentence in role_data.get("sentences", {}).items():
                role_content += f"- {sentence}\n"
            
            resume_content.append(role_content)
        
        # Format company info if available
        company_info_str = ""
        if company_info:
            company_info_str = json.dumps(company_info, indent=2)
        
        prompt = f"""
        I need you to create a compelling resume summary for a job application. This summary should
        succinctly highlight my most relevant qualifications, skills, and experience for the specific role,
        while aligning with the company's values and culture.
        
        Resume Content:
        {chr(10).join(resume_content)}
        
        Job Description:
        {job_description}
        
        Company Information:
        {company_info_str}
        
        Please write a professional, impactful resume summary (3-5 sentences) that:
        
        1. Captures my professional identity in a way that aligns with the job
        2. Written in silent first person (no pronouns) and doesn't mention the company name
        3. Highlights my most relevant skills and accomplishments for this specific role
        4. Speaks to the company's values or culture if relevant
        5. Includes a strong statement about what I can bring to the role

        
        The summary should be crisp, confident, and tailored to position me as an ideal candidate for this specific job.
        
        Return ONLY the summary as plaintext without any additional commentary or explanation.
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a professional resume writer who creates compelling resume summaries."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7  # Higher temperature for more creative writing
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"].strip()
                
                # Clean up the summary - sometimes the AI adds quotes
                summary = summary.strip('"\'')
                
                return summary
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return "Experienced IT professional with a track record of improving system reliability and efficiency."
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return "Experienced IT professional with a track record of improving system reliability and efficiency." 