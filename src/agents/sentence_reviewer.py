#!/usr/bin/env python3
from typing import Tuple

from .base_agent import Agent

class SentenceReviewer(Agent):
    """
    Agent responsible for reviewing constructed sentences for readability and grammar.
    """
    
    def __init__(self):
        super().__init__(name="SentenceReviewer")
    
    def run(self, sentence: str) -> Tuple[bool, str]:
        """
        Review a constructed sentence for readability and grammar.
        
        Args:
            sentence (str): The sentence to review
            
        Returns:
            Tuple[bool, str]: A tuple containing:
                1. Boolean indicating if the sentence is approved
                2. Feedback or reason for rejection
        """
        if not self.openai_api_key:
            # Default to approving all sentences if no API key
            return True, "No review performed (API key not set)"
        
        print("Reviewing sentence...")
        
        # Check for basic issues
        basic_checks_passed, basic_feedback = self._perform_basic_checks(sentence)
        if not basic_checks_passed:
            return False, basic_feedback
        
        # Use AI for more sophisticated review
        return self._review_sentence_with_ai(sentence)
    
    def _perform_basic_checks(self, sentence: str) -> Tuple[bool, str]:
        """
        Perform basic checks on the sentence without using AI.
        
        Args:
            sentence (str): The sentence to check
            
        Returns:
            Tuple[bool, str]: Approval status and feedback
        """
        # Check if sentence is empty
        if not sentence.strip():
            return False, "Sentence is empty"
        
        # Check if sentence is too short
        if len(sentence.split()) < 8:
            return False, "Sentence is too short"
        
        # Check if sentence is too long
        if len(sentence.split()) > 35:
            return False, "Sentence is too long (exceeds 35 words)"
        
        # Check for placeholders left in the sentence
        if "{" in sentence and "}" in sentence:
            return False, "Sentence contains unreplaced placeholders"
        
        return True, "Basic checks passed"
    
    def _review_sentence_with_ai(self, sentence: str) -> Tuple[bool, str]:
        """
        Use AI to review a sentence for readability and grammar.
        
        Args:
            sentence (str): The sentence to review
            
        Returns:
            Tuple[bool, str]: Approval status and feedback
        """
        prompt = f"""
        Please review the following sentence from a resume for readability, grammar, and professional impact:
        
        "{sentence}"
        
        Evaluate the sentence based on grammar, spelling, punctuation, readability, and effectiveness for a resume.
        
        If the sentence has issues, please explain what they are and provide specific feedback for improvement.
        If the sentence is acceptable, please approve it.
        
        Format your response as:
        APPROVED: Yes/No
        FEEDBACK: [Your feedback here]
        """
        
        system_message = "You are a professional editor who reviews resume content. Be concise in your feedback."
        
        content = self.call_llm_api(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4
        )
        
        if not content:
            # Default to approving if the API call fails
            return True, "API call failed, defaulting to approval"
        
        # Parse the response to get approval status and feedback
        approved = "APPROVED: Yes" in content or "APPROVED:Yes" in content
        
        # Extract feedback
        feedback_parts = content.split("FEEDBACK:")
        if len(feedback_parts) > 1:
            feedback = feedback_parts[1].strip()
        else:
            feedback = "No specific feedback provided"
        
        return approved, feedback 