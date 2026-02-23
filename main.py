from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
import os
import json

app = FastAPI(title="Comment Sentiment Analysis API")

# Request model
class CommentRequest(BaseModel):
    comment: str

# Response model
class SentimentResponse(BaseModel):
    sentiment: str
    rating: int

# JSON schema for structured output
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

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sentiment analysis assistant. Analyze the sentiment of the given comment.\n"
                        "Classify the sentiment as 'positive', 'negative', or 'neutral'.\n"
                        "Assign a rating from 1 to 5 where:\n"
                        "  5 = highly positive\n"
                        "  4 = somewhat positive\n"
                        "  3 = neutral\n"
                        "  2 = somewhat negative\n"
                        "  1 = highly negative\n"
                        "The rating must be consistent with the sentiment:\n"
                        "  - positive sentiment: rating 4 or 5\n"
                        "  - neutral sentiment: rating 3\n"
                        "  - negative sentiment: rating 1 or 2"
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze the sentiment of this comment: {request.comment}"
                }
            ],
            response_format=SENTIMENT_SCHEMA
        )

        result = json.loads(response.choices[0].message.content)

        # Validate values
        if result["sentiment"] not in ["positive", "negative", "neutral"]:
            raise ValueError(f"Invalid sentiment value: {result['sentiment']}")
        if not isinstance(result["rating"], int) or not (1 <= result["rating"] <= 5):
            raise ValueError(f"Invalid rating value: {result['rating']}")

        return JSONResponse(
            content={"sentiment": result["sentiment"], "rating": result["rating"]},
            media_type="application/json"
        )

    except openai.APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse API response: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
