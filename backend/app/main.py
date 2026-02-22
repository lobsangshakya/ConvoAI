import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from .llm_service import GroqService

# Load environment variables
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ConvoAI", description="AI Chatbot API")

# CORS — allow React frontend to connect
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Groq LLM Service ──────────────────────────────────────────────────────────
groq_service = GroqService()

# ── In-memory session store ──────────────────────────────────────────────────
chat_sessions: Dict[str, List[Dict[str, str]]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting ConvoAI backend...")
    
    if groq_service.is_available():
        logger.info("Groq service is available")
    else:
        logger.warning("Groq service not available - using fallback responses")
    
    logger.info("Backend startup complete")


# ── Request Models ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: str
    model: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []
    session_id: str


# ── Chat Endpoint (non-streaming) ────────────────────────────────────────────
@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    """Main chat endpoint with Groq integration"""
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    # Initialize session history
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # 1. Build system prompt
    system_instr = (
        "You are ConvoAI, a helpful assistant. "
        "Answer concisely and accurately."
    )

    # 2. Assemble message list
    messages = [{"role": "system", "content": system_instr}]
    messages.extend(chat_sessions[session_id][-10:])  # last 10 for context
    messages.append({"role": "user", "content": user_message})

    # 3. Generate response using Groq
    try:
        model = request.model or groq_service.get_default_model()
        
        full_reply = await groq_service.generate_response(
            messages=messages,
            model=model,
            max_tokens=150,
            temperature=0.7
        )

        # Save to history
        chat_sessions[session_id].append({"role": "user", "content": user_message})
        chat_sessions[session_id].append({"role": "assistant", "content": full_reply})

        return ChatResponse(response=full_reply, sources=[], session_id=session_id)
        
    except Exception as e:
        logger.exception(f"Chat generation error: {e}")
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        return ChatResponse(response=error_msg, sources=[], session_id=session_id)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "groq_available": groq_service.is_available(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "ConvoAI API is running. POST to /api/chat to chat.",
        "endpoints": ["/api/chat", "/api/health"],
        "services": {
            "groq": groq_service.is_available()
        }
    }


# ── Render Compatibility ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)