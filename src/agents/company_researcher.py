#!/usr/bin/env python3
import os
import re
import json
from typing import Dict, Tuple, Any, List
import sys

from .base_agent import Agent

class CompanyResearcher(Agent):
    """
    Agent responsible for researching company information using APIs
    and enriching the job description with additional context.
    """
    
    def __init__(self):
        super().__init__(name="CompanyResearcher")
        # Get API configuration directly from environment variables
        self.research_api_provider = os.environ.get("RESEARCH_API_PROVIDER", "perplexity").lower()
        
        # Validate API keys based on configured provider
        if self.research_api_provider == "tavily":
            self.tavily_api_key = os.environ.get("TAVILY_API_KEY")
            if not self.tavily_api_key:
                print("Warning: TAVILY_API_KEY environment variable not set.")
                print("Company research capabilities will be limited.")
        elif self.research_api_provider == "perplexity":
            self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
            if not self.perplexity_api_key:
                print("Warning: PERPLEXITY_API_KEY environment variable not set.")
                print("Company research capabilities will be limited.")
        else:
            print(f"Warning: Unknown RESEARCH_API_PROVIDER: {self.research_api_provider}")
            print("Defaulting to Tavily for company research.")
            self.research_api_provider = "tavily"
        
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Company extraction and description enrichment will be limited.")
    
    def run(self, job_description: str) -> Tuple[Dict[str, Any], str]:
        """
        Research the company mentioned in the job description and return enriched context.
        
        Args:
            job_description (str): The original job description
            
        Returns:
            Tuple[Dict[str, Any], str]: A tuple containing:
                1. Company information as a dictionary
                2. Enriched job description with additional context
        """
        # Extract company name from job description
        company_name = self._extract_company_name_with_ai(job_description)
        
        if not company_name:
            company_name = self._extract_company_name(job_description)
            
        if not company_name:
            print("Could not extract company name from job description.")
            return {}, job_description
        
        print(f"Researching company: {company_name}")
        
        # Research company using the configured API provider
        company_info = self._research_company(company_name)
        
        # Enrich job description with company information
        enriched_description = self._enrich_job_description(job_description, company_info)

        return company_info, enriched_description
    
    def _extract_company_name(self, job_description: str) -> str:
        """
        Extract the company name from the job description using regex patterns.
        This is a fallback method if the AI extraction fails.
        
        Args:
            job_description (str): The job description
            
        Returns:
            str: The extracted company name or empty string if not found
        """
        # Try to find common patterns for company names
        patterns = [
            r"at\s+([A-Z][A-Za-z0-9\s&.,]+?)(?:\s+is|\s+are|\s+we|\s*[,.])",
            r"([A-Z][A-Za-z0-9\s&.,]+?)\s+is\s+looking\s+for",
            r"About\s+([A-Z][A-Za-z0-9\s&.,]+?)[\s+:]",
            r"Join\s+([A-Z][A-Za-z0-9\s&.,]+?)[\s+,.]",
            r"with\s+([A-Z][A-Za-z0-9\s&.,]+?)[\s+,.]"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, job_description)
            if matches:
                return matches.group(1).strip()
        
        return ""
    
    def _extract_company_name_with_ai(self, job_description: str) -> str:
        """
        Use OpenAI to extract the company name from the job description.
        
        Args:
            job_description (str): The job description
            
        Returns:
            str: The extracted company name
        """
        prompt = f"""
        Extract the company name from the following job description. 
        Return ONLY the company name, nothing else.
        
        Job Description:
        {job_description[:2000]}  # Limit to first 2000 characters
        """
        
        system_message = "You are a helpful assistant that extracts company names from job descriptions."
        
        result = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.2
        )
        
        return result if result else ""
    
    def _research_company(self, company_name: str) -> Dict[str, Any]:
        """
        Research company information using the configured API provider.
        
        Args:
            company_name (str): The name of the company
            
        Returns:
            Dict[str, Any]: Information about the company
        """
        # Default company info structure
        company_info = {
            "name": company_name,
            "industry": "",
            "description": "",
            "values": [],
            "products": [],
            "tech_stack": []
        }
        
        # Choose research method based on configured provider
        if self.research_api_provider == "tavily":
            company_info = self._research_with_tavily(company_name, company_info)
        elif self.research_api_provider == "perplexity":
            company_info = self._research_with_perplexity(company_name, company_info)
        
        return company_info
    
    def _research_with_tavily(self, company_name: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research company information using Tavily API.
        
        Args:
            company_name (str): The name of the company
            company_info (Dict[str, Any]): Initial company info structure
            
        Returns:
            Dict[str, Any]: Updated information about the company
        """
        if not self.tavily_api_key:
            print("Tavily API key not set. Skipping company research.")
            return company_info
        
        # Prepare search queries for different aspects of the company
        search_queries = [
            f"{company_name} company description overview",
            f"{company_name} products services offerings",
            f"{company_name} company culture values mission",
            f"{company_name} technology stack tech stack"
        ]
        
        # Collect information from multiple searches
        for query in search_queries:
            include_domains = ["linkedin.com", "bloomberg.com", "reuters.com", "techcrunch.com", "forbes.com"]
            result = self.call_tavily_api(
                query=query,
                search_depth="basic",
                include_domains=include_domains,
                max_results=5
            )
            
            if result and "answer" in result:
                answer = result["answer"]
                
                # Extract relevant information based on the query
                if "description" in query:
                    company_info["description"] = answer
                elif "products" in query:
                    company_info["products"] = [p.strip() for p in answer.split(",")]
                elif "culture" in query:
                    company_info["values"] = [v.strip() for v in answer.split(",")]
                elif "tech stack" in query:
                    company_info["tech_stack"] = [t.strip() for t in answer.split(",")]
        
        return company_info
    
    def _research_with_perplexity(self, company_name: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research company information using Perplexity API with structured JSON output.
        
        Args:
            company_name (str): The name of the company
            company_info (Dict[str, Any]): Initial company info structure
            
        Returns:
            Dict[str, Any]: Updated information about the company
        """
        if not self.perplexity_api_key:
            print("Perplexity API key not set. Skipping company research.")
            return company_info
        
        # Define JSON schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A brief description of the company (about one paragraph)"
                },
                "industry": {
                    "type": "string",
                    "description": "The primary industry the company operates in"
                },
                "products": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of main products or services the company offers"
                },
                "values": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of company values, culture aspects, or mission statements"
                },
                "tech_stack": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of technologies and tech stack used by the company"
                }
            },
            "required": ["description", "industry", "products", "values", "tech_stack"]
        }
        
        # Set up response format for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "schema": json_schema
            }
        }
        
        # Create a prompt that asks for all company information at once
        prompt = f"""
        Research and provide detailed information about the company: {company_name}.
        
        Please return a structured JSON with the following information:
        1. A brief description of the company
        2. The industry the company operates in
        3. Main products or services offered by the company
        4. Company values, culture, and mission
        5. Technologies and tech stack used by the company
        
        For any fields where information is not available, provide empty arrays or best guesses based on similar companies.
        """
        
        system_message = "You are a research assistant providing concise, factual information about companies in a structured format."
        
        # Make a single API call with structured output format
        result = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            model="sonar-pro",
            response_format=response_format
        )
        
        if result:
            try:
                # Parse the JSON response
                parsed_result = json.loads(result)
                
                # Update company info with the research results
                company_info["description"] = parsed_result.get("description", "")
                company_info["industry"] = parsed_result.get("industry", "")
                company_info["products"] = parsed_result.get("products", [])
                company_info["values"] = parsed_result.get("values", [])
                company_info["tech_stack"] = parsed_result.get("tech_stack", [])
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Raw response: {result}")
        
        return company_info
    
    def _enrich_job_description(self, job_description: str, company_info: Dict[str, Any]) -> str:
        """
        Enrich the job description with company information using OpenAI.
        
        Args:
            job_description (str): The original job description
            company_info (Dict[str, Any]): Information about the company
            
        Returns:
            str: The enriched job description
        """
        # If we don't have sufficient company info, return the original
        if not company_info or not company_info.get("description"):
            return job_description
        
        prompt = f"""
        I have a job description and additional research about {company_info.get("name", "")}. 
        Please enrich the job description using the company research to give me a better context.
        
        Original Job Description:
        {job_description}
        
        Company Information:
        Name: {company_info.get("name", "")}
        Industry: {company_info.get("industry", "")}
        Description: {company_info.get("description", "")}
        Values: {", ".join(company_info.get("values", []))}
        Products: {", ".join(company_info.get("products", []))}
        Tech Stack: {", ".join(company_info.get("tech_stack", []))}
        
        Incorporate the information naturally as if it was part of the original description.
        """
        
        system_message = "You are a helpful assistant that enhances job descriptions using research about the respective company."
        
        result = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.5
        )
        
        if result:
            return result
        else:
            return job_description 