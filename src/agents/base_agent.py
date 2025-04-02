#!/usr/bin/env python3
import os
import requests
import json
from typing import Dict, Any, Optional, Union, List, Tuple

class Agent:
    """
    Base Agent class that provides common functionality for all agents
    in the resume customization workflow.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base agent with common API configurations.
        
        Args:
            name (str): The name of the agent for logging purposes
        """
        self.name = name
        
        # Get API keys from environment variables
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        
        # Common API URLs
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
        self.perplexity_api_url = "https://api.perplexity.ai/chat/completions"
        self.anthropic_api_url = "https://api.anthropic.com/v1/messages"
        self.tavily_api_url = "https://api.tavily.com/search"
        self.openrouter_api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def call_llm_api(self, 
                     prompt: str, 
                     system_message: str = "", 
                     model: str = "gpt-4o-mini", 
                     temperature: float = 0.5,
                     response_format: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Make a call to the appropriate provider API with standardized error handling.
        
        Args:
            prompt (str): The prompt to send to the API
            system_message (str, optional): The system message to use. Defaults to "".
            model (str, optional): The model to use. Defaults to "deepseek/deepseek-chat-v3-0324".
            temperature (float, optional): The temperature parameter. Defaults to 0.5.
            response_format (Dict[str, Any], optional): Format specification for structured outputs. Defaults to None.
            
        Returns:
            Optional[str]: The response content or None if the call failed
        """
        # Default system message if not provided
        if not system_message:
            system_message = "You are a helpful assistant."

        # Set the API URL, key, and provider type based on the model selected
        # OpenRouter API
        if model.startswith("openai/") or model.startswith("anthropic/") or model.startswith("meta/") or model.startswith("google/") or model.startswith("deepseek/"):
            if not self.openrouter_api_key:
                print(f"{self.name}: OpenRouter API key not set. Skipping API call.")
                return None
            api_url = self.openrouter_api_url
            api_key = self.openrouter_api_key
            provider = "OpenRouter"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }
            
        # Perplexity API
        elif model.startswith("sonar"):
            if not self.perplexity_api_key:
                print(f"{self.name}: Perplexity API key not set. Skipping API call.")
                return None
            # print(f"{self.name}: Calling Perplexity API with model {model}")
            api_url = self.perplexity_api_url
            api_key = self.perplexity_api_key
            provider = "Perplexity"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }
            
            # Add response_format if provided (for structured outputs)
            if response_format:
                data["response_format"] = response_format
            
        # Anthropic API
        elif any(name in model for name in ["claude", "opus", "sonnet", "haiku"]):
            if not self.anthropic_api_key:
                print(f"{self.name}: Anthropic API key not set. Skipping API call.")
                return None
            # print(f"{self.name}: Calling Anthropic API with model {model}")
            api_url = self.anthropic_api_url
            api_key = self.anthropic_api_key
            provider = "Anthropic"
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Anthropic has a different request format
            data = {
                "model": model,
                "system": system_message,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 2000
            }
            
        # OpenAI API (default)
        else:
            if not self.openai_api_key:
                print(f"{self.name}: OpenAI API key not set. Skipping API call.")
                return None
            # print(f"{self.name}: Calling OpenAI API with model {model}")
            api_url = self.openai_api_url
            api_key = self.openai_api_key
            provider = "OpenAI"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }
        
        try:
            response = requests.post(api_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response based on provider
                if provider == "Anthropic":
                    return result.get("content", [{}])[0].get("text", "").strip()
                else:  # OpenAI and Perplexity have the same response format
                    return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"{self.name}: Error from {provider} API: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"{self.name}: Exception when calling {provider} API: {e}")
            return None
    
    def call_tavily_api(self, query: str, search_depth: str = "basic", 
                       include_domains: List[str] = None, 
                       max_results: int = 5) -> Optional[Dict[str, Any]]:
        """
        Make a call to the Tavily API with standardized error handling.
        
        Args:
            query (str): The search query
            search_depth (str, optional): The search depth. Defaults to "basic".
            include_domains (List[str], optional): Domains to include. Defaults to None.
            max_results (int, optional): Maximum number of results. Defaults to 5.
            
        Returns:
            Optional[Dict[str, Any]]: The response data or None if the call failed
        """
        if not self.tavily_api_key:
            print(f"{self.name}: Tavily API key not set. Skipping API call.")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.tavily_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "query": query,
            "search_depth": search_depth,
            "include_answer": True,
            "max_results": max_results
        }
        
        # Add include_domains if provided
        if include_domains:
            data["include_domains"] = include_domains
        
        try:
            response = requests.post(self.tavily_api_url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"{self.name}: Error from Tavily API: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"{self.name}: Exception when calling Tavily API: {e}")
            return None
    
    def run(self, *args, **kwargs) -> Any:
        """
        Abstract method to be implemented by each agent subclass.
        """
        raise NotImplementedError("Subclasses must implement run()") 