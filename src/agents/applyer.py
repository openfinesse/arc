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

resume = Path.cwd() / 'data/reference_resume/UmerKhan_Resume.pdf'

if not resume.exists():
	raise FileNotFoundError(f'You need to set the path to your resume file in the resume variable. Resume file not found at {resume}')

class Job(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    fit_score: float
    salary: str
    link: str

@controller.action('Read my resume for context to fill forms, and help generate fit scores and estimate salaries')
def read_resume():
	pdf = PdfReader(resume)
	text = ''
	for page in pdf.pages:
		text += page.extract_text() or ''
	logger.info(f'Read resume with {len(text)} characters')
	return ActionResult(extracted_content=text, include_in_memory=True)

@controller.action('Save jobs to file - with a score of how well it fits me, and the estimated or extracted salary', param_model=Job)
def save_jobs(job: Job):
	with open('jobs.csv', 'a', newline='') as f:
		writer = csv.writer(f)
		writer.writerow([job.title, job.company, job.link, job.salary, job.location, job.fit_score])

	return 'Saved job to file'

@controller.action('Read jobs from CSV file')
def read_jobs():
	with open('jobs.csv', 'r') as f:
		return f.read()
     
@controller.action('Upload resume or cover letter to element with file path',)
async def upload_file(index: int, path: str, browser: BrowserContext, available_file_paths: list[str]):
	if path not in available_file_paths:
		return ActionResult(error=f'File path {path} is not available')

	if not os.path.exists(path):
		return ActionResult(error=f'File {path} does not exist')

	dom_el = await browser.get_dom_element_by_index(index)

	file_upload_dom_el = dom_el.get_file_upload_element()

	if file_upload_dom_el is None:
		msg = f'No file upload element found at index {index}'
		logger.info(msg)
		return ActionResult(error=msg)

	file_upload_el = await browser.get_locate_element(file_upload_dom_el)

	if file_upload_el is None:
		msg = f'No file upload element found at index {index}'
		logger.info(msg)
		return ActionResult(error=msg)

	try:
		await file_upload_el.set_input_files(path)
		msg = f'Successfully uploaded file to index {index}'
		logger.info(msg)
		return ActionResult(extracted_content=msg, include_in_memory=True)
	except Exception as e:
		msg = f'Failed to upload file to index {index}: {str(e)}'
		logger.info(msg)
		return ActionResult(error=msg)


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

# Initialize LLM
model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.4,
    api_key=OPENAI_API_KEY
)

# Open the linkedin jobs page
# goto_linkedin = [
#     {'go_to_url': {'url': 'https://www.linkedin.com/jobs/search/?f_TPR=r86400&geoId=90009551&keywords=((%22Systems%22%20OR%20%22System%22%20OR%20%22Desktop%22%20OR%20%22Technical%22%20OR%20%22Technology%22%20OR%20%22IT%22%20OR%20%22Endpoint%22%20OR%20%22Help%20Desk%22)%20AND%20(%22Support%22%20OR%20%22Engineer%22%20OR%20%22Analyst%22%20OR%20%22Specialist%22%20OR%20%22Administrator%22%20OR%20%22Technician%22))%20NOT%20(%22Data%20System%22%20OR%20%22Power%20Systems%22%20OR%20%22Business%22%20OR%20%22Bilingual%22%20OR%20%22Software%22)&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true'}},
# ]

upload_test = [
    {'go_to_url': {'url': 'https://www.csm-testcenter.org/test?do=show&subdo=common&test=file_upload'}},
]

tasks = (
    'Read my resume for context'
    'Read jobs from CSV file'
    'Start applying to the jobs'
)

# Configure AI agent
agent = Agent(
    task=tasks,
    llm=model,
    initial_actions=upload_test,
    controller=controller,
    use_vision=True,
    browser=browser,
    browser_context=browser_context,
	available_file_paths=[str(resume.absolute())]
)

# Main function to run the agent
async def main():
    try:
        print("Starting job application agent...")
        await agent.run()
        print("Job application agent completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

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