# ConvoAI

ConvoAI is a production-ready conversational AI platform featuring local LLM inference (transformers or Ollama), Retrieval Augmented Generation (RAG), real-time data processing with Kafka, and a premium chat interface with project-based provider selection.

## Key Features
- **Multiple LLM Providers**: Choose between local transformers models or Ollama for inference
- **Project-Based Configuration**: Per-project settings for providers and models
- **Retrieval Augmented Generation (RAG)**: Automatically retrieves relevant context from your local `/knowledge` base to provide more accurate and context-aware answers.
- **Conversation History**: Maintains session-based conversation history for contextual interactions.
- **Real-time Data Processing**: Integrates with Apache Kafka for live data ingestion.
- **Premium Chat UI**: Modern, responsive design with project/provider selection dropdowns.
- **Robust AI Integration**: Centralized model handling with configurable providers and error handling.

## Architecture
- **Frontend**: React (Polished UI with real-time updates and project selector).
- **Backend**: FastAPI (RAG Service, Local LLM integration, Ollama provider, Kafka consumer).
- **LLM**: Local transformers model (DialoGPT, BlenderBot, etc.) or Ollama (qwen2.5:3b, etc.).
- **Embeddings**: Sentence transformers for local embeddings or Ollama.
- **Real-time Data**: Apache Kafka for streaming data ingestion and processing.

## API Endpoints
- `POST /api/chat`: Main endpoint for RAG chat.
  - Body: `{ sessionId: string, message: string, project_id?: string, provider?: string, model?: string }`
  - Response: `{ reply: string, sources?: [{id: string, preview: string}] }`
- `POST /api/chat/stream`: Streaming endpoint for Ollama responses (Server-Sent Events).
- `GET /api/health`: Checks API and RAG ingestion status.
- `GET /api/health/ollama`: Checks Ollama service connectivity.
- `GET /api/models/ollama`: Lists available Ollama models.
- `POST /api/ingest`: Reload knowledge base from `/backend/knowledge/*.txt` files.
- `GET /api/projects`: List all projects.
- `POST /api/projects`: Create a new project.

## Quick Start

### 1. Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- Ollama (optional, for Ollama provider)

### 2. Environment Setup
Create a `.env` file in the root directory:
```bash
# Local LLM Configuration
LOCAL_LLM_MODEL=microsoft/DialoGPT-medium
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=60
OLLAMA_MAX_HISTORY_TURNS=10

# RAG Configuration
ENABLE_RAG=1  # Set to 1 to enable RAG functionality

# Kafka Configuration
ENABLE_KAFKA=false  # Set to true to enable Kafka real-time data processing

# Optional OpenAI configuration (fallback)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small

REACT_APP_BACKEND_URL=http://localhost:8000
```

### 3. Knowledge Ingestion
Place any markdown (`.md`) or text (`.txt`) files in the `/knowledge` directory. They will be automatically indexed on backend startup.

### 4. Running with Ollama Support

#### Option A: Using Ollama
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the default model:
   ```bash
   ollama pull qwen2.5:3b
   ```
3. Start Ollama server:
   ```bash
   ollama serve
   ```
4. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
5. Start the backend:
   ```bash
   uvicorn app.main:app --reload
   ```
6. In a new terminal, start the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

#### Option B: Using Local Transformers Only
1. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Start the backend:
   ```bash
   uvicorn app.main:app --reload
   ```
3. In a new terminal, start the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

## Project Selection
The UI includes dropdowns to select:
- Project: Choose between different project configurations
- Provider: Switch between "Local LLM" and "Local Ollama"
- Model: Specify the model name (e.g., "qwen2.5:3b" for Ollama)

## Troubleshooting

### Common Issues and Solutions

1. **"Failed to fetch" Error**:
   - Ensure backend is running on `http://localhost:8000`
   - Check that `REACT_APP_BACKEND_URL=http://localhost:8000` in your `.env` file
   - Verify CORS is properly configured (already set to allow all origins)

2. **ESLint no-loop-func Warning**:
   - Fixed by creating stable local copies inside loops in the streaming implementation

3. **Ollama Connection Issues**:
   - Verify Ollama is running with `ollama serve`
   - Check that the model is pulled: `ollama pull qwen2.5:3b`
   - Ensure `OLLAMA_BASE_URL` matches your Ollama instance

4. **Health Check**:
   - Test backend health: `curl http://localhost:8000/api/health`
   - Test Ollama health: `curl http://localhost:8000/api/health/ollama`

## Streaming Support
When using the Ollama provider, the application supports real-time streaming responses for a smoother user experience.

## Deployment
ConvoAI is deployment-ready for:
- **Vercel/Netlify**: Simple React build deployment.
- **Render/Fly.io**: FastAPI container deployment.
- **Docker**: Use the provided `docker-compose.yml` with Kafka services.

## Recent Changes
See [CHANGES.md](./CHANGES.md) for a full list of updates.