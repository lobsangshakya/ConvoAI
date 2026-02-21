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

# Safe optional imports for RAG and Ollama
try:
    from .rag_service import RAGService
except Exception:
    RAGService = None
    logging.warning("RAG service not available - continuing without RAG")

try:
    from .ollama_provider import OllamaProvider, Message
except Exception:
    OllamaProvider = None
    Message = None
    logging.warning("Ollama provider not available - continuing without Ollama")

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

# ── Optional Services ──────────────────────────────────────────────────────────
ollama_provider = None
rag_service = None

# Initialize Ollama if available
if OllamaProvider:
    try:
        ollama_provider = OllamaProvider()
        logger.info("Ollama provider initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Ollama provider: {e}")

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
    reply: str
    sources: List[dict] = []
    session_id: str


# ── Chat Endpoint (non-streaming) ────────────────────────────────────────────
@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    """Main chat endpoint with fallback support"""
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

    # 3. Try Ollama first, fallback to error message
    if ollama_provider is None:
        error_msg = "AI service is not available. Please check server configuration."
        logger.error("Ollama provider not initialized")
        return ChatResponse(reply=error_msg, sources=[], session_id=session_id)

    try:
        model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        ollama_messages = [Message(role=m["role"], content=m["content"]) for m in messages]
        
        parts = []
        async for token in ollama_provider.generate_response(
            messages=ollama_messages, model=model, stream=False
        ):
            parts.append(token)
        full_reply = "".join(parts)

        # Save to history
        chat_sessions[session_id].append({"role": "user", "content": user_message})
        chat_sessions[session_id].append({"role": "assistant", "content": full_reply})

        return ChatResponse(reply=full_reply, sources=[], session_id=session_id)
        
    except Exception as e:
        logger.exception(f"Chat generation error: {e}")
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        return ChatResponse(reply=error_msg, sources=[], session_id=session_id)


# ── Streaming Chat Endpoint ──────────────────────────────────────────────────
@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest):
    """Streaming chat endpoint with fallback support"""
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    system_instr = (
        "You are ConvoAI, a helpful assistant. "
        "Answer concisely and accurately."
    )

    # Add RAG context if available
    if rag_service and os.getenv("ENABLE_RAG", "0") == "1":
        try:
            relevant_chunks = rag_service.retrieve(user_message)
            if relevant_chunks:
                context_text = "\n\n".join(c["content"] for c in relevant_chunks)
                system_instr += f"\n\nCONTEXT:\n{context_text}"
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    messages = [{"role": "system", "content": system_instr}]
    messages.extend(chat_sessions[session_id][-10:])
    messages.append({"role": "user", "content": user_message})

    async def stream_generator():
        if ollama_provider is None:
            yield 'data: {"error": "AI service is not available"}\n\n'
            return
            
        try:
            model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            ollama_messages = [Message(role=m["role"], content=m["content"]) for m in messages]
            
            async for token in ollama_provider.generate_streaming_response(
                messages=ollama_messages, model=model
            ):
                yield token
        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "ollama_available": ollama_provider is not None,
        "rag_available": rag_service is not None,
        "rag_enabled": os.getenv("ENABLE_RAG", "0") == "1",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "ConvoAI API is running. POST to /api/chat to chat.",
        "endpoints": ["/api/chat", "/api/chat/stream", "/api/health"],
        "services": {
            "ollama": ollama_provider is not None,
            "rag": rag_service is not None
        }
    }


# ── Render Compatibility ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)