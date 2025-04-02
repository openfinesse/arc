#!/usr/bin/env python3
import argparse
import yaml
import json
import os
import asyncio
import sys
from typing import Dict, List, Any, Optional, Tuple

# Add the src directory to the path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import config to ensure environment variables are loaded
try:
    # Try relative import (when used as a module)
    from .config import load_dotenv
    from .logging_config import get_logger
    from .agents import (
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator,
        TitleSelector
    )
except ImportError:
    # Fall back to absolute import (when run as a script)
    from config import load_dotenv
    from logging_config import get_logger
    from agents import (
        CompanyResearcher,
        RoleSelector,
        GroupSelector,
        SentenceConstructor,
        SentenceReviewer,
        ContentReviewer,
        SummaryGenerator,
        TitleSelector
    )

# Get logger
logger = get_logger()

def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def load_text_file(file_path: str) -> str:
    """Load a text file and return its contents as a string."""
    with open(file_path, 'r') as f:
        return f.read()

async def test_company_researcher(job_description: str) -> Tuple[Dict[str, Any], str]:
    """Test the CompanyResearcher agent."""
    print("\n=== Testing CompanyResearcher ===")
    
    agent = CompanyResearcher()
    enriched_description = await agent.run(job_description)
    
    # Extract company info from the cache after the run
    company_name = agent._extract_company_name_with_ai(job_description)
    company_info = agent._load_from_cache(company_name) if company_name else {}
    
    print(f"Company name extracted: {company_info.get('name', 'Not found')}")
    print(f"Company industry: {company_info.get('industry', 'Not found')}")
    
    print("\nEnriched job description (excerpt):")
    print(enriched_description[:300] + "...")
    
    return company_info, enriched_description

def test_role_selector(resume_data: Dict[str, Any], job_description: str) -> List[int]:
    """Test the RoleSelector agent."""
    print("\n=== Testing RoleSelector ===")
    
    agent = RoleSelector()
    selected_roles = agent.run(resume_data["work"], job_description)
    
    print(f"Selected roles: {selected_roles}")
    
    # Print the titles of the selected roles
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        titles = ", ".join(role["title_variables"])
        company = ", ".join(role["company"]) if isinstance(role["company"], list) else role["company"]
        print(f"- Role {role_idx}: {titles} at {company}")
    
    return selected_roles

def test_group_selector(resume_data: Dict[str, Any], selected_roles: List[int], job_description: str) -> Dict[int, List[str]]:
    """Test the GroupSelector agent."""
    print("\n=== Testing GroupSelector ===")
    
    agent = GroupSelector()
    all_selected_groups = {}
    
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        
        print(f"\nSelecting groups for role {role_idx} ({role['title_variables'][0]}):")
        
        selected_groups = agent.run(role["responsibilities_and_accomplishments"], job_description)
        
        print(f"Selected groups: {selected_groups}")
        
        # Print original sentences for selected groups
        for group_name in selected_groups:
            group_data = role["responsibilities_and_accomplishments"][group_name]
            print(f"- {group_name}: {group_data['original_sentence']}")
        
        all_selected_groups[role_idx] = selected_groups
    
    # Test group selection for projects if they exist
    if "projects" in resume_data and resume_data["projects"]:
        print("\nSelecting groups for projects:")
        
        for project_idx, project in enumerate(resume_data["projects"]):
            print(f"\nProject {project_idx} ({project['name']}):")
            
            selected_groups = agent.run(project["responsibilities_and_accomplishments"], job_description)
            
            print(f"Selected groups: {selected_groups}")
            
            # Print original sentences for selected groups
            for group_name in selected_groups:
                group_data = project["responsibilities_and_accomplishments"][group_name]
                print(f"- {group_name}: {group_data['original_sentence']}")
            
            all_selected_groups[f"project_{project_idx}"] = selected_groups
    
    return all_selected_groups

async def test_title_selector(resume_data: Dict[str, Any], selected_roles: List[int], job_description: str) -> Dict[int, str]:
    """Test the TitleSelector agent."""
    print("\n=== Testing TitleSelector ===")
    
    agent = TitleSelector()
    selected_titles = {}
    
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        
        if len(role["title_variables"]) > 1:
            print(f"\nSelecting title for role {role_idx} ({role['company'][0]}):")
            print(f"Available titles: {', '.join(role['title_variables'])}")
            
            selected_title = await agent.run(role, job_description)
            
            print(f"Selected title: {selected_title}")
            selected_titles[role_idx] = selected_title
        else:
            print(f"\nRole {role_idx} ({role['company'][0]}) has only one title: {role['title_variables'][0]}")
            selected_titles[role_idx] = role["title_variables"][0]
    
    return selected_titles

