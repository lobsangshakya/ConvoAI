# AI-Powered Chatbot

A real-time chatbot system using Python, React, Docker, Kafka, and Reinforcement Learning.

## Architecture

The system consists of:
- **Backend**: FastAPI-based service handling API requests and Kafka integration
- **Frontend**: React-based chat interface
- **RL Agent**: Python-based reinforcement learning agent that evaluates interactions
- **LLM Service**: Large language model service for generating responses
- **Kafka**: Message broker for communication between services
- **Database**: PostgreSQL for storing conversation logs

## Prerequisites

- Docker
- Docker Compose

## Setup Instructions

1. Clone the repository
2. Navigate to the project directory
3. Run the application using Docker Compose:

```bash
docker-compose up --build
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Configuration

### Environment Variables

For the LLM service, you can configure:
- `USE_OPENAI`: Set to `true` to use OpenAI API (default: `false`)
- `OPENAI_API_KEY`: Your OpenAI API key (required if USE_OPENAI=true)
- `HF_MODEL`: Hugging Face model to use (default: `gpt2`)

### Kafka Topics

The system uses the following Kafka topics:
- `chat-messages`: For incoming user messages
- `llm-responses`: For responses from the LLM service
- `rl-responses`: For responses from the RL agent

## Services

### Backend

The backend service exposes the following endpoints:

- `POST /chat/send`: Send a message to the chatbot
- `GET /chat/history/{session_id}`: Get chat history for a session
- `GET /`: Health check endpoint
- `WS /ws`: WebSocket endpoint for real-time updates

### Frontend

The React frontend provides a real-time chat interface that connects to the backend via REST API and WebSocket.

### RL Agent

The reinforcement learning agent:
- Consumes messages from the `chat-messages` topic
- Calculates reward based on conversation quality
- Generates response suggestions
- Publishes results to the `rl-responses` topic

### LLM Service

The LLM service:
- Consumes messages from the `chat-messages` topic
- Generates human-like responses using either OpenAI or Hugging Face models
- Publishes results to the `llm-responses` topic

## Development

To run individual services during development:

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### RL Agent

```bash
cd rl_agent
pip install -r requirements.txt
python -m app.rl_agent
```

### LLM Service

```bash
cd llm
pip install -r requirements.txt
python -m app.llm_service
```

## Project Structure

```
ChatBot/
├── backend/           # FastAPI backend
│   ├── app/
│   ├── models/
│   ├── services/
│   └── utils/
├── frontend/          # React frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── rl_agent/          # Reinforcement learning agent
│   ├── app/
│   ├── models/
│   └── services/
├── llm/               # LLM service
│   ├── app/
│   ├── models/
│   └── services/
├── docker-compose.yml
└── README.md
```

## How It Works

1. User sends a message through the React frontend
2. Frontend sends the message to the backend via REST API
3. Backend publishes the message to the `chat-messages` Kafka topic
4. Both RL Agent and LLM Service consume the message
5. RL Agent calculates a reward and generates a response suggestion
6. LLM Service generates a response using the language model
7. Both services publish their responses to their respective Kafka topics
8. Backend consumes responses from Kafka and broadcasts them via WebSocket
9. Frontend receives the response in real-time and displays it

## Technologies Used

- **Backend**: FastAPI, SQLAlchemy, Kafka
- **Frontend**: React, WebSocket
- **RL**: TensorFlow, NumPy
- **LLM**: Transformers, PyTorch, OpenAI API
- **Database**: PostgreSQL
- **Message Broker**: Apache Kafka
- **Containerization**: Docker, Docker Compose# ConvoAI
