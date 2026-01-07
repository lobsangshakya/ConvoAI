#!/bin/bash

# Script to run the ConvoAI chatbot with OpenAI API key
# Usage: ./run_with_env.sh [your_openai_api_key]

if [ -z "$1" ]; then
    echo "Usage: ./run_with_env.sh [your_openai_api_key]"
    echo "Or set the OPENAI_API_KEY environment variable before running this script"
    echo ""
    echo "Example: ./run_with_env.sh sk-1234567890abcdef"
    exit 1
fi

export OPENAI_API_KEY=$1

echo "Starting ConvoAI chatbot with OpenAI integration..."
echo "OpenAI model configured: gpt-3.5-turbo"
echo "Make sure Docker and Docker Compose are installed and running."
echo ""

# Start all services with Docker Compose
docker-compose up --build