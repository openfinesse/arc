import os
from http import client
from dotenv import load_dotenv

load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")
conn = client.HTTPSConnection("api.steel.dev")

payload = {
    "file": ("UmerKhan_Resume.pdf", open("data/reference_resume/UmerKhan_Resume.pdf", "rb"), "application/pdf"),
    "name": "UmerKhan_Resume.pdf",
}

headers = {
    'Content-Type': 'multipart/form-data',
    'Steel-Api-Key': STEEL_API_KEY,
}

# Ask user for session_id and assign to variable
session_id = input("Enter session_id: ")

conn.request("POST", f"/v1/sessions/{session_id}/files", payload, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))