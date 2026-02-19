import os
import uuid
import logging
import httpx
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv

from .rag_service import RAGService
from .local_llm import LocalLLM
from .kafka_consumer import init_kafka_processor, get_kafka_processor
from .ollama_provider import OllamaProvider, Message
from .project_manager import project_manager, ProviderType, ProjectConfig

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

# Local LLM Client - defer loading
llm_client = None
try:
    # Only initialize local LLM if explicitly requested
    if os.getenv("ENABLE_LOCAL_LLM", "false").lower() == "true":
        llm_client = LocalLLM()
        logger.info("Local LLM initialized successfully")
    else:
        logger.info("Local LLM disabled, using Ollama or OpenAI")
except Exception as e:
    logger.error(f"Failed to initialize local LLM: {e}")

# Ollama Provider
ollama_provider = None
try:
    ollama_provider = OllamaProvider()
    logger.info("Ollama provider initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Ollama provider: {e}")

# Kafka Processor
kafka_processor = None

# RAG Service - Initialize with None as client for now
KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge"))
rag_service = RAGService(KNOWLEDGE_DIR, llm_client if llm_client else None)

# In-memory session store (In production, use Redis or Postgres)
chat_sessions: Dict[str, List[Dict[str, str]]] = {}

@app.on_event("startup")
async def startup_event():
    import os, logging
    
    # Initialize Kafka processor
    init_kafka_processor()
    
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
    project_id: Optional[str] = "default"  # Add project_id to request
    provider: Optional[str] = None  # Allow provider override
    model: Optional[str] = None  # Allow model override

@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    # Initialize history if new session
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Get project configuration based on request
    project_config = project_manager.get_project(request.project_id) or ProjectConfig(
        project_id=request.project_id,
        provider=ProviderType.OLLAMA,  # Default to Ollama instead of Local LLM
        model="qwen2.5:3b"  # Use available model
    )
    
    # Override provider/model if specified in request
    if request.provider:
        project_config.provider = ProviderType(request.provider)
    if request.model:
        project_config.model = request.model
    
    # 1. Retrieval
    sources = []
    context_text = ""
    
    # Only attempt RAG if client is available and RAG is enabled
    if llm_client is not None and os.getenv("ENABLE_RAG", "0") == "1":
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

    # Get Kafka processor
    kafka_proc = get_kafka_processor()
    
    # Enrich prompt with real-time data from Kafka if available
    enriched_system_instr = system_instr
    if kafka_proc:
        try:
            enriched_system_instr = kafka_proc.enrich_prompt_with_data(system_instr)
        except Exception as e:
            logger.warning(f"Could not enrich prompt with Kafka data: {e}")
    
    # Prepare the final prompt
    final_messages = []
    for msg in messages:
        if msg["role"] == "system":
            final_messages.append({"role": "system", "content": enriched_system_instr})
        else:
            final_messages.append(msg)
    
    # Route to the appropriate provider based on project configuration
    if project_config.provider == ProviderType.OLLAMA:
        if ollama_provider is not None:
            try:
                # Convert messages to the format expected by Ollama
                ollama_messages = [Message(role=msg["role"], content=msg["content"]) for msg in final_messages]
                
                # Generate response using Ollama
                response_parts = []
                async for token in ollama_provider.generate_response(
                    messages=ollama_messages,
                    model=project_config.model,
                    stream=False  # For now, we'll collect the full response
                ):
                    response_parts.append(token)
                
                full_reply = "".join(response_parts)
                
                # Save to history
                chat_sessions[session_id].append({"role": "user", "content": user_message})
                chat_sessions[session_id].append({"role": "assistant", "content": full_reply})
                
                return {
                    "reply": full_reply,
                    "sources": sources
                }
            except Exception as e:
                logger.exception(f"Ollama error: {e}")
                return {
                    "reply": f"Ollama service unavailable: {str(e)}",
                    "sources": sources
                }
        else:
            return {
                "reply": "Ollama provider not available. Please check configuration.",
                "sources": sources
            }
    elif project_config.provider == ProviderType.LOCAL_LLM:
        # Use local LLM if available, otherwise return error
        if llm_client is not None:
            try:
                # Convert the messages to a single prompt for local LLM
                prompt = ""
                for msg in final_messages:
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    prompt += f"{role}: {content}\n"
                
                # Add instruction for the assistant's response
                prompt += "Assistant:"
                
                full_reply = llm_client.generate_response(prompt, session_id=session_id, temperature=0.7)
                
                # Save to history
                chat_sessions[session_id].append({"role": "user", "content": user_message})
                chat_sessions[session_id].append({"role": "assistant", "content": full_reply})
                
                return {
                    "reply": full_reply,
                    "sources": sources
                }
            except Exception as e:
                logger.exception(f"Local LLM error: {e}")
                return {
                    "reply": "Local LLM service unavailable. Please try again.",
                    "sources": sources
                }
        else:
            return {
                "reply": "LLM service unavailable. Please check that the local model is properly configured.",
                "sources": sources
            }
    else:
        return {
            "reply": f"Unsupported provider: {project_config.provider}",
            "sources": sources
        }

