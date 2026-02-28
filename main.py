
import sys
import uuid
import time
import subprocess
import re
from google import genai
from google.genai import types
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
import os
import json

app = FastAPI(title="Comment Sentiment Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommentRequest(BaseModel):
    comment: str

SENTIMENT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "sentiment_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                    "description": "Overall sentiment of the comment"
                },
                "rating": {
                    "type": "integer",
                    "description": "Sentiment intensity from 1 (highly negative) to 5 (highly positive)"
                }
            },
            "required": ["sentiment", "rating"],
            "additionalProperties": False
        }
    }
}

@app.get("/")
async def root():
    return {"message": "Comment Sentiment Analysis API", "endpoint": "POST /comment"}

@app.post("/comment")
async def analyze_comment(request: CommentRequest):
    if not request.comment or not request.comment.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    api_key = os.environ.get("AIPROXY_TOKEN") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")

    # Use AIPipe base URL (new service replacing AIProxy)
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://aipipe.org/openai/v1"
    )

    last_error = None
    for attempt in range(4):  # Retry up to 4 times (aipipe.org may route through geo-blocked servers)
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise sentiment analysis assistant. "
                            "Analyze the sentiment of the given comment and return structured output.\n"
                            "Rules:\n"
                            "- sentiment must be exactly one of: 'positive', 'negative', 'neutral'\n"
                            "- rating must be an integer 1-5 where:\n"
                            "  * 5 = EXTREMELY positive (e.g., 'perfect', 'amazing', 'flawless', 'best ever'). Reserve ONLY for absolute glowing praise.\n"
                            "  * 4 = positive (e.g., 'really happy', 'good quality', 'well-structured', 'nice'). Use for general satisfaction without extreme exaggeration.\n"
                            "  * 3 = neutral (e.g., 'okay', 'average', 'it was fine')\n"
                            "  * 2 = negative (e.g., 'below expectations', 'damaged', 'disappointing', 'not great'). Use for general dissatisfaction.\n"
                            "  * 1 = EXTREMELY negative (e.g., 'terrible', 'complete rip-off', 'hate it', 'awful'). Reserve ONLY for absolute outrage or zero-star experience.\n"
                            "- positive sentiment -> rating 4 or 5\n"
                            "- neutral sentiment -> rating 3\n"
                            "- negative sentiment -> rating 1 or 2\n"
                            "Be consistent and accurate."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this comment: \"{request.comment}\""
                    }
                ],
                response_format=SENTIMENT_SCHEMA
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            sentiment = result.get("sentiment")
            rating = result.get("rating")

            if sentiment not in ["positive", "negative", "neutral"]:
                raise ValueError(f"Invalid sentiment value: {sentiment}")
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise ValueError(f"Invalid rating value: {rating}")

            return JSONResponse(
                content={"sentiment": sentiment, "rating": rating},
                media_type="application/json"
            )

        except openai.APIStatusError as e:
            # Retry on geo-blocked 403 errors
            if e.status_code == 403 and "unsupported_country" in str(e):
                last_error = e
                continue
            raise HTTPException(status_code=502, detail=f"API error {e.status_code}: {str(e)}")
        except openai.APIConnectionError as e:
            last_error = e
            continue
        except openai.RateLimitError as e:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {str(e)}")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse response: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    raise HTTPException(status_code=502, detail=f"All retry attempts failed: {str(last_error)}")


class AskRequest(BaseModel):
    video_url: str
    topic: str

class AskResponse(BaseModel):
    timestamp: str
    video_url: str
    topic: str

@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    file_id = str(uuid.uuid4())
    audio_path = f"/tmp/{file_id}.m4a"
    
    try:
        subprocess.run([
            sys.executable, "-m", "yt_dlp",
            "-f", "bestaudio[ext=m4a]",
            "-o", audio_path,
            request.video_url
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("yt-dlp error:", e.stderr)
        raise HTTPException(status_code=500, detail="Failed to download audio")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Audio file missing")

    uploaded_file = client.files.upload(file=audio_path, config={'mime_type': 'audio/mp4'})

    while True:
        uploaded_file = client.files.get(name=uploaded_file.name)
        if uploaded_file.state.name == "ACTIVE":
            break
        elif uploaded_file.state.name == "FAILED":
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise HTTPException(status_code=500, detail="Gemini failed to process audio")
        time.sleep(3)

    prompt = f"Find the specific moment where the topic or phrase '{request.topic}' is first spoken."
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "timestamp": {
                "type": "STRING",
                "description": "The exact timestamp of the first occurrence of the topic in HH:MM:SS format."
            }
        },
        "required": ["timestamp"]
    }
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        data = response.text
        result = json.loads(data)
        timestamp = result.get("timestamp", "00:00:00")
        
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', timestamp):
            m = re.match(r'^(\d{1,2}):(\d{2})$', timestamp)
            if m:
                timestamp = f"00:{int(m.group(1)):02d}:{m.group(2)}"
            else:
                timestamp = "00:00:00"
    except Exception as e:
        print("Model error:", e)
        timestamp = "00:00:00"
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass
            
    return {"timestamp": timestamp, "video_url": request.video_url, "topic": request.topic}
