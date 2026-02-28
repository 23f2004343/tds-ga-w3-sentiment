import cv2
import base64
import os
from openai import OpenAI
import json
import time

AIPROXY_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjIwMDQzNDNAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.Rtwe_A25AeRKs5oOMkCe_vrkrSti-m3X6H3Xrp0uMWk"

client = OpenAI(
    api_key=AIPROXY_TOKEN,
    base_url="https://aipipe.org/openai/v1"
)

video_path = "attendee_checkin_23f2004343.webm"
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
duration = total_frames / fps

print(f"Video FPS: {fps}, Duration: {duration}s")

frames_b64 = []
# The video is ~44 seconds. 20 attendees. That's about 1 attendee every 2.2 seconds.
# We'll sample 1 frame every 2 seconds.
sample_rate = 2.2

for i in range(20):
    time_sec = 1.0 + (i * sample_rate)  # offset by 1s to hit the middle of the display
    if time_sec > duration:
        break
    
    cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
    ret, frame = cap.read()
    if not ret:
        break
        
    # Resize frame to save token size
    frame = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    
    frames_b64.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{img_b64}",
            "detail": "low"
        }
    })

print(f"Extracted {len(frames_b64)} frames.")

prompt = "Here is a sequence of screen frames. In each frame, there is an attendee's name and registration date (format dd/mm/yyyy). Extract all these name-date pairs exactly as they appear in the images. Return ONLY a valid JSON array of objects structured like: [{\"name\": \"John Doe\", \"date\": \"15/02/2026\"}, ...]"

messages = [
    {
        "role": "user",
        "content": [{"type": "text", "text": prompt}] + frames_b64
    }
]

# Send to OpenAI (via proxy)
last_err = None
for attempt in range(4):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={ "type": "json_object" }
        )
        print("Success!")
        print(response.choices[0].message.content)
        break
    except Exception as e:
        last_err = e
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(2)
else:
    print("All attempts failed:", last_err)
