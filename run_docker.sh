#!/bin/bash

# Script to build and run the ChatBot project with Docker

echo "Building and running ChatBot project..."

# Build and start all services
docker-compose -f docker-compose.yml up --build

echo "ChatBot project is running!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "Press Ctrl+C to stop the services"