from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import openai
from .kafka_producer import get_kafka_producer
from .kafka_consumer import KafkaConsumerService
from .database import get_db, SessionLocal
from . import models, schemas
from sqlalchemy.orm import Session
import threading
import time

# Load environment variables
load_dotenv()

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


def call_openai_directly(prompt: str) -> str:
    """Directly call OpenAI API from the backend as a fallback"""
    try:
        # Check if API key is set
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logging.warning('OpenAI API key not set in backend.')
            return "I'm sorry, but the AI service is not properly configured. Please check that the API key is set."
        
        client = openai.OpenAI(api_key=api_key)
        model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for a chatbot application. Respond to the user's message."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except openai.AuthenticationError:
        logging.error('OpenAI Authentication Error: Invalid API key in backend')
        return "I'm sorry, but there's an issue with the AI service configuration. Please check the API key."
    except openai.RateLimitError:
        logging.error('OpenAI Rate Limit Error in backend')
        return "I'm currently experiencing high demand. Please try again in a moment."
    except openai.APIConnectionError:
        logging.error('OpenAI API Connection Error in backend')
        return "I'm having trouble connecting to the AI service. Please try again later."
    except openai.APIError as e:
        logging.error(f'OpenAI API Error in backend: {str(e)}')
        return "I'm having trouble processing your request. Please try again."
    except Exception as e:
        logging.error(f'Error calling OpenAI from backend: {str(e)}')
        return "I'm having trouble connecting to the AI service right now. Please try again later."


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
                        timestamp=datetime.fromtimestamp(time.time())
                    )
                    db.add(chat_log)
                    db.commit()
                except Exception as e:
                    logger.error(f'Error saving chat log: {str(e)}')
                finally:
                    db.close()
            
            # Add retry logic for consumer initialization
            max_retries = 30
            retry_count = 0
            while retry_count < max_retries:
                try:
                    consumer_service = KafkaConsumerService()
                    consumer_service.start_consuming(['llm-responses', 'rl-responses'], handle_response_message)
                    break  # Break if successful
                except Exception as e:
                    retry_count += 1
                    logger.error(f'Failed to initialize Kafka consumer (attempt {retry_count}/{max_retries}): {str(e)}')
                    if retry_count >= max_retries:
                        logger.error('Max retries reached for Kafka consumer initialization. Consumer will not start.')
                        return
                    time.sleep(10)  # Wait before retrying
        
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
            simulated_response = f"Simulated response to: {request.message}"
            
            # Broadcast to WebSocket clients
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
                    timestamp=datetime.fromtimestamp(time.time())
                )
                db.add(chat_log)
                db.commit()
            except Exception as e:
                logger.error(f'Error saving chat log: {str(e)}')
            finally:
                db.close()
            
            return ChatResponse(response=simulated_response, timestamp=time.time())
        else:
            try:
                # Send to Kafka topic
                producer = get_kafka_producer()
                producer.send_message('chat-messages', message_data)
            except Exception as e:
                logger.error(f'Error sending message to Kafka: {str(e)}. Falling back to direct OpenAI call.')
                # Fallback to direct OpenAI API call if Kafka is unavailable
                try:
                    direct_response = call_openai_directly(request.message)
                except Exception as openai_error:
                    logger.error(f'Direct OpenAI call also failed: {str(openai_error)}')
                    # If both Kafka and OpenAI fail, return a meaningful error
                    direct_response = "I'm sorry, but I'm having trouble connecting to the AI service right now. Please try again later."
                
                # Save to database
                db = SessionLocal()
                try:
                    chat_log = models.ChatLog(
                        user_id=request.user_id,
                        session_id=request.session_id,
                        user_message=request.message,
                        bot_response=direct_response,
                        timestamp=datetime.fromtimestamp(time.time())
                    )
                    db.add(chat_log)
                    db.commit()
                finally:
                    db.close()
                
                # Broadcast response to WebSocket
                response_message_data = {
                    'user_id': request.user_id,
                    'session_id': request.session_id,
                    'original_message': request.message,
                    'llm_response': direct_response,
                    'timestamp': time.time(),
                    'source': 'direct_openai'
                }
                await manager.broadcast(json.dumps(response_message_data))
                
                return ChatResponse(response=direct_response, timestamp=time.time())
            
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