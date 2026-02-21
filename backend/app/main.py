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

from .rag_service import RAGService
from .ollama_provider import OllamaProvider, Message

# Load environment variables
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ConvoAI", description="AI Chatbot powered by Ollama")

# CORS — allow the React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Ollama Provider ──────────────────────────────────────────────────────────
ollama_provider = None
try:
    ollama_provider = OllamaProvider()
    logger.info("Ollama provider initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Ollama provider: {e}")

# ── RAG Service (optional) ───────────────────────────────────────────────────
KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge"))
rag_service = RAGService(KNOWLEDGE_DIR, None)

# ── In-memory session store ──────────────────────────────────────────────────
chat_sessions: Dict[str, List[Dict[str, str]]] = {}


@app.on_event("startup")
async def startup_event():
    if os.getenv("ENABLE_RAG", "0") == "1":
        try:
            rag_service.ingest()
            logger.info("RAG ingestion completed")
        except Exception as e:
            logger.exception("RAG ingestion failed — continuing without RAG: %s", e)
    else:
        logger.info("RAG disabled. Server running without embeddings.")


# ── Request Model ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: str
    model: Optional[str] = None  # Override the default Ollama model


# ── Chat Endpoint (non-streaming) ────────────────────────────────────────────
@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    # Initialize session history
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # 1.  Build system prompt (with optional RAG context)
    system_instr = (
        "You are ConvoAI, a helpful assistant. "
        "Answer concisely and accurately."
    )

    if os.getenv("ENABLE_RAG", "0") == "1":
        try:
            relevant_chunks = rag_service.retrieve(user_message)
            if relevant_chunks:
                context_text = "\n\n".join(c["content"] for c in relevant_chunks)
                system_instr += f"\n\nCONTEXT:\n{context_text}"
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # 2.  Assemble message list
    messages = [{"role": "system", "content": system_instr}]
    messages.extend(chat_sessions[session_id][-10:])  # last 10 for context
    messages.append({"role": "user", "content": user_message})

    # 3.  Call Ollama
    if ollama_provider is None:
        return {"reply": "Ollama is not available. Make sure Ollama is running.", "sources": []}

    try:
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

        return {"reply": full_reply, "sources": []}
    except Exception as e:
        logger.exception(f"Ollama error: {e}")
        return {"reply": f"Error: {e}", "sources": []}


# ── Streaming Chat Endpoint ──────────────────────────────────────────────────
@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest):
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    system_instr = (
        "You are ConvoAI, a helpful assistant. "
        "Answer concisely and accurately."
    )

    if os.getenv("ENABLE_RAG", "0") == "1":
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
            yield 'data: {"error": "Ollama is not available"}\n\n'
            return
        try:
            ollama_messages = [Message(role=m["role"], content=m["content"]) for m in messages]
            async for token in ollama_provider.generate_streaming_response(
                messages=ollama_messages, model=model
            ):
                yield token
        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield f'data: {{"error": "{e}"}}\n\n'

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "ollama_available": ollama_provider is not None,
        "rag_enabled": os.getenv("ENABLE_RAG", "0") == "1",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    return {
        "message": "ConvoAI API is running. POST to /api/chat to chat.",
        "endpoints": ["/api/chat", "/api/chat/stream", "/api/health"],
    }