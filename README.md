# ConvoAI - Production-Ready AI Chatbot

A beginner-friendly chatbot application with React frontend and FastAPI backend, powered by Groq LLM API.

## 🚀 What This Project Does

ConvoAI is a simple, production-ready chatbot that:
- **React Frontend** - Modern, responsive chat interface
- **FastAPI Backend** - Python API with Groq LLM integration  
- **Groq LLM** - Fast AI responses using Llama models
- **Session Management** - Maintains conversation context
- **Render Ready** - Deploys cleanly to Render platform

## 📋 Prerequisites

- **Node.js** (v14 or higher) - [Download](https://nodejs.org/)
- **Python 3.11** - [Download](https://python.org/)
- **Groq API Key** - [Get free key](https://console.groq.com/)

## ⚡ Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo>
cd ChatBot
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Groq API key
# GROQ_API_KEY=gsk_your_api_key_here
```

### 3. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend (new terminal)
```bash
cd frontend
npm install
npm start
```

### 5. Open App
Visit http://localhost:3000 and start chatting! 🎉

## 📁 Project Structure

```
ConvoAI/
├── backend/                 # Python FastAPI server
│   ├── app/
│   │   ├── main.py          # Main API endpoints
│   │   ├── llm_service.py   # Groq LLM wrapper
│   │   └── __init__.py
│   ├── requirements.txt     # Python dependencies
│   └── runtime.txt          # Python 3.11.9 for Render
├── frontend/               # React web app
│   ├── src/
│   │   ├── App.js          # Main chat component
│   │   ├── App.css         # Chat styles
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   └── package.json
├── .env.example            # Environment template
└── README.md
```

## ⚙️ Environment Variables

Create `.env` from `.env.example`:

```env
# Backend (Required for AI responses)
GROQ_API_KEY=your_groq_api_key_here

# Optional Backend Settings
PORT=8000
FRONTEND_ORIGIN=*

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
```

### Getting Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up for free account
3. Create new API key
4. Copy key to your `.env` file

## 🔧 API Endpoints

### Backend API
- `POST /api/chat` - Send chat message, get AI response
- `GET /api/health` - Health check endpoint
- `GET /` - API information

### Example Usage
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, how are you?"}'
```

## 🎨 Features

- ✅ **Clean React UI** - Modern, responsive chat interface
- ✅ **Groq LLM Integration** - Fast AI responses with Llama models
- ✅ **Session Management** - Maintains conversation context
- ✅ **Error Handling** - Graceful fallbacks and user-friendly errors
- ✅ **Production Ready** - Works on Render, Vercel, Netlify
- ✅ **Simple Architecture** - No Kafka, no complex microservices

## 🚀 Deployment

### Render (Recommended)

#### Backend Deployment
1. **Connect GitHub repo** to Render
2. **Set Environment Variables:**
   - `GROQ_API_KEY` - Your Groq API key
   - `PORT` - Render sets this automatically
3. **Configure Service:**
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

#### Frontend Deployment
1. **Connect same repo** to Vercel/Netlify
2. **Set Environment Variable:**
   - `REACT_APP_API_URL` - Your Render backend URL
3. **Configure Build:**
   - Root Directory: `frontend`
   - Build: `npm install && npm run build`
   - Publish: `build`

### Environment Variables for Production

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Your Groq API key |
| `REACT_APP_API_URL` | ✅ | Backend URL for frontend |
| `FRONTEND_ORIGIN` | ❌ | Allowed CORS origin (default: "*") |
| `PORT` | ❌ | Backend port (Render sets automatically) |

## 🛠️ Development

### Running Locally

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

### Testing

#### Backend Health Check
```bash
curl http://localhost:8000/api/health
```

#### Frontend Build
```bash
cd frontend
npm run build
```

## 🔍 Troubleshooting

### Common Issues

**1. "GROQ_API_KEY not set"**
```bash
# Make sure .env file exists with your API key
cat .env
```

**2. "ModuleNotFoundError"**
- ✅ **Fixed!** - Backend uses proper package structure

**3. "Port already in use"**
```bash
# Kill existing processes
lsof -ti:8000 | xargs kill -9
```

**4. "npm: command not found"**
- Install Node.js from https://nodejs.org/

**5. "python: command not found"**
- Install Python 3.11 from https://python.org/

**6. Frontend build fails**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Getting Help

- Check backend logs: `uvicorn app.main:app --log-level debug`
- Check browser console for frontend errors
- Verify all environment variables are set
- Make sure Groq API key is valid

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Need help?** Check the issues tab or create a new issue.

**Made with ❤️ for beginners and production deployment**
