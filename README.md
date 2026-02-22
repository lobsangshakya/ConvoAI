# ConvoAI

AI chatbot with React frontend and FastAPI backend powered by Groq LLM.

## Quick Start

1. Clone repository
2. Copy `.env.example` to `.env` and add your Groq API key
3. Start backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
4. Start frontend: `cd frontend && npm install && npm start`
5. Open http://localhost:3000

## Project Structure

```
ConvoAI/
├── backend/                 # FastAPI server
│   ├── app/
│   │   ├── main.py          # API endpoints
│   │   ├── llm_service.py   # Groq LLM wrapper
│   │   └── __init__.py
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/               # React app
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── public/
│   └── package.json
└── .env.example
```

## Environment Variables

Create `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
PORT=8000
FRONTEND_ORIGIN=*
REACT_APP_API_URL=http://localhost:8000
```

Get API key from https://console.groq.com/

## API Endpoints

- `POST /api/chat` - Send message, get AI response
- `GET /api/health` - Health check
- `GET /` - API info

Example:
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
```

## Deployment

### Backend (Render)

- Root Directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment Variables: `GROQ_API_KEY`

### Frontend (Vercel/Netlify)

- Root Directory: `frontend`
- Build: `npm install && npm run build`
- Publish: `build`
- Environment Variables: `REACT_APP_API_URL` (your backend URL)

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

- "GROQ_API_KEY not set": Add API key to `.env`
- "Port already in use": `lsof -ti:8000 | xargs kill -9`
- Build fails: `rm -rf node_modules package-lock.json && npm install`

## License

MIT
