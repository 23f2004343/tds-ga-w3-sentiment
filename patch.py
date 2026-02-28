with open("main.py", "r") as f:
    main_code = f.read()

get_ask = """
@app.get("/ask")
async def ask_get():
    return {"message": "Use POST /ask for queries"}
"""

main_code = main_code.replace('api_key = os.environ.get("GEMINI_API_KEY")', 'api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyDN8nCv_maQ3LbVWOyrO7r8U8yJe0zc5hE")')
main_code = main_code.replace('@app.post("/ask", response_model=AskResponse)', get_ask + '\n@app.post("/ask", response_model=AskResponse)')

with open("main.py", "w") as f:
    f.write(main_code)
