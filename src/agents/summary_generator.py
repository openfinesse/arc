#!/usr/bin/env python3
import json
from typing import Dict, Any, List

from .base_agent import Agent

class SummaryGenerator(Agent):
    """
    Agent responsible for generating a resume summary that highlights key 
    skills and experiences relevant to the job description.
    """
    
    def __init__(self):
        super().__init__(name="SummaryGenerator")
    
    def run(self, constructed_sentences: Dict[str, Any], job_description: str) -> str:
        """
        Generate a resume summary that highlights key skills and experiences relevant to the job description.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description (potentially enriched)
            
        Returns:
            str: The generated resume summary
        """
        if not self.openai_api_key:
            # Return a basic summary if no API key
            self.logger.warning("No OpenAI API key available. Using generic summary.")
            return "Experienced professional with a track record of success in relevant fields."
        
        self.logger.info("Generating resume summary...")
        
        # Get relevant information from the constructed sentences
        relevant_info = self._extract_relevant_info(constructed_sentences)
        
        # Generate the summary
        return self._generate_summary_with_ai(relevant_info, job_description)
    
    def _extract_relevant_info(self, constructed_sentences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant information from the constructed sentences for use in the summary.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            
        Returns:
            Dict[str, Any]: Relevant information for the summary
        """
        # Extract titles, companies, and a sample of responsibilities
        titles = []
        companies = []
        responsibilities = []
        
        for role_idx, role_data in constructed_sentences.items():
            # Add title and company
            titles.append(role_data["title"])
            companies.append(role_data["company"])
            
            # Add a sample of responsibilities
            for group_name, sentence in role_data.get("sentences", {}).items():
                responsibilities.append(sentence)
        
        return {
            "titles": titles,
            "companies": companies,
            "responsibilities": responsibilities[:5]  # Limit to 5 responsibilities
        }
    
    def _generate_summary_with_ai(self, relevant_info: Dict[str, Any], job_description: str) -> str:
        """
        Use AI to generate a resume summary that highlights key skills and experiences.
        
        Args:
            relevant_info (Dict[str, Any]): Relevant information for the summary
            job_description (str): The job description
            
        Returns:
            str: The generated resume summary
        """
        # Format the relevant information
        titles_text = ", ".join(relevant_info["titles"][:3])  # Limit to 3 titles
        companies_text = ", ".join(relevant_info["companies"][:3])  # Limit to 3 companies
        responsibilities_text = "\n".join([f"- {r}" for r in relevant_info["responsibilities"]])
        
        prompt = f"""
        I need a professional resume summary that highlights my key skills and experiences relevant to a specific job.
        
        My Roles:
        Titles: {titles_text}
        Companies: {companies_text}
        
        Sample Responsibilities/Accomplishments:
        {responsibilities_text}
        
        Job Description:
        {job_description}
        
        Create a concise, professional resume summary that:
        1. Is 2-3 sentences long
        2. Positions me as a strong candidate for this specific role
        3. Highlights skills and experiences that match the job requirements
        4. Avoids clichés and focuses on concrete achievements
        5. Uses strong, professional language
        6. Is written in first person without using "I" statements
        
        Return only the summary text with no additional comments or formatting.
        """
        
        system_message = "You are a professional resume writer who creates tailored resume summaries."
        
        summary = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.6
        )
        
        if not summary:
            self.logger.error("Failed to generate summary. Using generic summary.")
            return "Experienced professional with a track record of success in relevant fields."
        
        self.logger.debug(f"Generated summary: {summary[:50]}...")
        return summary.strip('"\'') # Remove any quotes that might be in the response 