#!/usr/bin/env python3
import os
import requests
import json
import random
from typing import Dict, Any, Optional, List

class SentenceConstructor:
    """
    Agent responsible for constructing complete sentences from base sentences and variations
    that are tailored to the job description.
    """
    
    def __init__(self):
        # Get API key from environment variable for OpenAI (or alternative service)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Using fallback sentence construction method.")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
        # self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Track sentence patterns to avoid repetition
        self.used_sentence_starters = set()
        self.used_sentence_structures = set()
        self.all_generated_sentences = []
    
    def run(self, group_data: Dict[str, Any], job_description: str, feedback: Optional[str] = None) -> str:
        """
        Construct a complete sentence from base sentences and variations that is tailored to the job description.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            job_description (str): The job description (potentially enriched)
            feedback (Optional[str]): Feedback from the reviewer if this is a reconstruction
            
        Returns:
            str: The constructed sentence
        """
        if not self.api_key:
            # Use original sentence if no API key
            return group_data.get("original_sentence", "")
        
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
        base_sentences = group_data.get("base_sentences", [])
        variations = group_data.get("variations", {})
        
        # If no base sentences or variations, return original sentence
        if not base_sentences or not variations:
            return original_sentence
        
        # Format the data for the prompt
        base_sentences_str = "\n".join([f"- {sentence}" for sentence in base_sentences])
        
        variations_str = ""
        for key, values in variations.items():
            variations_str += f"\n{key}:\n"
            variations_str += "\n".join([f"- {value}" for value in values])
        
        # Format previously generated sentences to avoid repetition
        used_patterns_str = ""
        if self.all_generated_sentences:
            used_patterns_str = "Previously generated sentences (avoid overly similar patterns):\n"
            used_patterns_str += "\n".join([f"- {sentence}" for sentence in self.all_generated_sentences[-5:]])
        
        prompt = f"""
        I'm creating a tailored resume for a job application. I need to construct a sentence that describes 
        a responsibility or accomplishment in a way that is relevant to the job I'm applying for.
        
        Original Sentence:
        {original_sentence}
        
        Base Sentence Templates (choose one):
        {base_sentences_str}
        
        Variation Options:
        {variations_str}
        
        Job Description:
        {job_description}
        
        {used_patterns_str}
        
        {'Feedback from previous attempt: ' + feedback if feedback else ''}
        
        Please construct a single sentence that:
        1. Uses one of the base sentence templates
        2. Replaces each {{placeholder}} with an appropriate variation
        3. Is tailored to match keywords and themes from the job description
        4. Does not include the company name
        5. Flows naturally and is grammatically correct
        6. Is professional and impactful
        7. Try not to use the same action word or phrase to start points too much
        9. If any of the last 2 sentences are over 25 words, ensure this one is under 20 words
        
        You may rearrange words slightly for better flow, but maintain the core structure of the chosen base sentence.
        
        Return ONLY the final constructed sentence with no additional explanation or commentary.
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that crafts professional resume points."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2  # Lower temperature for more consistent results
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                constructed_sentence = result["choices"][0]["message"]["content"].strip()
                
                # Clean up the response - sometimes the AI adds quotes
                constructed_sentence = constructed_sentence.strip('"\'')
                print(f"Constructed sentence: {constructed_sentence}")
                
                # Track sentence patterns
                first_word = constructed_sentence.split()[0].lower() if constructed_sentence else ""
                self.used_sentence_starters.add(first_word)
                
                # Add to list of all generated sentences
                self.all_generated_sentences.append(constructed_sentence)
                
                return constructed_sentence
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return original_sentence
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return original_sentence
            
    def _construct_sentence_fallback(self, group_data: Dict[str, Any]) -> str:
        """
        Fallback method to return the original sentence without using AI.
        
        Args:
            group_data (Dict[str, Any]): Data for a responsibility/accomplishment group
            
        Returns:
            str: The constructed sentence
        """
        original_sentence = group_data.get("original_sentence", "")
        base_sentences = group_data.get("base_sentences", [])
        variations = group_data.get("variations", {})
        
        if original_sentence:
            return original_sentence
        else:
            # Select a random base sentence
            base_sentence = random.choice(base_sentences)
            
        # Replace placeholders with random variations
        for placeholder, options in variations.items():
            placeholder_tag = "{" + placeholder + "}"
            if placeholder_tag in base_sentence and options:
                replacement = random.choice(options)
                base_sentence = base_sentence.replace(placeholder_tag, replacement)
        
        return base_sentence 