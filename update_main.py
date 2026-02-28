with open("main.py", "r") as f:
    main_code = f.read()

imports_to_add = """
import sys
import uuid
import time
import subprocess
import re
from google import genai
from google.genai import types
"""

content_to_add = """

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
"""

with open("main.py", "w") as f:
    f.write(imports_to_add + main_code + content_to_add)

