#!/usr/bin/env python3
import os
import requests
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Union, List, Tuple

# Import logging module
try:
    # Try relative import
    from ..logging_config import get_class_logger, log_async_start, log_async_complete
except ImportError:
    # Try absolute import
    from logging_config import get_class_logger, log_async_start, log_async_complete

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
        
        # Set up logger
        self.logger = get_class_logger(self.__class__)
        
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
        
        self.logger.debug(f"Initialized {self.name} agent")
    
    def workflow_step(self, step_num: int, total_steps: int, message: str):
        """
        Log a major workflow step with step number and total steps.
        
        Args:
            step_num (int): Current step number
            total_steps (int): Total number of steps
            message (str): Description of the current step
        """
        self.logger.info(f"[{step_num}/{total_steps}] {message}")
    
    def progress_update(self, current: int, total: int, operation: str):
        """
        Log a progress update for a multi-part operation.
        
        Args:
            current (int): Current progress
            total (int): Total items to process
            operation (str): Description of the operation
        """
        # Only log at INFO level for 25%, 50%, 75% and 100% progress
        if current == 1 or current == total or current % max(1, (total // 4)) == 0:
            self.logger.info(f"{operation}... ({current}/{total} complete)")
        else:
            self.logger.debug(f"{operation}... ({current}/{total} complete)")
    
    def call_llm_api(self, 
                     prompt: str, 
                     system_message: str = "", 
                     model: str = "openrouter/quasar-alpha", 
                     temperature: float = 0.5,
                     response_format: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Make a call to the appropriate provider API with standardized error handling.
        Kept for backward compatibility with plan_action_verbs.
        
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
        if model.startswith("openai/") or model.startswith("anthropic/") or model.startswith("meta/") or model.startswith("google/") or model.startswith("deepseek/") or model.startswith("openrouter/"):
            if not self.openrouter_api_key:
                self.logger.error(f"OpenRouter API key not set. Skipping API call.")
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
                self.logger.error(f"Perplexity API key not set. Skipping API call.")
                return None
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
                self.logger.error(f"Anthropic API key not set. Skipping API call.")
                return None
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
                self.logger.error(f"OpenAI API key not set. Skipping API call.")
                return None
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
            self.logger.debug(f"Calling {provider} API with model {model}")
            response = requests.post(api_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response based on provider
                if provider == "Anthropic":
                    return result.get("content", [{}])[0].get("text", "").strip()
                else:  # OpenAI and Perplexity have the same response format
                    return result["choices"][0]["message"]["content"].strip()
            else:
                self.logger.error(f"Error from {provider} API: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Exception when calling {provider} API: {e}")
            return None
    
    async def call_llm_api_async(self, 
                           prompt: str, 
                           system_message: str = "", 
                           model: str = "openrouter/quasar-alpha", 
                           temperature: float = 0.5,
                           response_format: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Async version: Make a call to the appropriate provider API with standardized error handling.
        
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
        if model.startswith("openai/") or model.startswith("anthropic/") or model.startswith("meta/") or model.startswith("google/") or model.startswith("deepseek/") or model.startswith("openrouter/"):
            if not self.openrouter_api_key:
                self.logger.error(f"OpenRouter API key not set. Skipping API call.")
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
                self.logger.error(f"Perplexity API key not set. Skipping API call.")
                return None
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
                "temperature": temperature,
                "search_recency_filter": "year",
                "web_search_options": {
                    "search_context_size": "high"
                }
            }
            
            # Add response_format if provided (for structured outputs)
            if response_format:
                data["response_format"] = response_format
            
        # Anthropic API
        elif any(name in model for name in ["claude", "opus", "sonnet", "haiku"]):
            if not self.anthropic_api_key:
                self.logger.error(f"Anthropic API key not set. Skipping API call.")
                return None
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
                self.logger.error(f"OpenAI API key not set. Skipping API call.")
                return None
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
            self.logger.debug(f"Calling {provider} API asynchronously with model {model}")
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Parse response based on provider
                        if provider == "Anthropic":
                            return result.get("content", [{}])[0].get("text", "").strip()
                        else:  # OpenAI and Perplexity have the same response format
                            return result["choices"][0]["message"]["content"].strip()
                    else:
                        response_text = await response.text()
                        self.logger.error(f"Error from {provider} API: {response.status}")
                        self.logger.error(f"Response: {response_text}")
                        return None
        except Exception as e:
            self.logger.error(f"Exception when calling {provider} API: {e}")
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
            self.logger.error(f"Tavily API key not set. Skipping API call.")
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
            self.logger.debug(f"Calling Tavily API with query: {query}")
            response = requests.post(self.tavily_api_url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Error from Tavily API: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Exception when calling Tavily API: {e}")
            return None
    
    async def call_tavily_api_async(self, query: str, search_depth: str = "basic", 
                                  include_domains: List[str] = None, 
                                  max_results: int = 5) -> Optional[Dict[str, Any]]:
        """
        Async version: Make a call to the Tavily API with standardized error handling.
        
        Args:
            query (str): The search query
            search_depth (str, optional): The search depth. Defaults to "basic".
            include_domains (List[str], optional): Domains to include. Defaults to None.
            max_results (int, optional): Maximum number of results. Defaults to 5.
            
        Returns:
            Optional[Dict[str, Any]]: The response data or None if the call failed
        """
        if not self.tavily_api_key:
            self.logger.error(f"Tavily API key not set. Skipping API call.")
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
            
        self.logger.debug(f"Calling Tavily API asynchronously with query: {query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.tavily_api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        response_text = await response.text()
                        self.logger.error(f"Error from Tavily API: {response.status}")
                        self.logger.error(f"Response: {response_text}")
                        return None
        except Exception as e:
            self.logger.error(f"Exception when calling Tavily API: {e}")
            return None
    
    async def run(self, *args, **kwargs) -> Any:
        """
        Execute the agent's main logic. This method should be overridden by subclasses.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Returns:
            Any: The result of the agent's execution
        """
        func_name = f"{self.__class__.__name__}.run"
        log_async_start(self.logger, func_name)
        
        # This should be overridden by subclasses
        result = None
        
        log_async_complete(self.logger, func_name)
        return result 