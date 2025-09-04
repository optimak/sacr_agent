import os
import requests
from fastapi import FastAPI

app = FastAPI()

PROMPTFLOW_ENDPOINT = os.getenv("PROMPTFLOW_ENDPOINT")
PROMPTFLOW_KEY = os.getenv("PROMPTFLOW_KEY")
@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.get("/health") 
def health():
    return {"status": "healthy"}
@app.post("/ask")
async def ask_question(payload: dict):
    headers = {
        "Authorization": f"Bearer {PROMPTFLOW_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(PROMPTFLOW_ENDPOINT, headers=headers, json=payload)
    return response.json()
