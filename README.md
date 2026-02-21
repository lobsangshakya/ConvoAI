# ConvoAI - Simple AI Chatbot

A beginner-friendly chatbot application with React frontend and FastAPI backend.

## 🚀 Quick Start

### Prerequisites
- **Node.js** (v14 or higher) - [Download](https://nodejs.org/)
- **Python 3.11** - [Download](https://python.org/)
- **OpenAI API Key** - [Get yours](https://platform.openai.com/api-keys)

### One-Command Setup

1. **Clone and setup:**
```bash
git clone <your-repo>
cd ChatBot
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Start backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

4. **Start frontend** (in new terminal):
```bash
cd frontend
npm install
npm start
```

5. **Open app:** http://localhost:3000

That's it! 🎉

## 📁 Project Structure

```
ConvoAI/
├── backend/           # Python FastAPI server
│   ├── app/
│   │   ├── main.py      # Main API with OpenAI
│   │   └── __init__.py
│   ├── requirements.txt
│   └── runtime.txt        # Python 3.11.9 for Render
├── frontend/          # React web app
│   ├── src/
│   │   ├── App.js       # Main chat component
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   └── package.json
├── knowledge/         # Optional RAG documents
├── .env.example      # Environment template
└── README.md
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```env
# Backend (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Optional
PORT=8000
ENABLE_RAG=0  # Set to 1 to enable RAG
| -------------------- | ----------------------------- | ---------------------------------- |
| `OLLAMA_BASE_URL`    | `http://127.0.0.1:11434`     | Where Ollama is running            |
| `OLLAMA_MODEL`       | `qwen2.5:3b`                 | Which model to use                 |
| `OLLAMA_TIMEOUT`     | `60`                          | Request timeout in seconds         |
| `ENABLE_RAG`         | `0`                           | Set to `1` to enable RAG           |
| `REACT_APP_BACKEND_URL` | `http://localhost:8000`    | Backend URL for the frontend       |

---

## API Endpoints

| Method | Endpoint           | Description                    |
| ------ | ------------------ | ------------------------------ |
| POST   | `/api/chat`        | Send a message, get a reply    |
| POST   | `/api/chat/stream` | Send a message, get a streamed reply |
| GET    | `/api/health`      | Check if the server is running |

**Example request:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

---

## Optional: RAG (Knowledge Base)

Want the bot to answer questions using your own documents?

1. Drop `.txt` or `.md` files into the `knowledge/` folder
2. Set `ENABLE_RAG=1` in your `.env` file
3. Restart the backend

The bot will automatically read and index your documents on startup.

---

## Troubleshooting

| Problem                          | Solution                                            |
| -------------------------------- | --------------------------------------------------- |
| "Ollama is not available"       | Make sure Ollama is running: `ollama serve`          |
| "Failed to fetch" in frontend   | Make sure the backend is running on port 8000        |
| Slow first response             | First response is slower while the model loads       |
| "Model not found"               | Pull the model first: `ollama pull qwen2.5:3b`      |

---

## License

MIT — see [LICENSE](./LICENSE) for details.