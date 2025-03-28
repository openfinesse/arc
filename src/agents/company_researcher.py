#!/usr/bin/env python3
import os
import requests
import re
import json
from typing import Dict, Tuple, Any

class CompanyResearcher:
    """
    Agent responsible for researching company information using APIs
    and enriching the job description with additional context.
    """
    
    def __init__(self):
        # Get API keys from environment variables
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not self.tavily_api_key:
            print("Warning: TAVILY_API_KEY environment variable not set.")
            print("Company research capabilities will be limited.")
        
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Company extraction and description enrichment will be limited.")
        
        self.tavily_api_url = "https://api.tavily.com/search"
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
    
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
        company_name = self._extract_company_name_with_openai(job_description)
        
        if not company_name:
            company_name = self._extract_company_name(job_description)
            
        if not company_name:
            print("Could not extract company name from job description.")
            return {}, job_description
        
        print(f"Researching company: {company_name}")
        
        # Research company using Tavily API
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
    
    def _extract_company_name_with_openai(self, job_description: str) -> str:
        """
        Use OpenAI to extract the company name from the job description.
        
        Args:
            job_description (str): The job description
            
        Returns:
            str: The extracted company name
        """
        if not self.openai_api_key:
            print("OpenAI API key not set. Skipping AI-based company name extraction.")
            return ""
        
        prompt = f"""
        Extract the company name from the following job description. 
        Return ONLY the company name, nothing else.
        
        Job Description:
        {job_description[:2000]}  # Limit to first 2000 characters
        """
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts company names from job descriptions."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(self.openai_api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return ""
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return ""
    
    def _research_company(self, company_name: str) -> Dict[str, Any]:
        """
        Research company information using Tavily API.
        
        Args:
            company_name (str): The name of the company
            
        Returns:
            Dict[str, Any]: Information about the company
        """
        if not self.tavily_api_key:
            print("Tavily API key not set. Skipping company research.")
            return {
                "name": company_name,
                "industry": "",
                "description": "",
                "values": [],
                "products": [],
                "tech_stack": []
            }
        
        # Prepare search queries for different aspects of the company
        search_queries = [
            f"{company_name} company description overview",
            f"{company_name} products services offerings",
            f"{company_name} company culture values mission",
            f"{company_name} technology stack tech stack"
        ]
        
        company_info = {
            "name": company_name,
            "description": "",
            "values": [],
            "products": [],
            "tech_stack": []
        }
        
        headers = {
            "Authorization": f"Bearer {self.tavily_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Collect information from multiple searches
            for query in search_queries:
                data = {
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_domains": ["linkedin.com", "bloomberg.com", "reuters.com", "techcrunch.com", "forbes.com"],
                    "max_results": 5
                }
                
                response = requests.post(self.tavily_api_url, headers=headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    
                    # Process the search results
                    if "answer" in result:
                        answer = result["answer"]
                        
                        # Extract relevant information based on the query
                        if "description" in query:
                            company_info["description"] = answer
                        elif "products" in query:
                            company_info["products"] = [p.strip() for p in answer.split(",")]
                        elif "culture" in query:
                            company_info["values"] = [v.strip() for v in answer.split(",")]
                        elif "technology" in query:
                            company_info["tech_stack"] = [t.strip() for t in answer.split(",")]
                    
                    # Also process individual results for additional context
                    if "results" in result:
                        for res in result["results"]:
                            if "content" in res:
                                content = res["content"]
                                # Extract any additional relevant information
                                if "description" in query and not company_info["description"]:
                                    company_info["description"] = content[:200]  # First 200 chars
                                elif "products" in query and not company_info["products"]:
                                    company_info["products"] = [p.strip() for p in content.split(",")[:3]]
                                elif "culture" in query and not company_info["values"]:
                                    company_info["values"] = [v.strip() for v in content.split(",")[:3]]
                                elif "technology" in query and not company_info["tech_stack"]:
                                    company_info["tech_stack"] = [t.strip() for t in content.split(",")[:3]]
                else:
                    print(f"Error from Tavily API: {response.status_code} {response.text}")
            
            return company_info
            
        except Exception as e:
            print(f"Exception when calling Tavily API: {e}")
            return {"name": company_name}
    
    def _enrich_job_description(self, job_description: str, company_info: Dict[str, Any]) -> str:
        """
        Enrich the job description with company information.
        
        Args:
            job_description (str): The original job description
            company_info (Dict[str, Any]): Information about the company
            
        Returns:
            str: Enriched job description
        """
        if not self.openai_api_key or not company_info:
            return job_description
        
        prompt = f"""
        I have a job description and additional company information. 
        Please enhance the job description by incorporating relevant company information,
        but maintain the essence of the original job description.
        
        Original Job Description:
        {job_description}
        
        Company Information:
        {json.dumps(company_info, indent=2)}
        
        Enhanced Job Description:
        """
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that enhances job descriptions."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(self.openai_api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return job_description
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return job_description 