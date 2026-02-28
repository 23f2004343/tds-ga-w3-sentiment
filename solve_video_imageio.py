import imageio
import base64
import os
from openai import OpenAI
import json
import time
from PIL import Image
import io

AIPROXY_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjIwMDQzNDNAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.Rtwe_A25AeRKs5oOMkCe_vrkrSti-m3X6H3Xrp0uMWk"

client = OpenAI(
    api_key=AIPROXY_TOKEN,
    base_url="https://aipipe.org/openai/v1"
)

video_path = "attendee_checkin_23f2004343.webm"
reader = imageio.get_reader(video_path)

total_frames = reader.count_frames()
print(f"Total Frames: {total_frames}")
step = total_frames // 21

frames_b64 = []
it = reader.iter_data()

current_idx = 0
for i in range(1, 21):
    target_idx = i * step
    
    # advance iterator
    while current_idx < target_idx:
        frame = next(it)
        current_idx += 1
        
    img = Image.fromarray(frame)
    # Resize just a little to preserve text
    img = img.resize((960, 540))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    frames_b64.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{img_b64}",
            "detail": "high"
        }
    })

print(f"Extracted {len(frames_b64)} frames.")

prompt = "Each image shows an attendee's check-in screen. Look closely to read the Name and Date. Produce a output in JSON format exactly like: {\"attendees\": [{\"name\": \"Alice\", \"date\": \"03/07/2025\"}, ...]}"

messages = [
    {
        "role": "user",
        "content": [{"type": "text", "text": prompt}] + frames_b64
    }
]

last_err = None
for attempt in range(4):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={ "type": "json_object" },
            max_tokens=2000
        )
        print("Success! JSON Results:")
        print(response.choices[0].message.content)
        break
    except Exception as e:
        last_err = e
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(2)
else:
    print("All attempts failed:", last_err)
