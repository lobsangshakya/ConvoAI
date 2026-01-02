from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import logging
import os
from .kafka_producer import get_kafka_producer
from .kafka_consumer import KafkaConsumerService
from .database import get_db, SessionLocal
from . import models, schemas
from sqlalchemy.orm import Session
import threading
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chatbot Backend", description="Backend API for AI-powered chatbot")

# Database dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Check if running in local mode (without Kafka)
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"


# Models for API requests

class MessageRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: float


# Store active WebSocket connections
active_connections: List[WebSocket] = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # If sending fails, remove the connection
                self.active_connections.remove(connection)


manager = ConnectionManager()


@app.on_event("startup")
def startup_event():
    # Start Kafka consumer to listen for responses from RL agent and LLM
    if not LOCAL_MODE:
        def kafka_consumer_loop():
            def handle_response_message(message_data):
                # Broadcast the response to all connected WebSocket clients
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(manager.broadcast(json.dumps(message_data)))
                loop.close()
                
                # Also save to database
                db = SessionLocal()
                try:
                    # Create a chat log entry
                    chat_log = models.ChatLog(
                        user_id=message_data.get('user_id', 'unknown'),
                        session_id=message_data.get('session_id', 'unknown'),
                        user_message=message_data.get('original_message', ''),
                        bot_response=message_data.get('llm_response', '') or message_data.get('suggested_response', ''),
                        timestamp=time.time()
                    )
                    db.add(chat_log)
                    db.commit()
                except Exception as e:
                    logger.error(f'Error saving chat log: {str(e)}')
                finally:
                    db.close()
            
            consumer_service = KafkaConsumerService()
            consumer_service.start_consuming(['llm-responses', 'rl-responses'], handle_response_message)
        
        # Run Kafka consumer in a separate thread
        consumer_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
        consumer_thread.start()
    else:
        logger.info("Running in local mode without Kafka")


@app.post("/chat/send", response_model=ChatResponse)
async def send_message(request: MessageRequest):
    """Send a message to the chatbot and receive a response"""
    try:
        message_data = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "message": request.message,
            "timestamp": time.time()
        }
        
        # In local mode, we simulate the response
        if LOCAL_MODE:
            # Simulate a response after a short delay
            simulated_response = f"Simulated response to: {request.message}"
            
            # Broadcast to WebSocket clients
            simulated_message_data = {
                'user_id': request.user_id,
                'session_id': request.session_id,
                'original_message': request.message,
                'llm_response': simulated_response,
                'timestamp': time.time(),
                'source': 'simulator'
            }
            await manager.broadcast(json.dumps(simulated_message_data))
            
            # Save to database
            db = SessionLocal()
            try:
                # Create a chat log entry
                chat_log = models.ChatLog(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    user_message=request.message,
                    bot_response=simulated_response,
                    timestamp=time.time()
                )
                db.add(chat_log)
                db.commit()
            except Exception as e:
                logger.error(f'Error saving chat log: {str(e)}')
            finally:
                db.close()
            
            return ChatResponse(response=simulated_response, timestamp=time.time())
        else:
            # Send to Kafka topic
            producer = get_kafka_producer()
            producer.send_message('chat-messages', message_data)
            
            # Save to database
            db = SessionLocal()
            try:
                chat_log = models.ChatLog(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    user_message=request.message,
                    bot_response="",  # Will be filled when response comes
                    timestamp=time.time()
                )
                db.add(chat_log)
                db.commit()
            finally:
                db.close()
            
            # Return a placeholder response
            # Actual response will come via WebSocket
            return ChatResponse(response="Message received, processing...", timestamp=time.time())
    
    except Exception as e:
        logger.error(f'Error sending message: {str(e)}')
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            data = await websocket.receive_text()
            # For now, we just keep the connection alive
            # In a real app, you might process additional commands
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Get chat history for a specific session"""
    chat_logs = db.query(models.ChatLog).filter(models.ChatLog.session_id == session_id).all()
    return chat_logs


@app.get("/")
async def root():
    return {"message": "AI Chatbot Backend API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)