import sys
import uuid
import time
import subprocess
import re
from google import genai
from google.genai import types
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal, List
from pydantic import BaseModel, Field
import os
import requests
import json
import traceback
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from io import StringIO
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok"}

AI_API_TOKEN = os.environ.get("OPENAI_API_KEY", os.environ.get("AIPROXY_TOKEN"))
CHAT_URL = os.environ.get("CHAT_URL", "https://aipipe.org/openrouter/v1/chat/completions")

# === Q2: /comment ===
class CommentRequest(BaseModel):
    comment: str = Field(..., min_length=1)

class SentimentResponse(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    rating: int = Field(..., ge=1, le=5)

@app.post("/comment", response_model=SentimentResponse)
async def analyze_comment(request: CommentRequest):
    try:
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a sentiment analysis API. Return ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": f"""
Analyze this comment and respond ONLY in this exact JSON format:

{{
  "sentiment": "positive | negative | neutral",
  "rating": 1-5
}}

Rules:
- 5 = highly positive
- 4 = positive
- 3 = neutral
- 2 = negative
- 1 = highly negative
- No explanations.
- No extra text.

Comment:
{request.comment}
"""
                }
            ],
            "temperature": 0
        }

        headers = {
            "Authorization": f"Bearer {AI_API_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            CHAT_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text)

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        content = content.strip().replace("```json", "").replace("```", "")
        parsed = json.loads(content)
        return parsed

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model did not return valid JSON")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Q7: /ask ===
class AskRequest(BaseModel):
    video_url: str
    topic: str

class AskResponse(BaseModel):
    timestamp: str
    video_url: str
    topic: str

def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    return match.group(1)

def seconds_to_hhmmss(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def fix_timestamp_format(timestamp: str) -> str:
    if not timestamp:
        return "00:00:00"
    parts = timestamp.strip().split(":")
    if len(parts) == 2:
        return "00:" + timestamp.strip()
    elif len(parts) == 3:
        return timestamp.strip()
    return "00:00:00"

def get_transcript(video_id: str) -> str:
    fetched = YouTubeTranscriptApi().fetch(video_id)
    transcript_list = fetched.to_raw_data()
    formatted = ""
    for item in transcript_list:
        time_str = seconds_to_hhmmss(item["start"])
        text = item["text"].replace("\n", " ")
        formatted += f"[{time_str}] {text}\n"
    return formatted

def ask_gemini(transcript: str, topic: str) -> str:
    user_prompt = (
        "You are a precise timestamp finder. You will be given a video transcript "
        "with timestamps in HH:MM:SS format.\n\n"
        f'Find the FIRST moment where the speaker discusses: "{topic}"\n\n'
        "Rules:\n"
        "1. Look for the exact phrase OR its meaning/context\n"
        "2. Return the timestamp of that EXACT moment\n"
        "3. Do NOT return chapter starts unless the topic starts there\n"
        "4. Timestamp MUST be in HH:MM:SS format\n"
        "5. Return ONLY raw JSON, no markdown, no explanation\n\n"
        f"Transcript:\n{transcript}\n\n"
        'Return ONLY this JSON: {"timestamp": "HH:MM:SS"}'
    )

    headers = {
        "Authorization": f"Bearer {AI_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.0,
    }

    response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"AI API error: {response.text}")

    raw = response.json()["choices"][0]["message"]["content"]
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines).strip()

    try:
        result = json.loads(raw)
        return result.get("timestamp", "00:00:00")
    except json.JSONDecodeError:
        match = re.search(r"\d{2}:\d{2}:\d{2}", raw)
        if match:
            return match.group(0)
        return "00:00:00"

@app.post("/ask", response_model=AskResponse)
@app.post("/ask/", response_model=AskResponse)
def ask(request: AskRequest):
    video_id = extract_video_id(request.video_url)
    try:
        transcript = get_transcript(video_id)
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(status_code=400, detail="No transcript found for this video.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript error: {str(e)}")

    timestamp = ask_gemini(transcript, request.topic)
    timestamp = fix_timestamp_format(timestamp)

    return AskResponse(
        timestamp=timestamp,
        video_url=request.video_url,
        topic=request.topic,
    )

# === `/execute` (from Q1) ===
@app.get("/execute")
def execute_query(q: str = Query(..., description="The query to process")):
    match = re.search(r"What is the status of ticket (\d+)", q, re.IGNORECASE)
    if match: return {"name": "get_ticket_status", "arguments": json.dumps({"ticket_id": int(match.group(1))})}
        
    match = re.search(r"Schedule a meeting on ([\d-]+) at ([\d:]+) in (.*?)\.?$", q, re.IGNORECASE)
    if match: return {"name": "schedule_meeting", "arguments": json.dumps({"date": match.group(1), "time": match.group(2), "meeting_room": match.group(3).strip()})}
        
    match = re.search(r"Show my expense balance for employee (\d+)", q, re.IGNORECASE)
    if match: return {"name": "get_expense_balance", "arguments": json.dumps({"employee_id": int(match.group(1))})}
        
    match = re.search(r"Calculate performance bonus for employee (\d+) for (\d+)", q, re.IGNORECASE)
    if match: return {"name": "calculate_performance_bonus", "arguments": json.dumps({"employee_id": int(match.group(1)), "current_year": int(match.group(2))})}
        
    match = re.search(r"Report office issue (\d+) for the (.*?)\s*department", q, re.IGNORECASE)
    if match: return {"name": "report_office_issue", "arguments": json.dumps({"issue_code": int(match.group(1)), "department": match.group(2).strip()})}
        
    return {"error": "No matching function found"}

# === `/code-interpreter` (from Q3) ===
class CodeRequest(BaseModel):
    code: str

def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        exec(code, {})
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}
    except Exception as e:
        output = traceback.format_exc()
        return {"success": False, "output": output}
    finally:
        sys.stdout = old_stdout

@app.post("/code-interpreter")
async def code_interpreter(request: CodeRequest):
    code = request.code
    exec_result = execute_python_code(code)
    
    if exec_result["success"]:
        return {"error": [], "result": exec_result["output"]}
    if not AI_API_TOKEN:
        return {"error": [], "result": exec_result["output"]}
        
    prompt = f"Analyze this Python code and its error traceback.\nIdentify the line number(s) where the error occurred.\n\nCODE:\n{code}\n\nTRACEBACK:\n{exec_result['output']}\n\nReturn ONLY a JSON object like {{\"error_lines\": [x, y]}} capturing the line numbers of the error."
    try:
        response = requests.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {AI_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            },
            timeout=30
        )
        if response.status_code == 200:
            raw = response.json()["choices"][0]["message"]["content"]
            raw = raw.strip().replace("```json", "").replace("```", "")
            data = json.loads(raw)
            error_lines = data.get("error_lines", [])
        else:
            error_lines = []
    except Exception as e:
        print("AI Error:", e)
        error_lines = []
        
    return {"error": error_lines, "result": exec_result["output"]}
