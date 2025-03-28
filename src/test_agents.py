#!/usr/bin/env python3
import argparse
import yaml
import json
import os
from typing import Dict, Any

from agents.company_researcher import CompanyResearcher
from agents.role_selector import RoleSelector
from agents.group_selector import GroupSelector
from agents.sentence_constructor import SentenceConstructor
from agents.sentence_reviewer import SentenceReviewer
from agents.content_reviewer import ContentReviewer
from agents.summary_generator import SummaryGenerator

def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def load_text_file(file_path: str) -> str:
    """Load a text file and return its contents as a string."""
    with open(file_path, 'r') as f:
        return f.read()

def test_company_researcher(job_description: str) -> None:
    """Test the CompanyResearcher agent."""
    print("\n=== Testing CompanyResearcher ===")
    
    agent = CompanyResearcher()
    company_info, enriched_description = agent.run(job_description)
    
    print(f"Company name extracted: {company_info.get('name', 'Not found')}")
    print(f"Company industry: {company_info.get('industry', 'Not found')}")
    
    print("\nEnriched job description (excerpt):")
    print(enriched_description[:300] + "...")
    
    return company_info, enriched_description

def test_role_selector(resume_data: Dict[str, Any], job_description: str) -> None:
    """Test the RoleSelector agent."""
    print("\n=== Testing RoleSelector ===")
    
    agent = RoleSelector()
    selected_roles = agent.run(resume_data["work"], job_description)
    
    print(f"Selected roles: {selected_roles}")
    
    # Print the titles of the selected roles
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        titles = ", ".join(role["title_variations"])
        company = ", ".join(role["company"])
        print(f"- Role {role_idx}: {titles} at {company}")
    
    return selected_roles

def test_group_selector(resume_data: Dict[str, Any], selected_roles: list, job_description: str) -> None:
    """Test the GroupSelector agent."""
    print("\n=== Testing GroupSelector ===")
    
    agent = GroupSelector()
    all_selected_groups = {}
    
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        
        print(f"\nSelecting groups for role {role_idx} ({role['title_variations'][0]}):")
        
        selected_groups = agent.run(role["responsibilities_and_accomplishments"], job_description)
        
        print(f"Selected groups: {selected_groups}")
        
        # Print original sentences for selected groups
        for group_name in selected_groups:
            group_data = role["responsibilities_and_accomplishments"][group_name]
            print(f"- {group_name}: {group_data['original_sentence']}")
        
        all_selected_groups[role_idx] = selected_groups
    
    return all_selected_groups

def test_sentence_constructor(resume_data: Dict[str, Any], selected_roles: list, 
                             all_selected_groups: Dict[int, list], job_description: str) -> None:
    """Test the SentenceConstructor agent."""
    print("\n=== Testing SentenceConstructor ===")
    
    agent = SentenceConstructor()
    constructed_sentences = {}
    
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        role_sentences = {}
        
        print(f"\nConstructing sentences for role {role_idx} ({role['title_variations'][0]}):")
        
        for group_name in all_selected_groups[role_idx]:
            group_data = role["responsibilities_and_accomplishments"][group_name]
            
            constructed_sentence = agent.run(group_data, job_description)
            
            print(f"- {group_name}: {constructed_sentence}")
            
            role_sentences[group_name] = constructed_sentence
        
        # Store the constructed sentences for this role
        constructed_sentences[role_idx] = {
            "title": role["title_variations"][0],
            "company": role["company"][0],
            "start_date": role["start_date"],
            "end_date": role["end_date"],
            "location": role["location"],
            "sentences": role_sentences
        }
    
    return constructed_sentences

def test_sentence_reviewer(constructed_sentences: Dict[int, Dict[str, Any]]) -> None:
    """Test the SentenceReviewer agent."""
    print("\n=== Testing SentenceReviewer ===")
    
    agent = SentenceReviewer()
    review_results = {}
    
    for role_idx, role_data in constructed_sentences.items():
        print(f"\nReviewing sentences for role {role_idx} ({role_data['title']}):")
        
        role_reviews = {}
        for group_name, sentence in role_data["sentences"].items():
            is_approved, feedback = agent.run(sentence)
            
            status = "✅ Approved" if is_approved else "❌ Rejected"
            print(f"- {group_name}: {status}")
            if not is_approved:
                print(f"  Feedback: {feedback}")
            
            role_reviews[group_name] = {
                "approved": is_approved,
                "feedback": feedback
            }
        
        review_results[role_idx] = role_reviews
    
    return review_results

def test_content_reviewer(constructed_sentences: Dict[int, Dict[str, Any]], job_description: str) -> None:
    """Test the ContentReviewer agent."""
    print("\n=== Testing ContentReviewer ===")
    
    agent = ContentReviewer()
    review_results = agent.run(constructed_sentences, job_description)
    
    print("\nContent review results:")
    print(f"Overall alignment: {review_results.get('overall_alignment', 'Not provided')}")
    
    if "key_skills" in review_results:
        print("\nKey skills:")
        print("- Covered: " + ", ".join(review_results["key_skills"].get("covered", ["None"])))
        print("- Missing: " + ", ".join(review_results["key_skills"].get("missing", ["None"])))
    
    if "suggested_improvements" in review_results:
        print("\nSuggested improvements:")
        for improvement in review_results["suggested_improvements"]:
            print(f"- {improvement}")
    
    if "title_recommendations" in review_results:
        print("\nTitle recommendations:")
        for role_idx, title in review_results["title_recommendations"].items():
            print(f"- Role {role_idx}: {title}")
    
    return review_results

def test_summary_generator(constructed_sentences: Dict[int, Dict[str, Any]], 
                           job_description: str, company_info: Dict[str, Any]) -> None:
    """Test the SummaryGenerator agent."""
    print("\n=== Testing SummaryGenerator ===")
    
    agent = SummaryGenerator()
    summary = agent.run(constructed_sentences, job_description, company_info)
    
    print("\nGenerated summary:")
    print(summary)
    
    return summary

def main():
    parser = argparse.ArgumentParser(description="Test the resume customizer agents")
    parser.add_argument("--resume", required=True, help="Path to the resume YAML file")
    parser.add_argument("--job-description", required=True, help="Path to the job description file")
    
    args = parser.parse_args()
    
    # Load data
    resume_data = load_yaml_file(args.resume)
    job_description = load_text_file(args.job_description)
    
    # Test each agent in sequence
    company_info, enriched_description = test_company_researcher(job_description)
    
    # Using the enriched job description for subsequent tests
    selected_roles = test_role_selector(resume_data, enriched_description)
    
    all_selected_groups = test_group_selector(resume_data, selected_roles, enriched_description)
    
    constructed_sentences = test_sentence_constructor(resume_data, selected_roles, 
                                                    all_selected_groups, enriched_description)
    
    review_results = test_sentence_reviewer(constructed_sentences)
    
    content_review = test_content_reviewer(constructed_sentences, enriched_description)
    
    summary = test_summary_generator(constructed_sentences, enriched_description, company_info)
    
    print("\nAll agents tested successfully.")

if __name__ == "__main__":
    main() 