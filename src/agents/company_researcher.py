#!/usr/bin/env python3
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Tuple, Any, List
import sys
from datetime import datetime, timedelta

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
                self.logger.warning("TAVILY_API_KEY environment variable not set.")
                self.logger.warning("Company research capabilities will be limited.")
        elif self.research_api_provider == "perplexity":
            self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
            if not self.perplexity_api_key:
                self.logger.warning("PERPLEXITY_API_KEY environment variable not set.")
                self.logger.warning("Company research capabilities will be limited.")
        else:
            self.logger.warning(f"Unknown RESEARCH_API_PROVIDER: {self.research_api_provider}")
            self.logger.warning("Defaulting to Tavily for company research.")
            self.research_api_provider = "tavily"
        
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            self.logger.warning("OPENAI_API_KEY environment variable not set.")
            self.logger.warning("Company extraction and description enrichment will be limited.")
            
        # Set up the cache directory
        self.cache_dir = Path("data/company_research")
        self._setup_cache_directory()
    
    def _setup_cache_directory(self):
        """
        Create the cache directory if it doesn't exist
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Cache directory set up at: {self.cache_dir}")
    
    def _get_cache_filename(self, company_name: str) -> Path:
        """
        Generate a cache filename for a company
        
        Args:
            company_name (str): The name of the company
            
        Returns:
            Path: Path to the cache file
        """
        # Create a hash of the company name to use as filename
        # This avoids issues with special characters in company names
        hash_obj = hashlib.md5(company_name.lower().encode())
        filename = hash_obj.hexdigest() + ".json"
        return self.cache_dir / filename
    
    def _load_from_cache(self, company_name: str) -> Dict[str, Any]:
        """
        Load company research from cache if available
        
        Args:
            company_name (str): The name of the company
            
        Returns:
            Dict[str, Any]: Cached company information or empty dict if not found
        """
        cache_file = self._get_cache_filename(company_name)
        
        if cache_file.exists():
            try:
                with cache_file.open('r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is expired (default: 30 days)
                if self._is_cache_valid(cached_data):
                    self.logger.info(f"Using cached research for company: {company_name}")
                    # Remove cache metadata from the returned data
                    if "_cache_timestamp" in cached_data:
                        del cached_data["_cache_timestamp"]
                    if "_cache_company_name" in cached_data:
                        del cached_data["_cache_company_name"]
                    return cached_data
                else:
                    self.logger.info(f"Cached research for {company_name} is expired, refreshing...")
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error reading cache for {company_name}: {e}")
        
        return {}
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """
        Check if the cached data is still valid or if it has expired
        
        Args:
            cached_data (Dict[str, Any]): The cached data with timestamp
            
        Returns:
            bool: True if cache is still valid, False if expired
        """
        # Get cache expiration time from environment variable (default: 30 days)
        cache_days = int(os.environ.get("COMPANY_CACHE_DAYS", "30"))
        
        # If no timestamp is present, consider it expired
        if "_cache_timestamp" not in cached_data:
            return False
            
        try:
            # Parse the timestamp
            cache_time = datetime.fromisoformat(cached_data["_cache_timestamp"])
            # Check if it's older than the expiration time
            return datetime.now() - cache_time < timedelta(days=cache_days)
        except (ValueError, TypeError):
            # If there's an error parsing the timestamp, consider it expired
            return False
    
    def _save_to_cache(self, company_name: str, company_info: Dict[str, Any]) -> bool:
        """
        Save company research to cache
        
        Args:
            company_name (str): The name of the company
            company_info (Dict[str, Any]): Company information to cache
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not company_info:
            return False
            
        cache_file = self._get_cache_filename(company_name)
        
        try:
            # Add timestamp to cache entry
            cache_data = company_info.copy()
            cache_data["_cache_timestamp"] = datetime.now().isoformat()
            cache_data["_cache_company_name"] = company_name
            
            with cache_file.open('w') as f:
                json.dump(cache_data, f, indent=2)
            self.logger.info(f"Saved company research to cache: {company_name}")
            return True
        except IOError as e:
            self.logger.error(f"Error saving cache for {company_name}: {e}")
            return False
    
    def clear_cache(self):
        """
        Clear the company research cache
        """
        if self.cache_dir.exists():
            import shutil
            shutil.rmtree(self.cache_dir)
            self._setup_cache_directory()
            self.logger.info("Company research cache cleared.")
        else:
            self.logger.info("No company research cache found.")
        
    def list_cached_companies(self) -> List[str]:
        """
        List all companies that have been cached
        
        Returns:
            List[str]: List of cached company names
        """
        cached_companies = []
        
        if not self.cache_dir.exists():
            return cached_companies
            
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open('r') as f:
                    data = json.load(f)
                    
                company_name = data.get("_cache_company_name", "Unknown")
                cached_companies.append(company_name)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error reading cache file {cache_file}: {e}")
                
        return cached_companies
    
    async def run(self, job_description: str) -> str:
        """
        Research the company mentioned in the job description and return enriched context.
        
        Args:
            job_description (str): The original job description
            
        Returns:
            str: Enriched job description with additional context
        """
        # Extract company name from job description
        self.logger.debug("Extracting company name from job description...")
        company_name = self._extract_company_name_with_ai(job_description)
        
        if not company_name:
            self.logger.warning("Could not extract company name from job description.")
            return job_description
            
        self.logger.info(f"Found company: {company_name}")
        
        # Check cache first
        company_info = self._load_from_cache(company_name)
        
        # If not in cache, perform company research
        if not company_info:
            self.logger.info(f"Researching company information...")
            company_info = self._research_company(company_name)
            
            # Save research to cache
            if company_info:
                self._save_to_cache(company_name, company_info)
        
        # Enrich job description with company research
        if company_info:
            self.logger.debug("Enriching job description with company information...")
            enriched_description = self._enrich_job_description(job_description, company_info)
            return enriched_description
        
        return job_description
    
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
            self.logger.warning("Tavily API key not set. Skipping company research.")
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
        Research a company using the Perplexity API to get additional information.
        
        Args:
            company_name (str): The name of the company
            company_info (Dict[str, Any]): Existing company information
            
        Returns:
            Dict[str, Any]: Updated company information
        """
        if not self.perplexity_api_key:
            self.logger.warning("Perplexity API key not set. Skipping company research.")
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
                },
                "trends": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of trends the company seems to be following"
                }
            },
            "required": ["description", "industry", "products", "values", "tech_stack", "trends"]
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
        6. Trends the company seems to be following
        
        For any fields where information is not available, provide empty arrays.
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
                parsed_result = self._parse_perplexity_json(result)
                
                # Update company info with the research results
                company_info["description"] = parsed_result.get("description", "")
                company_info["industry"] = parsed_result.get("industry", "")
                company_info["products"] = parsed_result.get("products", [])
                company_info["values"] = parsed_result.get("values", [])
                company_info["tech_stack"] = parsed_result.get("tech_stack", [])
                company_info["trends"] = parsed_result.get("trends", [])

            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON response: {e}")
                self.logger.debug(f"Raw response: {result}")
        
        return company_info
    
    def _parse_perplexity_json(self, result: str) -> Dict[str, Any]:
        """
        Parse the JSON from Perplexity API response (with error handling).
        
        Args:
            result (str): The JSON string to parse
            
        Returns:
            Dict[str, Any]: Parsed JSON or empty dict on error
        """
        try:
            # Find and extract JSON (pattern: {...})
            import re
            json_match = re.search(r'(\{[\s\S]*\})', result)
            if json_match:
                result = json_match.group(1)
            
            # Parse the JSON
            return json.loads(result)
        except Exception as e:
            self.logger.error(f"Error parsing JSON response: {e}")
            self.logger.debug(f"Raw response: {result}")
            return {}
    
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
        Incorporate the information naturally as if it was part of the original description.
        Be selective in the information you use to enrich the job description. Things like values, culture, and trends
        are usually relevant. The tech stack can be relevant, but it might contain technologies that aren't relevant to the specific role.

        Only return the enriched job description, don't include any explanation or other text.

        Original Job Description:
        {job_description}
        
        Company Information:
        Name: {company_info.get("name", "")}
        Industry: {company_info.get("industry", "")}
        Description: {company_info.get("description", "")}
        Values: {", ".join(company_info.get("values", []))}
        Products: {", ".join(company_info.get("products", []))}
        Tech Stack: {", ".join(company_info.get("tech_stack", []))}
        Trends: {", ".join(company_info.get("trends", []))}
        """
        
        system_message = "You are a helpful assistant that enhances job descriptions using research about the respective company."
        
        result = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if result:
            return result
        else:
            return job_description 