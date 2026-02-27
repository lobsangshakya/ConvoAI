# ConvoAI

AI chatbot with React frontend and FastAPI backend powered by local Ollama.

## Quick Start

### Prerequisites
- Node.js (v14+)
- Python 3.11
- Ollama installed locally

### 1. Install Ollama and Pull Model
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Qwen model
ollama pull qwen2.5:3b

# Start Ollama server
ollama serve
```

### 2. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start Frontend (new terminal)
```bash
cd frontend
npm install
npm start
```

### 4. Open App
Visit http://localhost:3000

## Project Structure

```
ConvoAI/
├── backend/                 # FastAPI server
│   ├── app/
│   │   ├── main.py          # API endpoints
│   │   ├── ollama_service.py # Ollama LLM wrapper
│   │   └── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── runtime.txt
├── frontend/               # React app
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── knowledge/              # Optional RAG documents
└── .env.example
```

## Environment Variables

Create `.env` file:

```env
# Backend Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=60
PORT=8000
FRONTEND_ORIGIN=*

# Optional RAG Configuration
ENABLE_RAG=0

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
```

## API Endpoints

- `POST /api/chat` - Send message, get AI response
- `POST /api/chat/stream` - Streaming chat response
- `GET /api/health` - Health check

Example:
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
```

## Docker Setup

### Using Docker Compose

1. Ensure Ollama is running on host:
```bash
ollama serve
```

2. Start application:
```bash
docker-compose up --build
```

### Manual Docker Build

Backend:
```bash
cd backend
docker build -t convoai-backend .
docker run -p 8000:8000 convoai-backend
```

Frontend:
```bash
cd frontend
docker build -t convoai-frontend .
docker run -p 3000:3000 convoai-frontend
```

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Build Frontend
```bash
cd frontend
npm run build
```

## Troubleshooting

- "Ollama not available": Make sure `ollama serve` is running
- "Model not found": Run `ollama pull qwen2.5:3b`
- "Port already in use": `lsof -ti:8000 | xargs kill -9`
- Build fails: `rm -rf node_modules package-lock.json && npm install`

## Optional RAG

To enable knowledge base:

1. Add documents to `knowledge/` folder
2. Set `ENABLE_RAG=1` in `.env`
3. Restart backend

## License

MIT
