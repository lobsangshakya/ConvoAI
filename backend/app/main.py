import os

# Explicitly unset proxy environment variables that interfere with OpenAI client
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

# Also set REQUESTS_CA_BUNDLE to avoid SSL issues in Docker
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple AI Chatbot", description="Minimal chatbot with OpenAI integration")

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize OpenAI client with minimal configuration to avoid proxy issues
import httpx

timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
transport = httpx.HTTPTransport(proxy=None)
http_client = httpx.Client(timeout=timeout, limits=limits, transport=transport)

client = OpenAI(
    api_key=api_key,
    http_client=http_client,
)

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
                {"role": "system", "content": "You are a friendly and helpful AI assistant. Respond in a conversational, engaging manner. Be polite, informative, and keep responses concise but helpful."},
                {"role": "user", "content": request.message}
            ],
            max_tokens=150,
            temperature=0.7,
            timeout=20.0
        )
        
        ai_response = response.choices[0].message.content.strip()
        return {"response": ai_response}
    
    except Exception as e:
        logger.error(f"Error calling OpenAI: {str(e)}")
        return {"response": "Sorry, I'm having trouble connecting to the AI service. Please try again."}

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Simple AI Chatbot API - Use POST /chat to send messages"}