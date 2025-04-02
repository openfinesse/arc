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
        
        # Track sentence patterns to avoid repetition
        self.used_sentence_starters = set()
        self.used_sentence_structures = set()
        self.all_generated_sentences = []
    
    def run(self, group_data: Dict[str, Any], job_description: str, feedback: Optional[str] = None) -> str:
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
            return self._construct_sentence_fallback(group_data)
        
        print("Constructing tailored sentence...")
        
        if feedback:
            print(f"Using feedback: {feedback}")
        
        return self._construct_sentence_with_ai(group_data, job_description, feedback)
    
    def _construct_sentence_with_ai(self, group_data: Dict[str, Any], job_description: str, feedback: Optional[str] = None) -> str:
        """
        Use AI to construct a complete sentence that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            
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
        
        # Format previously generated sentences to avoid repetition
        used_patterns_str = ""
        if self.all_generated_sentences:
            used_patterns_str = "Previously generated sentences (Avoid overusing the same action verbs or phrases):\n"
            used_patterns_str += "\n".join([f"- {sentence}" for sentence in self.all_generated_sentences[-5:]])
        
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
        
        {used_patterns_str}
        
        {'Feedback from previous attempt: ' + feedback if feedback else ''}
        
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
        
        constructed_sentence = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3
        )
        
        # If API call failed, use fallback method
        if not constructed_sentence:
            return self._construct_sentence_fallback(group_data)
        
        # Clean up the response - sometimes the AI adds quotes
        constructed_sentence = constructed_sentence.strip('"\'')
        print(f"Constructed sentence: {constructed_sentence}")
        
        # Track sentence patterns
        first_word = constructed_sentence.split()[0].lower() if constructed_sentence else ""
        self.used_sentence_starters.add(first_word)
        
        # Add to list of all generated sentences
        self.all_generated_sentences.append(constructed_sentence)
        
        return constructed_sentence
            
    def _construct_sentence_fallback(self, group_data: Dict[str, Any]) -> str:
        """
        Fallback method to return the original sentence without using AI.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            
        Returns:
            str: The constructed sentence
        """
        original_sentence = group_data.get("original_sentence", "")
        modular_sentence = group_data.get("modular_sentence", [])
        variables = group_data.get("variables", {})
        
        if original_sentence:
            return original_sentence
        
        return "No sentence could be constructed." 