async def test_sentence_constructor(resume_data: Dict[str, Any], selected_roles: List[int], 
                             all_selected_groups: Dict[int, List[str]], job_description: str) -> Dict[int, Dict[str, Any]]:
    """Test the SentenceConstructor agent."""
    print("\n=== Testing SentenceConstructor ===")
    
    agent = SentenceConstructor()
    constructed_sentences = {}
    
    # Prepare all group data for action verb planning
    all_group_data = []
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        for group_name in all_selected_groups[role_idx]:
            all_group_data.append(role["responsibilities_and_accomplishments"][group_name])
            
    # Plan action verbs for all sentences (synchronous method)
    if hasattr(agent, 'plan_action_verbs'):
        print("\nPlanning action verbs for all sentences...")
        agent.plan_action_verbs(all_group_data, job_description)
    
    # Process roles
    for role_idx in selected_roles:
        role = resume_data["work"][role_idx]
        role_sentences = {}
        
        print(f"\nConstructing sentences for role {role_idx} ({role['title_variables'][0]}):")
        
        for group_name in all_selected_groups[role_idx]:
            group_data = role["responsibilities_and_accomplishments"][group_name]
            
            constructed_sentence = await agent.run(group_data, job_description)
            
            print(f"- {group_name}: {constructed_sentence}")
            
            role_sentences[group_name] = constructed_sentence
        
        # Store the constructed sentences for this role
        constructed_sentences[role_idx] = {
            "title": role["title_variables"][0],  # Will be updated by title selector later
            "company": role["company"][0] if isinstance(role["company"], list) else role["company"],
            "start_date": role["start_date"],
            "end_date": role["end_date"],
            "location": role["location"],
            "sentences": role_sentences
        }
    
    # Process projects if they exist
    if "projects" in resume_data and resume_data["projects"]:
        project_sentences = {}
        
        for project_idx, project in enumerate(resume_data["projects"]):
            if f"project_{project_idx}" in all_selected_groups:
                print(f"\nConstructing sentences for project {project_idx} ({project['name']}):")
                
                project_role_sentences = {}
                
                for group_name in all_selected_groups[f"project_{project_idx}"]:
                    group_data = project["responsibilities_and_accomplishments"][group_name]
                    
                    constructed_sentence = await agent.run(group_data, job_description)
                    
                    print(f"- {group_name}: {constructed_sentence}")
                    
                    project_role_sentences[group_name] = constructed_sentence
                
                project_sentences[project_idx] = {
                    "name": project["name"],
                    "sentences": project_role_sentences
                }
        
        constructed_sentences["projects"] = project_sentences
    
    return constructed_sentences

async def test_sentence_reviewer(constructed_sentences: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Dict[str, Any]]]:
    """Test the SentenceReviewer agent."""
    print("\n=== Testing SentenceReviewer ===")
    
    agent = SentenceReviewer()
    review_results = {}
    
    # Review work experience sentences
    for role_idx, role_data in constructed_sentences.items():
        if role_idx != "projects": # Skip the projects key
            print(f"\nReviewing sentences for role {role_idx} ({role_data['title']}):")
            
            role_reviews = {}
            for group_name, sentence in role_data["sentences"].items():
                is_approved, feedback = await agent.run(sentence)
                
                status = "✅ Approved" if is_approved else "❌ Rejected"
                print(f"- {group_name}: {status}")
                if not is_approved:
                    print(f"  Feedback: {feedback}")
                
                role_reviews[group_name] = {
                    "approved": is_approved,
                    "feedback": feedback
                }
            
            review_results[role_idx] = role_reviews
    
    # Review project sentences if they exist
    if "projects" in constructed_sentences:
        project_reviews = {}
        
        for project_idx, project_data in constructed_sentences["projects"].items():
            print(f"\nReviewing sentences for project {project_idx} ({project_data['name']}):")
            
            project_role_reviews = {}
            for group_name, sentence in project_data["sentences"].items():
                is_approved, feedback = await agent.run(sentence)
                
                status = "✅ Approved" if is_approved else "❌ Rejected"
                print(f"- {group_name}: {status}")
                if not is_approved:
                    print(f"  Feedback: {feedback}")
                
                project_role_reviews[group_name] = {
                    "approved": is_approved,
                    "feedback": feedback
                }
            
            project_reviews[project_idx] = project_role_reviews
        
        review_results["projects"] = project_reviews
    
    return review_results

