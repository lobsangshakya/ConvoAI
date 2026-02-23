import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from dotenv import load_dotenv
from .ollama_service import OllamaService

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
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Ollama LLM Service ──────────────────────────────────────────────────────────
ollama_service = OllamaService()

# ── Optional RAG Service ────────────────────────────────────────────────────────
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
    
    if ollama_service.is_available():
        logger.info("Ollama service is available")
    else:
        logger.warning("Ollama service not available - using fallback responses")
    
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
    """Main chat endpoint with Ollama integration"""
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

    # 3. Generate response using Ollama
    try:
        model = request.model or ollama_service.get_default_model()
        
        full_reply = await ollama_service.generate_response(
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


# ── Streaming Chat Endpoint ──────────────────────────────────────────────────
@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest):
    """Streaming chat endpoint with Ollama integration"""
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

    # 3. Stream response using Ollama
    async def stream_generator():
        try:
            model = request.model or ollama_service.get_default_model()
            
            full_response = ""
            async for chunk in ollama_service.generate_streaming_response(
                messages=messages,
                model=model,
                max_tokens=150,
                temperature=0.7
            ):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # Save to history after streaming complete
            chat_sessions[session_id].append({"role": "user", "content": user_message})
            chat_sessions[session_id].append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "ollama_available": ollama_service.is_available(),
        "rag_available": rag_service is not None,
        "rag_enabled": os.getenv("ENABLE_RAG", "0") == "1",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "ConvoAI API is running. POST to /api/chat to chat.",
        "endpoints": ["/api/chat", "/api/health", "/api/chat/stream"],
        "services": {
            "ollama": ollama_service.is_available(),
            "rag": rag_service is not None
        }
    }


# ── Render Compatibility ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)