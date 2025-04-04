#!/usr/bin/env python3
import random
from typing import Dict, Any, Optional, List
import hashlib

from .base_agent import Agent

class SentenceConstructor(Agent):
    """
    Agent responsible for constructing complete sentences from base sentences and variables
    that are tailored to the job description.
    """
    
    def __init__(self):
        super().__init__(name="SentenceConstructor")
        # We'll use a single source of truth for action verbs
        self.action_verbs = {}
    
    async def run(self, group_data: Dict[str, Any], job_description: str, feedback: Optional[str] = None, 
                  planned_action_verbs: Optional[Dict[str, str]] = None) -> str:
        """
        Construct a complete sentence from base sentences and variables that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description (potentially enriched)
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            planned_action_verbs (Optional[Dict[str, str]]): Pre-planned action verbs from planning step
            
        Returns:
            str: The constructed sentence
        """
        if not self.openai_api_key:
            # Use original sentence if no API key
            self.logger.warning("No OpenAI API key available. Using original sentence.")
            return self._construct_sentence_fallback(group_data)
        
        self.logger.debug("Constructing tailored sentence...")
        
        if feedback:
            self.logger.debug(f"Using feedback: {feedback}")
        
        # Generate a unique, consistent ID for this sentence
        sentence_id = self._generate_sentence_id(group_data)
        self.logger.debug(f"Using sentence ID: {sentence_id}")
        
        # Use planned_action_verbs if provided (from main.py state)
        # Store in our local action_verbs for consistency
        if planned_action_verbs and not self.action_verbs:
            self.action_verbs = planned_action_verbs
        
        # Get the action verb for this sentence if available
        action_verb = None
        if sentence_id in self.action_verbs:
            action_verb = self.action_verbs[sentence_id]
            self.logger.debug(f"Using planned action verb: {action_verb}")
        
        # Construct the sentence using the AI
        return await self._construct_sentence_with_ai(group_data, job_description, feedback, action_verb)
    
    def _generate_sentence_id(self, group_data: Dict[str, Any]) -> str:
        """
        Generate a consistent sentence ID for a group.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            
        Returns:
            str: A consistent ID for the sentence
        """
        # Try to use the group's ID if available
        if "id" in group_data:
            return f"sentence_{group_data['id']}"
        
        # Use original sentence if available (most consistent)
        if "original_sentence" in group_data:
            sentence_hash = hashlib.md5(group_data["original_sentence"].encode()).hexdigest()[:8]
            return f"sentence_{sentence_hash}"
        
        # Use first module as fallback
        if "modular_sentence" in group_data and group_data["modular_sentence"]:
            module_hash = hashlib.md5(group_data["modular_sentence"][0].encode()).hexdigest()[:8]
            return f"sentence_{module_hash}"
        
        # Last resort - use random ID
        return f"sentence_random_{random.randint(1000, 9999)}"
    
    def plan_action_verbs(self, all_group_data: List[Dict[str, Any]], job_description: str) -> Dict[str, str]:
        """
        Select action verbs for selected sentence groups to avoid repetition.
        
        Args:
            all_group_data (List[Dict[str, Any]]): Data for selected responsibility/accomplishment groups
            job_description (str): The job description
            
        Returns:
            Dict[str, str]: Mapping of sentence IDs to their assigned action verbs
        """
        if not self.openai_api_key or not all_group_data:
            return {}
        
        self.logger.info(f"Planning action verbs for {len(all_group_data)} selected groups...")
        
        # Create a mapping of numeric IDs to actual sentence IDs for translation
        numeric_to_actual_id = {}
        sentence_data = []
        
        for i, group in enumerate(all_group_data):
            # Generate consistent ID using same function as in run()
            sentence_id = self._generate_sentence_id(group)
            
            # Create a simple numeric ID for the LLM
            numeric_id = f"sentence_{i+1}"
            numeric_to_actual_id[numeric_id] = sentence_id
            
            original_sentence = group.get("original_sentence", "")
            modular_sentence = group.get("modular_sentence", [])
            action_module = modular_sentence[0] if modular_sentence else ""
            
            # Get action verb variables if available
            action_variables = []
            variables = group.get("variables", {})
            for var_name, var_values in variables.items():
                if var_name in action_module:
                    action_variables = var_values
                    break
            
            sentence_data.append({
                "numeric_id": numeric_id,
                "original_sentence": original_sentence,
                "action_module": action_module,
                "action_variables": action_variables,
                "role": group.get("role", "")
            })
        
        # Log the mapping for debugging
        self.logger.debug(f"ID mapping: {numeric_to_actual_id}")
        
        # Prepare the prompt for the LLM
        sentence_details = "\n\n".join([
            f"{data['numeric_id']} (Role: {data['role']}):\n" +
            f"Original: {data['original_sentence']}\n" +
            f"Action module: {data['action_module']}\n" +
            f"Available action variables: {', '.join(data['action_variables'])}"
            for data in sentence_data
        ])
        
        prompt = f"""
        I'm creating a tailored resume with multiple bullet points. I need to select appropriate action verbs 
        for each sentence to ensure variety and relevance to the job description.
        
        Job Description:
        {job_description}
        
        Sentence Details:
        {sentence_details}
        
        For each sentence, select ONE action verb from its available variables
        
        Rules:
        1. Don't repeat action verbs within the same role
        2. Don't use the same action verb more than twice across all sentences
        3. Choose action verbs that align with the job description
        
        Return ONLY a JSON object mapping sentence IDs to their assigned action verbs, like:
        {{
          "sentence_1": "Developed",
          "sentence_2": "Built and deployed",
          ...
        }}
        """
        
        system_message = "You are a helpful assistant that selects professional and varied action verbs for resume bullet points."
        
        response = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if not response:
            self.logger.error("Failed to plan action verbs")
            return {}
        
        try:
            import json
            import re
            
            # Extract JSON object from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            numeric_action_verbs = json.loads(response)
            
            # Translate numeric IDs to actual sentence IDs
            actual_action_verbs = {}
            for numeric_id, verb in numeric_action_verbs.items():
                if numeric_id in numeric_to_actual_id:
                    actual_id = numeric_to_actual_id[numeric_id]
                    actual_action_verbs[actual_id] = verb
            
            # Store in our instance variable
            self.action_verbs = actual_action_verbs
            
            self.logger.debug(f"Planned action verbs: {actual_action_verbs}")
            return actual_action_verbs
            
        except Exception as e:
            self.logger.error(f"Error parsing action verb planning response: {e}")
            return {}
    
    async def _construct_sentence_with_ai(self, group_data: Dict[str, Any], job_description: str, 
                                    feedback: Optional[str] = None, action_verb: Optional[str] = None) -> str:
        """
        Use AI to construct a complete sentence that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            action_verb (Optional[str]): Pre-selected action verb from planning step
            
        Returns:
            str: The constructed sentence
        """
        # Get values from group_data
        original_sentence = group_data.get("original_sentence", "")
        modular_sentence = group_data.get("modular_sentence", [])
        variables = group_data.get("variables", {}).copy()  # Create a copy to avoid modifying the original
        
        # If no base sentences or variables, return original sentence
        if not modular_sentence or not variables:
            return original_sentence
        
        # Simplified action verb handling
        if action_verb and modular_sentence:
            # Find the first variable in the first module (action verb)
            first_module = modular_sentence[0]
            for var_name in variables.keys():
                if "{" + var_name + "}" in first_module:
                    # Set the action verb directly
                    self.logger.debug(f"Setting action verb '{action_verb}' for variable {var_name}")
                    variables[var_name] = [action_verb]
                    break
        
        # Format variables for the prompt
        variables_str = ""
        for key, values in variables.items():
            variables_str += f"\n{key}:\n"
            variables_str += "\n".join([f"- {value}" for value in values])
        
        prompt = f"""        
        Modular Sentence Template:
        {modular_sentence}
        
        Available Variables:
        {variables_str}

        Job Description:
        {job_description}
        
        {'Feedback from previous attempt: ' + feedback if feedback else ''}
        """
        
        system_message = f"""
        You are a helpful assistant that crafts professional resume points.
        The user will provide you with a modular sentence template and a list of available variables.
        Your job is to construct a resume bullet point that:
        1. Has each {{placeholder}} replaced with the variable that best matches the job description
        2. Flows naturally and is grammatically correct

        Notes:
        - You may cautiously rearrange words slightly in cases where not doing so would make the sentence awkward or unnatural. 
          Maintain the core structure of the chosen modular sentence.
        - Correct any BASIC grammatical errors, punctuation errors, and typos.
        - If the job description makes mention of a specific technology or keyword like AI for example, 
          and there is a variable that has the word "AI" in it, it should be considered.
        - If the job description generally focuses on a specific ecosystem like Microsoft for example, 
          and there are a group of variables from different ecosystems, none of which are explicitly mentioned in the job description, 
          it's probably better to choose the one that is from the Microsoft ecosystem.
        
        Return ONLY the final constructed sentence with no additional explanation or commentary.
        """
        
        constructed_sentence = await self.call_llm_api_async(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        # If API call failed, use fallback method
        if not constructed_sentence:
            return self._construct_sentence_fallback(group_data)
        
        # Clean up the response - sometimes the AI adds quotes
        constructed_sentence = constructed_sentence.strip('"\'')
        self.logger.debug(f"Constructed sentence: {constructed_sentence}")
        
        return constructed_sentence
            
    def _construct_sentence_fallback(self, group_data: Dict[str, Any]) -> str:
        """
        Fallback method to construct a sentence when API calls fail.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            
        Returns:
            str: The constructed sentence
        """
        # If there's an original sentence, return it
        if "original_sentence" in group_data:
            return group_data["original_sentence"]
        
        # Try to construct from modular sentence and variables
        modular_sentence = group_data.get("modular_sentence", [])
        variables = group_data.get("variables", {})
        
        if not modular_sentence:
            self.logger.warning("No original or modular sentence available for fallback construction")
            return "Details not available"
        
        # Construct a basic sentence by selecting random variables
        constructed = ""
        for module in modular_sentence:
            # Check if module is a variable
            for var_name, var_values in variables.items():
                if var_name == module and var_values:
                    # Select a random variable value
                    module = random.choice(var_values)
                    break
            
            constructed += module + " "
        
        constructed_sentence = constructed.strip()
        self.logger.debug(f"Constructed fallback sentence: {constructed_sentence}")
        return constructed_sentence 