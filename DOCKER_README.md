# Docker Deployment Guide

This guide explains how to build and run the AI-Powered Chatbot using Docker.

## Prerequisites

- Docker Engine (v20.10 or higher)
- Docker Compose (v2.0 or higher)

## Build and Run

### Development Mode (with live reloading)

```bash
docker-compose up --build
```

### Production Mode

```bash
docker-compose -f docker-compose.prod.yml up --build
```

## Services

The application consists of the following services:

- **Frontend**: React-based chat interface (port 3000)
- **Backend**: FastAPI server (port 8000)
- **LLM Service**: Language model service
- **RL Agent**: Reinforcement learning agent
- **Kafka**: Message broker
- **Zookeeper**: Kafka dependency
- **PostgreSQL**: Database

## Environment Variables

You can customize the following environment variables:

### For LLM Service:
- `USE_OPENAI`: Set to `true` to use OpenAI API
- `OPENAI_API_KEY`: Your OpenAI API key
- `HF_MODEL`: Hugging Face model to use (default: `gpt2`)

### For Database:
- `POSTGRES_DB`: Database name (default: `chatbot_db`)
- `POSTGRES_USER`: Database user (default: `user`)
- `POSTGRES_PASSWORD`: Database password (default: `password`)

## Useful Commands

### Build all services without running:
```bash
docker-compose build
```

### Run in detached mode:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f
```

### Stop all services:
```bash
docker-compose down
```

### Stop and remove volumes:
```bash
docker-compose down -v
```

## Troubleshooting

1. **Port already in use**: Make sure ports 3000 and 8000 are available
2. **Kafka connection issues**: Wait for Kafka to fully start before other services
3. **Database connection issues**: Check that PostgreSQL is running and accessible

## Production Deployment Notes

- The production configuration removes volume mounts for better performance
- Uses proper networking between services
- Sets LOCAL_MODE=false for full functionality
- Uses Nginx to serve the frontend in production