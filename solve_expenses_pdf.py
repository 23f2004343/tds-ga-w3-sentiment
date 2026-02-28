import sys
import time
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class ExpenseEntry(BaseModel):
    date: str = Field(description="The date string exactly as it appears in the PDF")
    amount: float = Field(description="The exact numerical amount")
    currency: str = Field(description="The currency: Rs, Rupees, Dollar, Dollars, or USD")

class ExpenseExtraction(BaseModel):
    entries: list[ExpenseEntry] = Field(description="All expense entries on 9th January across all 10 pages")

def solve_expenses(pdf_path):
    print(f"Uploading {pdf_path}...")
    client = genai.Client()
    
    file_info = client.files.upload(file=pdf_path)
    print(f"Uploaded as: {file_info.name}")
    
    print("Waiting for file processing to complete...")
    while True:
        f = client.files.get(name=file_info.name)
        if f.state == "ACTIVE":
            print("File is ready.")
            break
        elif f.state == "FAILED":
            raise Exception("File processing failed.")
        print(".", end="", flush=True)
        time.sleep(2)
        
    prompt = """
    This PDF has exactly 10 pages, each containing exactly 50 expense entries (500 total).
    
    Your task: Scan EVERY SINGLE page (all 10 pages) line by line and find ALL expense entries 
    whose date is the 9th of January. 
    
    The date for 9th January may appear in ANY of these formats:
    9Jan, 9JAN, 09Jan, 09JAN, January9, January 9, 9January, 9JANUARY, 09January, Jan9, Jan 9, JAN9
    
    For EACH matching entry on ANY page, extract the exact date string, the amount, and the currency.
    Currency can be: Rs, Rupees, Dollar, Dollars, USD
    
    Be very thorough — there should be many entries spread across different pages. Do NOT miss any.
    """
    
    print("Running extraction with gemini-2.5-flash (thorough)...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[file_info, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExpenseExtraction
        )
    )
    
    print("Extraction Complete!\n")
    data = json.loads(response.text)
    print(json.dumps(data, indent=2))
    
    total_rupees = 0.0
    print("\n--- Calculation ---")
    for entry in data.get('entries', []):
        amt = entry['amount']
        curr = entry['currency'].lower()
        
        if 'usd' in curr or 'dollar' in curr or '$' in curr:
            converted = amt * 80
            total_rupees += converted
            print(f"  {entry['date']}: {amt} {entry['currency']} -> {converted} Rs")
        else:
            total_rupees += amt
            print(f"  {entry['date']}: {amt} Rs")
            
    print(f"\n==> TOTAL ENTRIES FOUND: {len(data.get('entries', []))}")
    print(f"==> FINAL TOTAL IN RUPEES: {total_rupees}")
    print(f"\n*** ANSWER FOR THE BOX: {int(total_rupees)} ***")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 solve_expenses_pdf.py <pdf_file>")
        sys.exit(1)
    solve_expenses(sys.argv[1])
