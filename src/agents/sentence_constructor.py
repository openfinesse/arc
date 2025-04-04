#!/usr/bin/env python3
import random
from typing import Dict, Any, Optional, List

from .base_agent import Agent

class SentenceConstructor(Agent):
    """
    Agent responsible for constructing complete sentences from base sentences and variables
    that are tailored to the job description.
    """
    
    def __init__(self):
        super().__init__(name="SentenceConstructor")
        
        # Maps sentence IDs to their assigned action verbs
        self.assigned_action_verbs = {}
    
    async def run(self, group_data: Dict[str, Any], job_description: str, feedback: Optional[str] = None) -> str:
        """
        Construct a complete sentence from base sentences and variables that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description (potentially enriched)
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            
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
        
        sentence_id = group_data.get("id", "")
        # If we already have an assigned action verb for this sentence, use it
        if sentence_id and sentence_id in self.assigned_action_verbs:
            self.logger.debug(f"Using pre-assigned action verb: {self.assigned_action_verbs[sentence_id]}")
            return await self._construct_sentence_with_ai(group_data, job_description, feedback, 
                                                   assigned_action_verb=self.assigned_action_verbs[sentence_id])
        else:
            return await self._construct_sentence_with_ai(group_data, job_description, feedback)
    
    def plan_action_verbs(self, all_group_data: List[Dict[str, Any]], job_description: str) -> None:
        """
        Do a first pass to select action verbs for all sentences to avoid repetition.
        This method remains synchronous as requested.
        
        Args:
            all_group_data (List[Dict[str, Any]]): Data for all responsibility/accomplishment groups
            job_description (str): The job description
        """
        if not self.openai_api_key or not all_group_data:
            return
        
        self.logger.info("Planning action verbs for all sentences...")
        
        # Prepare data for each sentence
        sentence_data = []
        for i, group in enumerate(all_group_data):
            sentence_id = group.get("id", f"sentence_{i}")
            original_sentence = group.get("original_sentence", "")
            modular_sentence = group.get("modular_sentence", [])
            action_module = modular_sentence[0] if modular_sentence else ""
            role = group.get("role", "")
            
            # Get action verb variables if available
            action_variables = []
            variables = group.get("variables", {})
            for var_name, var_values in variables.items():
                if var_name in action_module:
                    action_variables = var_values
                    break
            
            sentence_data.append({
                "id": sentence_id,
                "original_sentence": original_sentence,
                "action_module": action_module,
                "action_variables": action_variables,
                "role": role
            })
        
        # Prepare the prompt
        sentence_details = "\n\n".join([
            f"Sentence {i+1} (Role: {data['role']}):\n" +
            f"Original: {data['original_sentence']}\n" +
            f"Action module: {data['action_module']}\n" +
            f"Available action variables: {', '.join(data['action_variables'])}"
            for i, data in enumerate(sentence_data)
        ])
        
        prompt = f"""
        I'm creating a tailored resume with multiple bullet points. I need to select appropriate action verbs 
        for each sentence to ensure variety and relevance to the job description.
        
        Job Description:
        {job_description}
        
        Sentence Details:
        {sentence_details}
        
        For each sentence, select ONE action verb from its available variables or suggest a new one if none are suitable.
        
        Rules:
        1. Don't repeat action verbs within the same role
        2. Don't use the same action verb more than twice across all sentences
        3. Choose action verbs that align with the job description when possible
        4. If suggesting a new action verb, ensure it's professionally appropriate and fits the context
        
        Return ONLY a JSON object mapping sentence IDs to their assigned action verbs, like:
        {{
          "sentence_1": "Developed",
          "sentence_2": "Managed",
          ...
        }}
        """
        
        system_message = "You are a helpful assistant that selects professional and varied action verbs for resume bullet points."
        
        response = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3
        )
        
        if not response:
            self.logger.error("Failed to plan action verbs")
            return
        
        try:
            import json
            # Extract JSON object from response (in case there's any text around it)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            action_verbs = json.loads(response)
            self.assigned_action_verbs = action_verbs
            self.logger.debug(f"Planned action verbs: {action_verbs}")
        except Exception as e:
            self.logger.error(f"Error parsing action verb planning response: {e}")
    
    async def _construct_sentence_with_ai(self, group_data: Dict[str, Any], job_description: str, 
                                    feedback: Optional[str] = None, assigned_action_verb: Optional[str] = None) -> str:
        """
        Use AI to construct a complete sentence that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            assigned_action_verb (Optional[str]): Pre-selected action verb from planning step
            
        Returns:
            str: The constructed sentence
        """
        # Get values from group_data
        original_sentence = group_data.get("original_sentence", "")
        modular_sentence = group_data.get("modular_sentence", [])
        variables = group_data.get("variables", {})
        
        # If no base sentences or variables, return original sentence
        if not modular_sentence or not variables:
            return original_sentence
        
        variables_str = ""
        for key, values in variables.items():
            variables_str += f"\n{key}:\n"
            variables_str += "\n".join([f"- {value}" for value in values])
        
        assigned_verb_str = ""
        if assigned_action_verb:
            assigned_verb_str = f"Use '{assigned_action_verb}' as the starting action verb for this sentence."
        
        prompt = f"""
        I'm creating a tailored resume for a job application. I need to construct a sentence that describes 
        a responsibility or accomplishment in a way that is relevant to the job I'm applying for.
        
        Original Sentence:
        {original_sentence}
        
        Modular Sentence Template:
        {modular_sentence}
        
        Available Variables:
        {variables_str}
        
        Job Description:
        {job_description}
        
        {'Feedback from previous attempt: ' + feedback if feedback else ''}
        
        {assigned_verb_str}
        
        Please construct a single sentence that:
        1. Has each {{placeholder}} replaced with the most relevant variable from the available variables, tailored to the job description
        2. Does not include the company name
        3. Flows naturally and is grammatically correct

        Notes:
        - For any option, choose the more concise variable, EXCEPT when a more verbose variable matches a part of the job description better, or when the more concise variable would make the sentence awkward or unnatural.
        - You may cautiously rearrange words slightly in cases where not doing so would make the sentence awkward or unnatural. Maintain the core structure of the chosen modular sentence.
        
        Return ONLY the final constructed sentence with no additional explanation or commentary.
        """
        
        system_message = "You are a helpful assistant that crafts professional resume points."
        
        constructed_sentence = await self.call_llm_api_async(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3
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