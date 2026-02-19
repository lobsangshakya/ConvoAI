# ConvoAI

ConvoAI is a modern conversational AI platform featuring local LLM inference (Ollama or Transformers), Retrieval Augmented Generation (RAG), and a premium React chat interface with project-based provider selection.

## Key Features
- **Multiple LLM Providers**: Choose between local Ollama models or Transformers for inference
- **Project-Based Configuration**: Per-project settings for providers and models
- **Retrieval Augmented Generation (RAG)**: Automatically retrieves relevant context from your local knowledge base for more accurate and context-aware answers
- **Conversation History**: Maintains session-based conversation history for contextual interactions
- **Real-time Streaming**: Smooth, ChatGPT-like typing experience with token-by-token streaming
- **Premium Chat UI**: Modern, responsive design with project/provider selection dropdowns

## Architecture
- **Frontend**: React with real-time streaming and project selector
- **Backend**: FastAPI with RAG service, local LLM integration, and Ollama provider
- **LLM**: Local Transformers model or Ollama (qwen2.5:3b, etc.)
- **Embeddings**: Sentence transformers for local embeddings

## API Endpoints
- `POST /api/chat`: Main endpoint for RAG chat
  - Body: `{ sessionId: string, message: string, project_id?: string, provider?: string, model?: string }`
  - Response: `{ reply: string, sources?: [{id: string, preview: string}] }`
- `POST /api/chat/stream`: Streaming endpoint for Ollama responses (Server-Sent Events)
- `GET /api/health`: Checks API status

## Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- Ollama (optional, for Ollama provider)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd convoai
```

### 2. Environment Setup
Create a `.env` file in the root directory:
```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=60

# RAG Configuration
ENABLE_RAG=0  # Set to 1 to enable RAG functionality

# Kafka Configuration (disabled by default)
ENABLE_KAFKA=false

# Frontend Configuration
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 3. Knowledge Ingestion (Optional)
Place any markdown (`.md`) or text (`.txt`) files in the `/knowledge` directory. They will be automatically indexed on backend startup when RAG is enabled.

### 4. Running the Application

#### Option A: With Ollama
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull qwen2.5:3b
   ```
3. Start Ollama server:
   ```bash
   ollama serve
   ```

#### Option B: Local Setup
1. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Start the backend:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. In a new terminal, install and start the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

The application will be available at `http://localhost:3000`.

## Project Selection
The UI includes dropdowns to select:
- Project: Choose between different project configurations
- Provider: Switch between "Local Ollama" and "Local LLM"
- Model: Specify the model name

## Deployment
ConvoAI is ready for deployment on:
- **Frontend**: Vercel/Netlify for React build
- **Backend**: Render/Fly.io for FastAPI application
- **Containerized**: Use Docker with the provided configurations

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog
See [CHANGELOG.md](./CHANGELOG.md) for a full list of changes and updates.

## Acknowledgments
- Built with React and FastAPI
- Powered by Ollama for local LLM inference
- Uses Transformers for local model support