import os
import csv
from pathlib import Path
import logging
import asyncio

from typing import Optional
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller, ActionResult
from playwright.async_api import BrowserContext
from steel import Steel
from pydantic import BaseModel
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext

# Load environment variables and define the API keys
load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

controller = Controller()

logger = logging.getLogger(__name__)

resume = Path.cwd() / 'UmerKhan_Resume.pdf'

if not resume.exists():
	raise FileNotFoundError(f'You need to set the path to your resume file in the resume variable. Resume file not found at {resume}')

class Job(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    fit_score: float
    estimated_salary: str
    link: str

@controller.action('Read my resume for context to generate fit scores, estimate salaries, and fill forms')
def read_resume():
	pdf = PdfReader(resume)
	text = ''
	for page in pdf.pages:
		text += page.extract_text() or ''
	logger.info(f'Read resume with {len(text)} characters')
	return ActionResult(extracted_content=text, include_in_memory=True)

@controller.action('Generate a fit score for the job based on the job description and my resume')
def generate_fit_score(job: Job):
    return f"Fit score: {job.fit_score}"

@controller.action('Estimate the salary for the job based on the job description, location, trends, and company')
def estimate_salary(job: Job):
    return f"Estimated salary: {job.estimated_salary}"

@controller.action('Save job data to CSV', param_model=Job)
def write_to_csv(job: Job):
    with open('jobs.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([job.title, job.company, job.location, job.fit_score, job.estimated_salary, job.link])

    return 'Saved job to file'

@controller.action('Read jobs from CSV file')
def read_jobs():
	with open('jobs.csv', 'r') as f:
		return f.read()

@controller.action('Ask user for further information or help')
def ask_human(question: str):
    answer = input(f"\n{question}\nInput: ")
    return ActionResult(extracted_content=answer)

# Initialize the Steel client and create a new session
client = Steel(steel_api_key=STEEL_API_KEY)
session = client.sessions.create()
print(f"Session created at {session.session_viewer_url}")

# Connect to the Steel session and create a browser context
cdp_url = f"wss://connect.steel.dev/?apiKey={STEEL_API_KEY}&sessionId={session.id}"
browser = Browser(config=BrowserConfig(cdp_url=cdp_url))
browser_context = BrowserContext(browser=browser)

# Initialize the LLMs
model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.4,
    api_key=OPENAI_API_KEY
)

planner_model = ChatOpenAI(
    model="o3-mini",
    temperature=0.65,
    api_key=OPENAI_API_KEY
)

login_creds = {'x_username': f'{LINKEDIN_USERNAME}', 'x_password': f'{LINKEDIN_PASSWORD}'}

# Define tasks
login_task = "Goto https://www.linkedin.com/login and login using x_username and x_password"


# Define the initial standard actions
goto_linkedin = [
    {'open_tab': {'url': 'https://www.linkedin.com/jobs/search/?f_TPR=r86400&geoId=90009551&keywords=((%22Systems%22%20OR%20%22System%22%20OR%20%22Desktop%22%20OR%20%22Technical%22%20OR%20%22Technology%22%20OR%20%22IT%22%20OR%20%22Endpoint%22%20OR%20%22Help%20Desk%22)%20AND%20(%22Support%22%20OR%20%22Engineer%22%20OR%20%22Analyst%22%20OR%20%22Specialist%22%20OR%20%22Administrator%22%20OR%20%22Technician%22))%20NOT%20(%22Data%20System%22%20OR%20%22Power%20Systems%22%20OR%20%22Business%22%20OR%20%22Bilingual%22%20OR%20%22Software%22)&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true'}},
]

extract_jobs = [
          {'extract_content': {'goal': 'Extract the following information for all the search results: job titles, company names, locations, and cooresponding links, param_model=Job', 'browser': 'browser', 'page_extraction_llm': 'gpt-4o'}}
]

# Configure AI agents
login_agent = Agent(
    task=login_task,
    llm=model,
    controller=controller,
    # planner_llm=planner_model,
    sensitive_data=login_creds,
    # initial_actions=goto_linkedin,
    browser=browser,
    browser_context=browser_context,
)

agent = Agent(
    task="",
    llm=model,
    planner_llm=planner_model,
    initial_actions=extract_jobs,
    # message_context="",
    controller=controller,
    use_vision=True,
    browser=browser,
    browser_context=browser_context,
)

# next_agent = Agent(
#     task="Filter the results using the following criteria: Date posted in the last 24 hours, Location: Greater Toronto Area, Ontario, Canada",
#     llm=model,
#     browser=browser,
#     browser_context=browser_context
# )

# Main function to run the agent
async def main():
    try:
        # Run the agent
        print("Starting login agent...")
        await login_agent.run()
        print("Login agent completed successfully.")

    except Exception as e:
        # Print errors
        print(f"An error occurred: {e}")

    # try:
    #     print("Starting job search agent...")
    #     await agent.run()
    #     print("Job search agent completed successfully.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")

    finally:
        # Close the browser and release the session
        if browser:
            await browser.close()
            print("Browser closed")
        if session:
            client.sessions.release(session.id)
            print("Session released")
        print("Agent execution completed.")

# Run the main function
if __name__ == '__main__':
    asyncio.run(main())