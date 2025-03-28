#!/usr/bin/env python3
import os
import requests
import json
import re  # Import re for regex operations
from typing import Dict, Any

class ContentReviewer:
    """
    Agent responsible for reviewing the overall content for relevance and narrative
    across all selected positions and constructed sentences.
    """
    
    def __init__(self):
        # Get API key from environment variable for OpenAI (or alternative service)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Content review will be limited.")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
        # self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def run(self, constructed_sentences: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """
        Review the overall content for relevance and narrative.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description (potentially enriched)
            
        Returns:
            Dict[str, Any]: Review results and suggestions
        """
        if not self.api_key:
            # Return a basic review if no API key
            return {"overall_assessment": "No review performed (API key not set)"}
        
        print("Reviewing overall content...")
        
        return self._review_content_with_ai(constructed_sentences, job_description)
    
    def _review_content_with_ai(self, constructed_sentences: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """
        Use AI to review the overall content for relevance and narrative.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            job_description (str): The job description
            
        Returns:
            Dict[str, Any]: Review results and suggestions
        """
        # Prepare the content for review
        content_for_review = []
        
        for role_idx, role_data in constructed_sentences.items():
            role_content = f"### {role_data['title']} | {role_data['company']}\n"
            role_content += f"*{role_data['start_date']} - {role_data['end_date']}* | {role_data['location']}\n\n"
            
            for group_name, sentence in role_data.get("sentences", {}).items():
                role_content += f"- {sentence}\n"
            
            content_for_review.append(role_content)
        
        prompt = f"""
        I need you to review the content of a resume that I'm tailoring for a specific job.
        Please analyze how well the resume content aligns with the job description and
        suggest improvements to make it more compelling if applicable.
        
        Resume Content:
        {chr(10).join(content_for_review)}
        
        Job Description:
        {job_description}
        
        Please provide a thorough review that addresses:
        
        1. Overall alignment: How well does the content align with the job requirements?
        2. Key skills coverage: Are all the key skills from the job description represented?
        3. Narrative strength: Do the bullet points tell a coherent story about my experience?
        4. Missing elements: What important aspects of the job description are not covered?
        5. Redundancies: Are there any points that are redundant or could be combined?
        6. Clutter: Are there any points that are too long and can be divided into multiple points?
        7. Job title suggestions: Based on the job description, which title variations would be most effective?
        
        Format your response as a JSON object with the following structure:
        ```json
        {{
            "overall_alignment": "1-10 score and brief explanation",
            "key_skills": {{
                "covered": ["list of covered skills"],
                "missing": ["list of missing skills"]
            }},
            "narrative_assessment": "brief assessment of the narrative strength",
            "redundancies": ["list of any redundant points"],
            "suggested_improvements": ["list of specific improvements"],
            "clutter": ["list of any points that are too long and can be divided into multiple points"],
            "title_recommendations": {{
                "role_0": "recommended title variation for first role",
                "role_1": "recommended title variation for second role",
                ...
            }}
        }}
        ```
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o",
            # "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": "You are a professional resume reviewer with expertise in tailoring resumes to specific job descriptions."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.55  # Lower temperature for more consistent evaluation
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Extract and parse the JSON from the response
                try:
                    # Find JSON-like structure in the response
                    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Try to find JSON without the code block markers
                        json_match = re.search(r"(\{[\s\S]*\})", content)
                        if json_match:
                            json_str = json_match.group(1)
                        else:
                            json_str = content
                    
                    review_results = json.loads(json_str)
                    
                    # Apply title recommendations if provided
                    if "title_recommendations" in review_results:
                        for role_idx, title in review_results["title_recommendations"].items():
                            if role_idx in constructed_sentences:
                                constructed_sentences[role_idx]["title"] = title
                    
                    return review_results
                except Exception as e:
                    print(f"Error parsing content review results: {e}")
                    return {"overall_assessment": "Error parsing results", "error": str(e)}
            else:
                print(f"Error from OpenAI API: {response.status_code}")
                return {"overall_assessment": f"API error: {response.status_code}"}
        except Exception as e:
            print(f"Exception when calling OpenAI API: {e}")
            return {"overall_assessment": f"Exception: {str(e)}"}
            
    def _update_titles_based_on_review(self, constructed_sentences: Dict[str, Any], review_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the titles based on the review results.
        
        Args:
            constructed_sentences (Dict[str, Any]): The constructed sentences for each role
            review_results (Dict[str, Any]): The review results
            
        Returns:
            Dict[str, Any]: The updated constructed sentences
        """
        if "title_recommendations" in review_results:
            for role_idx, title in review_results["title_recommendations"].items():
                if role_idx in constructed_sentences:
                    constructed_sentences[role_idx]["title"] = title
        
        return constructed_sentences 