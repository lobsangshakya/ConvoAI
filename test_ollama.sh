#!/bin/bash

echo "Testing Ollama Integration with ConvoAI"

# Check if Ollama is running
echo "Checking if Ollama is running on http://127.0.0.1:11434..."
if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is running"
else
    echo "✗ Ollama is not running. Please start Ollama with 'ollama serve'"
    echo "To install and run Ollama:"
    echo "  1. Install: https://ollama.ai"
    echo "  2. Pull model: ollama pull qwen2.5:3b"
    echo "  3. Start: ollama serve"
    exit 1
fi

# List available models
echo -e "\nAvailable Ollama models:"
curl -s http://127.0.0.1:11434/api/tags | jq -r '.models[].name' 2>/dev/null || echo "No models found (install a model with 'ollama pull <model_name>')"

# Test the ConvoAI backend health check
echo -e "\nTesting ConvoAI backend health check..."
if curl -s http://localhost:8000/api/health/ollama > /dev/null 2>&1; then
    echo "✓ ConvoAI backend is running and can reach Ollama"
    curl -s http://localhost:8000/api/health/ollama | jq '.' 2>/dev/null
else
    echo "✗ ConvoAI backend is not running or cannot reach Ollama"
    echo "Make sure to start the backend with: python -m uvicorn app.main:app --reload"
fi

echo -e "\nTo run the complete system:"
echo "1. Start Ollama: ollama serve"
echo "2. Pull the model: ollama pull qwen2.5:3b"
echo "3. Start backend: cd backend && python -m uvicorn app.main:app --reload"
echo "4. Start frontend: cd frontend && npm start"