#!/usr/bin/env python3
import json
from typing import Dict, Any

from .base_agent import Agent

class SummaryGenerator(Agent):
    """
    Agent responsible for creating a resume summary based on the completed points,
    job description, and company information.
    """
    
    def __init__(self):
        super().__init__(name="SummaryGenerator")
    
    def run(self, constructed_sentences: Dict[str, Any], job_description: str) -> str:
        """
        Create a resume summary based on the completed points, job description, and company information.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description (potentially enriched)
            
        Returns:
            str: The generated resume summary
        """
        if not self.openai_api_key:
            # Return a basic summary if no API key
            return "Professional with experience in IT and systems administration seeking new opportunities."
        
        print("Generating resume summary...")
        
        return self._generate_summary_with_ai(constructed_sentences, job_description)
    
    def _generate_summary_with_ai(self, constructed_sentences: Dict[str, Any], job_description: str) -> str:
        """
        Use AI to generate a resume summary.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description
            
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
        
        prompt = f"""
        I need you to create a compelling resume summary for a job application. This summary should
        succinctly highlight my most relevant qualifications, skills, and experience for the specific role,
        while aligning with the company's values and culture.
        
        Resume Content:
        {chr(10).join(resume_content)}
        
        Job Description:
        {job_description}
        
        Please write a professional, impactful resume summary (3-5 sentences) that:
        
        1. Captures my professional identity in a way that aligns with the job
        2. Written in silent first person (no pronouns) and doesn't mention the company name
        3. Highlights my most relevant skills and accomplishments for this specific role
        4. Implicitly speaks to the company's values or culture if relevant
        5. Includes a strong statement about what I can bring to the role
        6. Is concise
        7. Is easy to read
        
        Return ONLY the summary as plaintext without any additional commentary or explanation.
        """
        
        system_message = """
        You are a professional resume writer who creates compelling resume summaries.
        Avoid the unnecessary use of jargon or excessively grandiose/pretentious language that may obfuscate the message rather than enhance it. 
        Instead, describe actions and outcomes directly and succinctly, emphasizing concrete results and specific skills. 
        The goal is to communicate value effectively. Use simple yet professional language to convey effectiveness and efficiency without 
        resorting to common buzzwords or industry clichés. For every task or achievement, quantify the impact where possible.
        """
        
        summary = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7
        )
        
        if not summary:
            return "Experienced IT professional with a track record of improving system reliability and efficiency."
            
        # Clean up the summary - sometimes the AI adds quotes
        summary = summary.strip('"\'')
        
        return summary 