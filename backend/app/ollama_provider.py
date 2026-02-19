import logging
import httpx
import json
from typing import Dict, Any, AsyncGenerator, List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Message], 
        model: str, 
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.max_retries = 1
    
    async def generate_response(
        self, 
        messages: List[Message], 
        model: str, 
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate response from Ollama with streaming support
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048)
            }
        }
        
        # Add any additional options
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])
        
        logger.info(f"Sending request to Ollama: {url}")
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            logger.error(f"Ollama returned status {response.status_code}: {await response.aread()}")
                            if attempt < self.max_retries:
                                continue
                            else:
                                yield f"Error: Ollama returned status {response.status_code}"
                                return
                        
                        # Process streaming response
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    
                                    # Check if this is the final response
                                    if data.get("done", False):
                                        break
                                    
                                    # Yield the content
                                    if "message" in data and "content" in data["message"]:
                                        content = data["message"]["content"]
                                        if content:
                                            yield content
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error decoding JSON from Ollama: {e}")
                                    continue
                                except Exception as e:
                                    logger.error(f"Unexpected error processing Ollama response: {e}")
                                    continue
                            
            except httpx.TimeoutException as e:
                logger.error(f"Ollama request timed out: {e}")
                if attempt < self.max_retries:
                    continue
                else:
                    yield f"Error: Request to Ollama timed out after {self.timeout}s"
                    return
            except httpx.RequestError as e:
                logger.error(f"Ollama request error: {e}")
                if attempt < self.max_retries:
                    continue
                else:
                    yield f"Error: Unable to connect to Ollama - {str(e)}"
                    return
            except Exception as e:
                logger.error(f"Unexpected error calling Ollama: {e}")
                yield f"Error: Unexpected error connecting to Ollama - {str(e)}"
                return

    async def generate_streaming_response(
        self, 
        messages: List[Message], 
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from Ollama for direct streaming to client
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048)
            }
        }
        
        # Add any additional options
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])
        
        logger.info(f"Sending streaming request to Ollama: {url}")
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            logger.error(f"Ollama returned status {response.status_code}: {await response.aread()}")
                            if attempt < self.max_retries:
                                continue
                            else:
                                yield f"data: {{\"error\": \"Ollama returned status {response.status_code}\"}}\n\n"
                                return
                        
                        # Process streaming response for SSE
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    
                                    # Check if this is the final response
                                    if data.get("done", False):
                                        # Send a special end marker
                                        yield "data: [DONE]\n\n"
                                        break
                                    
                                    # Yield the content as SSE
                                    if "message" in data and "content" in data["message"]:
                                        content = data["message"]["content"]
                                        if content:
                                            yield f"data: {{\"content\": \"{json.dumps(content)[1:-1]}\"}}\n\n"
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error decoding JSON from Ollama: {e}")
                                    continue
                                except Exception as e:
                                    logger.error(f"Unexpected error processing Ollama response: {e}")
                                    continue
                            
            except httpx.TimeoutException as e:
                logger.error(f"Ollama request timed out: {e}")
                yield f"data: {{\"error\": \"Request to Ollama timed out after {self.timeout}s\"}}\n\n"
                return
            except httpx.RequestError as e:
                logger.error(f"Ollama request error: {e}")
                yield f"data: {{\"error\": \"Unable to connect to Ollama - {str(e)}\"}}\n\n"
                return
            except Exception as e:
                logger.error(f"Unexpected error calling Ollama: {e}")
                yield f"data: {{\"error\": \"Unexpected error connecting to Ollama - {str(e)}\"}}\n\n"
                return

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Ollama is reachable
        """
        url = f"{self.base_url}/api/tags"
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return {"status": "healthy", "models": [m.get("name", "") for m in response.json().get("models", [])]}
                else:
                    return {"status": "unhealthy", "error": f"Status {response.status_code}"}
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> List[str]:
        """
        List available Ollama models
        """
        url = f"{self.base_url}/api/tags"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return [model.get("name", "") for model in data.get("models", [])]
                else:
                    return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []