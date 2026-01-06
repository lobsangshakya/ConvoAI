from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import logging
import os
from datetime import datetime
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket connection: {str(e)}")
                disconnected_connections.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected_connections:
            try:
                self.active_connections.remove(connection)
            except ValueError:
                pass  # Connection already removed


manager = ConnectionManager()


@app.on_event("startup")
def startup_event():
    # Start Kafka consumer to listen for responses from RL agent and LLM
    if not LOCAL_MODE:
        def kafka_consumer_loop():
            async def handle_response_message_async(message_data):
                # Broadcast the response to all connected WebSocket clients
                await manager.broadcast(json.dumps(message_data))
                
                # Also save to database
                db = SessionLocal()
                try:
                    # Create a chat log entry
                    chat_log = models.ChatLog(
                        user_id=message_data.get('user_id', 'unknown'),
                        session_id=message_data.get('session_id', 'unknown'),
                        user_message=message_data.get('original_message', ''),
                        bot_response=message_data.get('llm_response', '') or message_data.get('suggested_response', ''),
                        timestamp=datetime.fromtimestamp(time.time())
                    )
                    db.add(chat_log)
                    db.commit()
                except Exception as e:
                    logger.error(f'Error saving chat log: {str(e)}')
                finally:
                    db.close()
            
            def handle_response_message(message_data):
                # Run the async function in the asyncio event loop
                import asyncio
                try:
                    # Get the running event loop if available
                    loop = asyncio.get_running_loop()
                    # Schedule the coroutine in the existing loop
                    asyncio.run_coroutine_threadsafe(handle_response_message_async(message_data), loop)
                except RuntimeError:
                    # No event loop running, create a new one
                    asyncio.run(handle_response_message_async(message_data))
            
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
            logger.info(f"Processing message in local mode: {request.message}")
            # Simulate a response after a short delay
            # Create a more natural and helpful response
            user_msg = request.message.lower().strip()
            
            # Check for greetings first - match whole words or start of sentence
            if any(user_msg.startswith(greeting) or f' {greeting} ' in f' {user_msg} ' or user_msg.endswith(f' {greeting}') for greeting in ["hello", "hi", "hey"]):
                simulated_response = "Hello there! How can I assist you today?"
            elif "help" in user_msg and not any(word in user_msg for word in ["something", "anything"]):
                simulated_response = "I'm here to help! You can ask me questions or have a conversation about various topics."
            elif "thank" in user_msg or "thanks" in user_msg:
                simulated_response = "You're welcome! Is there anything else I can help with?"
            elif any(bye_word in user_msg for bye_word in ["bye", "goodbye"]):
                simulated_response = "Goodbye! Feel free to come back if you have more questions."
            else:
                # Generate a more contextually relevant response
                user_msg_lower = user_msg.lower()
                if "llm" in user_msg_lower or "large language model" in user_msg_lower:
                    simulated_response = "A Large Language Model (LLM) is an AI model that understands and generates human-like text based on vast amounts of training data. Examples include GPT, Claude, and Llama."
                elif "ai" in user_msg_lower or "artificial intelligence" in user_msg_lower:
                    simulated_response = "Artificial Intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence, such as understanding language, recognizing patterns, and making decisions."
                elif "chatbot" in user_msg_lower or "bot" in user_msg_lower:
                    simulated_response = "A chatbot is an AI program designed to simulate conversation with humans through text or voice interactions. This system is an AI-powered chatbot with reinforcement learning capabilities."
                elif any(word in user_msg_lower for word in ["name", "call", "you"]):
                    simulated_response = "I'm an AI assistant powered by advanced language models. You can ask me questions or have a conversation about various topics."
                elif any(word in user_msg_lower for word in ["weather", "temperature", "rain", "sunny"]):
                    simulated_response = "I don't have access to real-time weather data in local mode, but I can help you find weather information if connected to the appropriate services."
                elif any(word in user_msg_lower for word in ["time", "date", "today"]):
                    now = datetime.now()
                    simulated_response = f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}. In a full implementation, I would provide more contextually aware responses."
                else:
                    # Default response with more helpful content
                    simulated_response = f"Thanks for asking about '{request.message}'! In a full implementation with active AI models, I would provide a detailed and accurate response. This is a simulated response in local development mode."

            
            # Save to database first
            db = SessionLocal()
            try:
                # Create a chat log entry
                chat_log = models.ChatLog(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    user_message=request.message,
                    bot_response=simulated_response,
                    timestamp=datetime.fromtimestamp(time.time())
                )
                db.add(chat_log)
                db.commit()
            except Exception as e:
                logger.error(f'Error saving chat log: {str(e)}')
            finally:
                db.close()
            
            # Prepare message data for WebSocket
            current_timestamp = datetime.fromtimestamp(time.time())
            simulated_message_data = {
                'user_id': request.user_id,
                'session_id': request.session_id,
                'original_message': request.message,
                'llm_response': simulated_response,
                'timestamp': time.time(),
                'source': 'simulator'
            }
            logger.info(f"Broadcasting simulated response: {simulated_response}")
            
            # Broadcast to WebSocket clients
            await manager.broadcast(json.dumps(simulated_message_data))
            
            # Return the response immediately
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
                    timestamp=datetime.fromtimestamp(time.time())
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