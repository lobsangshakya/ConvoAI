# ConvoAI — Simple AI Chatbot

A beginner-friendly chatbot with a **React** frontend and **FastAPI** backend, powered by [Ollama](https://ollama.ai) for local AI inference.

![React](https://img.shields.io/badge/React-18-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Python-green) ![Ollama](https://img.shields.io/badge/Ollama-Local_AI-orange)

---

## What Does This Project Do?

You type a message → the React frontend sends it to the FastAPI backend → the backend forwards it to Ollama (a local AI model running on your machine) → and streams the response back in real time, just like ChatGPT.

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  React   │ ───▶  │  FastAPI  │ ───▶  │  Ollama  │
│ Frontend │ ◀───  │  Backend  │ ◀───  │  (AI)    │
└──────────┘       └──────────┘       └──────────┘
 localhost:3000     localhost:8000     localhost:11434
```

---

## Prerequisites

Make sure you have these installed:

| Tool       | Version | How to install                          |
| ---------- | ------- | --------------------------------------- |
| **Node.js** | 18+     | [nodejs.org](https://nodejs.org)       |
| **Python**  | 3.9+    | [python.org](https://python.org)       |
| **Ollama**  | latest  | [ollama.ai](https://ollama.ai)         |

---

## Quick Start (3 steps)

### 1. Install Ollama and pull a model

```bash
# After installing Ollama from ollama.ai, pull a model:
ollama pull qwen2.5:3b

# Start the Ollama server (it may already be running):
ollama serve
```

### 2. Start the Backend

```bash
# Open a terminal and run:
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

You should see: `Uvicorn running on http://127.0.0.1:8000`

### 3. Start the Frontend

```bash
# Open a NEW terminal and run:
cd frontend
npm install
npm start
```

Your browser will open `http://localhost:3000` — start chatting! 🎉

---

## Project Structure

```
ConvoAI/
├── backend/                 # Python FastAPI server
│   ├── app/
│   │   ├── main.py          # API endpoints (/api/chat, /api/health)
│   │   ├── ollama_provider.py  # Talks to Ollama
│   │   └── rag_service.py   # (Optional) RAG for knowledge-base Q&A
│   └── requirements.txt     # Python dependencies
│
├── frontend/                # React chat interface
│   ├── src/
│   │   ├── App.js           # Main chat component
│   │   ├── App.css          # Styles
│   │   └── index.js         # React entry point
│   ├── public/index.html
│   └── package.json
│
├── knowledge/               # (Optional) Drop .txt/.md files here for RAG
│   └── sample.txt
│
├── .env                     # Your local config (not committed to git)
├── .env.example             # Template — copy this to .env
└── README.md                # You are here!
```

---

## Configuration

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

| Variable             | Default                       | Description                        |
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