def test_content_reviewer(constructed_sentences: Dict[int, Dict[str, Any]], job_description: str) -> Dict[str, Any]:
    """Test the ContentReviewer agent."""
    print("\n=== Testing ContentReviewer ===")
    
    # Filter out the "projects" key for content reviewer as it expects only work experiences
    work_constructed_sentences = {k: v for k, v in constructed_sentences.items() if k != "projects"}
    
    agent = ContentReviewer()
    review_results = agent.run(work_constructed_sentences, job_description)
    
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
                           job_description: str) -> str:
    """Test the SummaryGenerator agent."""
    print("\n=== Testing SummaryGenerator ===")
    
    # Filter out the "projects" key for summary generator as it expects only work experiences
    work_constructed_sentences = {k: v for k, v in constructed_sentences.items() if k != "projects"}
    
    agent = SummaryGenerator()
    summary = agent.run(work_constructed_sentences, job_description)
    
    print("\nGenerated summary:")
    print(summary)
    
    return summary

async def update_titles_with_content_review(constructed_sentences: Dict[int, Dict[str, Any]], 
                                     content_review: Dict[str, Any], 
                                     selected_titles: Dict[int, str]) -> Dict[int, Dict[str, Any]]:
    """Update the titles in constructed sentences based on content review recommendations and title selector."""
    print("\n=== Updating Titles ===")
    
    # Start with the titles from TitleSelector
    for role_idx, title in selected_titles.items():
        if role_idx in constructed_sentences:
            constructed_sentences[role_idx]["title"] = title
    
    # Update with ContentReviewer recommendations if available
    if "title_recommendations" in content_review:
        for role_key, title in content_review["title_recommendations"].items():
            # Extract the role index from keys like 'role_0'
            if isinstance(role_key, str) and role_key.startswith('role_'):
                try:
                    role_idx = int(role_key.split('_')[1])
                    if role_idx in constructed_sentences:
                        print(f"Updating title for role {role_idx}: {constructed_sentences[role_idx]['title']} -> {title}")
                        constructed_sentences[role_idx]["title"] = title
                except (ValueError, IndexError):
                    print(f"Could not parse role index from {role_key}")
            else:
                # Handle numeric role indexes
                role_idx = int(role_key) if isinstance(role_key, str) else role_key
                if role_idx in constructed_sentences:
                    print(f"Updating title for role {role_idx}: {constructed_sentences[role_idx]['title']} -> {title}")
                    constructed_sentences[role_idx]["title"] = title
    
    return constructed_sentences

async def main():
    parser = argparse.ArgumentParser(description="Test the resume customizer agents")
    parser.add_argument("--resume", help="Path to the resume YAML file")
    parser.add_argument("--job-description", help="Path to the job description file")
    parser.add_argument("--clear-company-cache", action="store_true", help="Clear the cached company research data")
    parser.add_argument("--list-cached-companies", action="store_true", help="List all companies in the research cache")
    
    args = parser.parse_args()
    
    # Handle company cache commands
    if args.clear_company_cache or args.list_cached_companies:
        researcher = CompanyResearcher()
        
        if args.clear_company_cache:
            researcher.clear_cache()
            print("Company research cache cleared.")
            return
        
        if args.list_cached_companies:
            companies = researcher.list_cached_companies()
            if companies:
                print("Cached company research data:")
                for company in companies:
                    print(f" - {company}")
            else:
                print("No cached company research data found.")
            return
    
    # Check required args for testing
    if not args.resume or not args.job_description:
        parser.error("--resume and --job-description are required for testing agents")
    
    # Load data
    resume_data = load_yaml_file(args.resume)
    job_description = load_text_file(args.job_description)
    
    print(f"Loaded resume with {len(resume_data['work'])} work experiences")
    print(f"Job description length: {len(job_description)} characters")
    
    # Execute each test in sequence
    company_info, enriched_description = await test_company_researcher(job_description)
    
    # Using the enriched job description for subsequent tests
    selected_roles = test_role_selector(resume_data, enriched_description)
    
    all_selected_groups = test_group_selector(resume_data, selected_roles, enriched_description)
    
    selected_titles = await test_title_selector(resume_data, selected_roles, enriched_description)
    
    constructed_sentences = await test_sentence_constructor(resume_data, selected_roles, 
                                                    all_selected_groups, enriched_description)
    
    review_results = await test_sentence_reviewer(constructed_sentences)
    
    content_review = test_content_reviewer(constructed_sentences, enriched_description)
    
    # Update titles based on content review and title selector
    constructed_sentences = await update_titles_with_content_review(constructed_sentences, content_review, selected_titles)
    
    summary = test_summary_generator(constructed_sentences, enriched_description)
    
    print("\nAll agents tested successfully.")

if __name__ == "__main__":
    # Ensure environment variables are loaded
    load_dotenv()
    
    # Run the async main function
    asyncio.run(main()) 