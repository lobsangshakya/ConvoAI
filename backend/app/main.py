import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Safe optional imports for RAG
try:
    from .rag_service import RAGService
except Exception:
    RAGService = None
    logging.warning("RAG service not available - continuing without RAG")

# Load environment variables
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ConvoAI", description="AI Chatbot API")

# CORS — allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── OpenAI Client ──────────────────────────────────────────────────────────
openai_client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    else:
        logger.warning("OPENAI_API_KEY not set - using fallback responses")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")

# ── Optional Services ──────────────────────────────────────────────────────────
rag_service = None

# Initialize RAG if available
if RAGService:
    try:
        KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge"))
        rag_service = RAGService(KNOWLEDGE_DIR, None)
        logger.info("RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")
        rag_service = None

# ── In-memory session store ──────────────────────────────────────────────────
chat_sessions: Dict[str, List[Dict[str, str]]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting ConvoAI backend...")
    
    # Initialize RAG if enabled
    if rag_service and os.getenv("ENABLE_RAG", "0") == "1":
        try:
            rag_service.ingest()
            logger.info("RAG ingestion completed")
        except Exception as e:
            logger.exception("RAG ingestion failed — continuing without RAG: %s", e)
    else:
        logger.info("RAG disabled or unavailable. Server running without embeddings.")
    
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
    """Main chat endpoint with OpenAI integration"""
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    # Initialize session history
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # 1. Build system prompt (with optional RAG context)
    system_instr = (
        "You are ConvoAI, a helpful assistant. "
        "Answer concisely and accurately."
    )

    # Add RAG context if available and enabled
    if rag_service and os.getenv("ENABLE_RAG", "0") == "1":
        try:
            relevant_chunks = rag_service.retrieve(user_message)
            if relevant_chunks:
                context_text = "\n\n".join(c["content"] for c in relevant_chunks)
                system_instr += f"\n\nCONTEXT:\n{context_text}"
                logger.info(f"Added RAG context for session {session_id}")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # 2. Assemble message list
    messages = [{"role": "system", "content": system_instr}]
    messages.extend(chat_sessions[session_id][-10:])  # last 10 for context
    messages.append({"role": "user", "content": user_message})

    # 3. Try OpenAI first, fallback to error message
    if openai_client is None:
        error_msg = "AI service is not available. Please check OPENAI_API_KEY environment variable."
        logger.error("OpenAI client not initialized")
        return ChatResponse(response=error_msg, sources=[], session_id=session_id)

    try:
        model = request.model or "gpt-3.5-turbo"
        
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=150,
            temperature=0.7,
            timeout=30.0
        )
        
        full_reply = response.choices[0].message.content.strip()

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
        "openai_available": openai_client is not None,
        "rag_available": rag_service is not None,
        "rag_enabled": os.getenv("ENABLE_RAG", "0") == "1",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "ConvoAI API is running. POST to /api/chat to chat.",
        "endpoints": ["/api/chat", "/api/health"],
        "services": {
            "openai": openai_client is not None,
            "rag": rag_service is not None
        }
    }


# ── Render Compatibility ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)