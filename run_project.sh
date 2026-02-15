#!/bin/bash

# Script to run the chatbot project

echo "Starting the Simple AI Chatbot project..."

# Function to start backend
start_backend() {
    echo "Starting backend server..."
    cd backend
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
    echo "Backend server starting on http://localhost:8000"
    uvicorn app.main:app --reload
}

# Function to start frontend
start_frontend() {
    echo "Starting frontend server..."
    cd frontend
    npm install
    echo "Frontend server starting on http://localhost:3000"
    npm start
}

# Check command line argument
case "$1" in
    "backend")
        start_backend
        ;;
    "frontend")
        start_frontend
        ;;
    *)
        echo "Usage: $0 {backend|frontend}"
        echo "  backend  - Start only the backend server"
        echo "  frontend - Start only the frontend server"
        echo "  both     - Start both servers (run in separate terminals)"
        exit 1
        ;;
esac