@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest):
    """Streaming endpoint for Ollama responses"""
    session_id = request.sessionId or str(uuid.uuid4())
    user_message = request.message
    
    # Initialize history if new session
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Get project configuration based on request
    project_config = project_manager.get_project(request.project_id) or ProjectConfig(
        project_id=request.project_id,
        provider=ProviderType.OLLAMA,  # Default to Ollama for streaming
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    )
    
    # Override provider/model if specified in request
    if request.provider:
        project_config.provider = ProviderType(request.provider)
    if request.model:
        project_config.model = request.model

    # 1. Retrieval
    sources = []
    context_text = ""
    
    # Only attempt RAG if client is available and RAG is enabled
    if llm_client is not None and os.getenv("ENABLE_RAG", "0") == "1":
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

    # Get Kafka processor
    kafka_proc = get_kafka_processor()
    
    # Enrich prompt with real-time data from Kafka if available
    enriched_system_instr = system_instr
    if kafka_proc:
        try:
            enriched_system_instr = kafka_proc.enrich_prompt_with_data(system_instr)
        except Exception as e:
            logger.warning(f"Could not enrich prompt with Kafka data: {e}")
    
    # Prepare the final prompt
    final_messages = []
    for msg in messages:
        if msg["role"] == "system":
            final_messages.append({"role": "system", "content": enriched_system_instr})
        else:
            final_messages.append(msg)

    async def stream_generator():
        # Only Ollama provider supports streaming in this implementation
        if project_config.provider == ProviderType.OLLAMA and ollama_provider is not None:
            try:
                # Convert messages to the format expected by Ollama
                ollama_messages = [Message(role=msg["role"], content=msg["content"]) for msg in final_messages]
                
                # Initialize response buffer for history
                full_reply = ""
                
                # Stream response from Ollama
                async for token in ollama_provider.generate_streaming_response(
                    messages=ollama_messages,
                    model=project_config.model
                ):
                    yield token
                
                # After streaming completes, save the full response to history
                # Note: In a real streaming scenario, we'd need to accumulate the full response
                # For now, we'll log that the streaming is complete
                logger.info(f"Streaming completed for session {session_id}")
                
            except Exception as e:
                logger.exception(f"Ollama streaming error: {e}")
                yield f"data: {{\"error\": \"Ollama streaming error: {str(e)}\"}}\n\n"
        else:
            yield f"data: {{\"error\": \"Streaming only supported for Ollama provider\"}}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.get("/api/health")
async def health_check():
    rag_enabled = os.getenv("ENABLE_RAG", "0") == "1"
    ollama_available = ollama_provider is not None
    local_llm_available = llm_client is not None
    
    return {
        "status": "ok",
        "rag_enabled": rag_enabled,
        "ollama_available": ollama_available,
        "local_llm_available": local_llm_available,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def legacy_health():
    rag_enabled = os.getenv("ENABLE_RAG", "0") == "1"
    return {
        "status": "ok",
        "rag_enabled": rag_enabled
    }

@app.get("/api/health/ollama")
async def ollama_health_check():
    """Health check for Ollama service"""
    if ollama_provider:
        try:
            result = await ollama_provider.health_check()
            return result
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    else:
        return {"status": "unhealthy", "error": "Ollama provider not initialized"}

@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    projects = project_manager.list_projects()
    return {"projects": [p.dict() for p in projects]}

@app.post("/api/projects")
async def create_project(config: ProjectConfig):
    """Create a new project"""
    project = project_manager.create_project(config)
    return {"project": project.dict()}

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, config_update: dict):
    """Update project configuration"""
    project = project_manager.update_project(project_id, **config_update)
    if project:
        return {"project": project.dict()}
    else:
        raise HTTPException(status_code=404, detail="Project not found")

@app.get("/api/models/ollama")
async def list_ollama_models():
    """List available Ollama models"""
    if ollama_provider:
        try:
            models = await ollama_provider.list_models()
            return {"models": models}
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching Ollama models: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="Ollama provider not initialized")

@app.post("/api/ingest")
async def api_ingest():
    if llm_client is None:
        return {"status": "error", "message": "Local LLM client not available"}
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