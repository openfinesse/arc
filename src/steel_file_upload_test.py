import os
from steel import Steel
import httpx
from dotenv import load_dotenv

load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")

client = Steel(
    steel_api_key=STEEL_API_KEY,
)

session = client.sessions.create()

payload = {
    "file": ("requirements.txt", open("requirements.txt", "rb"), "text/plain"),
    "name": "requirements.txt",
}

files = {'upload-file': open('requirements.txt', 'rb')}

# Ask user for session_id and assign to variable
session_id = input("Enter session_id: ")

response = client.post(
    f"/sessions/{session_id}/files",
    cast_to=httpx.Response,
    files=files,
)

print(response.content)