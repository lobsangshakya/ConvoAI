import os
import uuid
import logging
import httpx
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from .rag_service import RAGService

# Load environment variables
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ConvoAI Production", description="High-performance RAG-enabled chatbot API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Client
api_key = os.getenv("OPENAI_API_KEY")
try:
    client = OpenAI(api_key=api_key or "missing")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

# RAG Service
KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge"))
rag_service = RAGService(KNOWLEDGE_DIR, client)

# In-memory session store (In production, use Redis or Postgres)
chat_sessions: Dict[str, List[Dict[str, str]]] = {}

@app.on_event("startup")
async def startup_event():
    import os, logging
    
    if os.getenv("ENABLE_RAG", "0") == "1":
        try:
            rag_service.ingest()
        except Exception as e:
            logging.exception("RAG ingestion failed — continuing without RAG: %s", e)
    else:
        logging.info("RAG disabled. Server running without embeddings.")

class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: str

@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    # Initialize history if new session
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # 1. Retrieval
    sources = []
    context_text = ""
    
    # Only attempt RAG if client is available and RAG is enabled
    if client is not None and os.getenv("ENABLE_RAG", "0") == "1":
        try:
            relevant_chunks = rag_service.retrieve(user_message)
            if relevant_chunks:
                context_text = "\n\n".join([c['content'] for c in relevant_chunks])
                sources = [{"id": c["id"], "preview": c["content"][:100] + "..."} for c in relevant_chunks]
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # 2. Construct System Prompt
    system_instr = (
        "You are ConvoAI, a helpful senior assistant. "
        "Use requested CONTEXT to answer exactly and concisely. "
        "If the context is irrelevant, answer based on your general knowledge but mention that "
        "the local knowledge base didn't have specific info. "
        "Always provide citations if using context like [Source: filename.txt#chunkX]."
    )
    
    if context_text:
        system_instr += f"\n\nCONTEXT:\n{context_text}"

    # 3. Prepare messages for LLM
    messages = [{"role": "system", "content": system_instr}]
    # Add history (last 10 messages for safety)
    messages.extend(chat_sessions[session_id][-10:])
    messages.append({"role": "user", "content": user_message})

    # Check if OpenAI client is available
    if client is None:
        return {
            "reply": "LLM service unavailable. Please check API key or billing.",
            "sources": sources
        }

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.7,
            timeout=20  # Add timeout protection
        )
        
        full_reply = response.choices[0].message.content
        
        # Save to history
        chat_sessions[session_id].append({"role": "user", "content": user_message})
        chat_sessions[session_id].append({"role": "assistant", "content": full_reply})
        
        return {
            "reply": full_reply,
            "sources": sources
        }
        
    except Exception as e:
        logger.exception(f"Chat error: {e}")
        return {
            "reply": "LLM service unavailable. Please check API key or billing.",
            "sources": sources
        }

@app.get("/api/health")
async def health_check():
    rag_enabled = os.getenv("ENABLE_RAG", "0") == "1"
    return {
        "status": "ok",
        "rag_enabled": rag_enabled
    }

@app.get("/health")
async def legacy_health():
    rag_enabled = os.getenv("ENABLE_RAG", "0") == "1"
    return {
        "status": "ok",
        "rag_enabled": rag_enabled
    }

@app.post("/api/ingest")
async def api_ingest():
    if client is None:
        return {"status": "error", "message": "OpenAI client not available"}
    try:
        rag_service.ingest()
        return {"status": "success", "documents_loaded": len(rag_service.documents)}
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        return {"status": "error", "message": f"Error during ingestion: {str(e)}"}

@app.get("/")
async def root():
    return {
        "message": "ConvoAI API is active. POST to /api/chat",
        "api_endpoints": ["/api/chat", "/api/health", "/api/ingest"],
        "status": "ok"
    }