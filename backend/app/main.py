from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple AI Chatbot", description="Minimal chatbot with OpenAI integration")

# Get OpenAI API key from environment
# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
client = OpenAI(api_key=api_key)

class MessageRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat")
async def chat(request: MessageRequest) -> Dict[str, str]:
    """Simple chat endpoint that calls OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        return {"response": ai_response}
    
    except Exception as e:
        logger.error(f"Error calling OpenAI: {str(e)}")
        return {"response": "Sorry, I'm having trouble connecting to the AI service. Please try again."}

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Simple AI Chatbot API - Use POST /chat to send messages"}