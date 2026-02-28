import os
import sys
import time
from google import genai
from google.genai import types

def extract_attendees(video_path):
    print(f"Uploading {video_path}...")
    client = genai.Client()
    video_file = client.files.upload(file=video_path)

    print(f"Uploaded as: {video_file.name}")
    print("Waiting for video processing to complete...")
    
    # Wait for the file to be processed
    while True:
        file_info = client.files.get(name=video_file.name)
        if file_info.state == "ACTIVE":
            print("Video is ready for processing.")
            break
        elif file_info.state == "FAILED":
            raise Exception("Video processing failed in Gemini.")
        print(".", end="", flush=True)
        time.sleep(2)

    prompt = """
    Watch this entire video from start to finish — it is exactly 44 seconds long and shows 20 different attendee check-ins one by one.
    Each check-in shows a name and a registration date on screen. There is also a "Recent Check-ins" panel on the RIGHT side that accumulates all names shown so far.
    
    Read EVERY name and date visible anywhere on screen across the full duration.
    DO NOT make up or guess any names. Only include names that are clearly visible in the video.
    DO NOT repeat names.
    
    Return ALL entries you found as a JSON array with keys "name" (full name) and "date" (in dd/mm/yyyy format).
    Example: [{"name": "John Doe", "date": "15/02/2026"}, ...]
    """
    
    print("Running extraction...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            video_file,
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )

    print("\nExtraction Complete! JSON Output below:\n")
    print(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python solve_gemini.py <video_file>")
        sys.exit(1)
    extract_attendees(sys.argv[1])
