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
