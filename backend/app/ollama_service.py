"""
Ollama Service - Local LLM integration
"""

import os
import logging
import httpx
from typing import List, Dict, Optional, AsyncGenerator

logger = logging.getLogger(__name__)

class OllamaService:
    """Ollama LLM service for local inference"""
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is available"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.available = True
                logger.info(f"Ollama available at {self.base_url}")
            else:
                self.available = False
                logger.warning(f"Ollama returned status {response.status_code}")
        except Exception as e:
            self.available = False
            logger.warning(f"Ollama not available: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        return self.available
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> str:
        """Generate response using Ollama"""
        
        if not self.is_available():
            return self._get_fallback_response()
        
        try:
            model = model or self.default_model
            
            # Check if user wants points format
            user_message = messages[-1].get("content", "").lower() if messages else ""
            wants_points = any(keyword in user_message for keyword in ["points", "in points", "bullet points", "point form"])
            
            # Convert messages to Ollama format
            ollama_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    ollama_messages.append({"role": "system", "content": content})
                elif role == "user":
                    ollama_messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    ollama_messages.append({"role": "assistant", "content": content})
            
            # Modify system prompt if user wants points
            if wants_points:
                system_prompt = "You are ConvoAI, a helpful assistant. When the user asks for information 'in points', 'bullet points', or 'point form', format your response as a numbered list with clear, concise points. Each point should start with a number and a brief description."
                
                # Update or add system message
                if ollama_messages and ollama_messages[0].get("role") == "system":
                    ollama_messages[0]["content"] = system_prompt
                else:
                    ollama_messages.insert(0, {"role": "system", "content": system_prompt})
            
            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get("message", {}).get("content", "").strip()
                    
                    # Post-process to ensure points format if requested
                    if wants_points and not any(raw_response.strip().startswith(str(i)) for i in range(1, 10)):
                        # Convert to points if not already in point format
                        return self._convert_to_points(raw_response)
                    
                    return raw_response
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    return self._get_error_response(f"HTTP {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error("Ollama request timeout")
            return self._get_error_response("Request timeout")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return self._get_error_response(str(e))
    
    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using Ollama"""
        
        if not self.is_available():
            yield self._get_fallback_response()
            return
        
        try:
            model = model or self.default_model
            
            # Check if user wants points format
            user_message = messages[-1].get("content", "").lower() if messages else ""
            wants_points = any(keyword in user_message for keyword in ["points", "in points", "bullet points", "point form"])
            
            # Convert messages to Ollama format
            ollama_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    ollama_messages.append({"role": "system", "content": content})
                elif role == "user":
                    ollama_messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    ollama_messages.append({"role": "assistant", "content": content})
            
            # Modify system prompt if user wants points
            if wants_points:
                system_prompt = "You are ConvoAI, a helpful assistant. When the user asks for information 'in points', 'bullet points', or 'point form', format your response as a numbered list with clear, concise points. Each point should start with a number and a brief description."
                
                # Update or add system message
                if ollama_messages and ollama_messages[0].get("role") == "system":
                    ollama_messages[0]["content"] = system_prompt
                else:
                    ollama_messages.insert(0, {"role": "system", "content": system_prompt})
            
            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            full_response = ""
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", 
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    data = line.decode('utf-8') if isinstance(line, bytes) else line
                                    if data.startswith("data: "):
                                        data = data[6:]  # Remove "data: " prefix
                                        if data.strip() and data != "[DONE]":
                                            import json
                                            chunk = json.loads(data)
                                            if "message" in chunk and "content" in chunk["message"]:
                                                content = chunk["message"]["content"]
                                                full_response += content
                                                yield content
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.error(f"Stream parsing error: {e}")
                                    continue
                    else:
                        logger.error(f"Ollama streaming error: {response.status_code}")
                        yield self._get_error_response(f"HTTP {response.status_code}")
                        return
            
            # Post-process for points if needed (streaming doesn't support this well)
            # For streaming, we rely on the system prompt to guide the model
                        
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield self._get_error_response(str(e))
    
    def _get_fallback_response(self) -> str:
        """Return fallback response when Ollama is unavailable"""
        return (
            "🤖 ConvoAI is not available. "
            "Please make sure Ollama is running on http://localhost:11434 "
            "and that model 'qwen2.5:3b' is pulled. "
            "Run: ollama pull qwen2.5:3b"
        )
    
    def _get_error_response(self, error: str) -> str:
        """Return error response"""
        return f"Sorry, I encountered an error: {error}. Please try again."
    
    def _convert_to_points(self, text: str) -> str:
        """Convert text to numbered points format"""
        # Split by sentences or common delimiters
        sentences = [s.strip() for s in text.replace('\n', '. ').split('. ') if s.strip()]
        
        # Filter out very short sentences
        sentences = [s for s in sentences if len(s) > 10]
        
        # Convert to numbered points
        points = []
        for i, sentence in enumerate(sentences[:8], 1):  # Limit to 8 points
            # Remove leading conjunctions and articles
            cleaned = sentence
            if cleaned.lower().startswith(('and ', 'but ', 'so ', 'also ', 'the ', 'a ', 'an ')):
                cleaned = cleaned.split(' ', 1)[1] if ' ' in cleaned else cleaned
            
            # Capitalize first letter
            cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
            
            points.append(f"{i}. {cleaned}")
        
        return '\n'.join(points) if points else text
    
    def get_default_model(self) -> str:
        """Get default Ollama model"""
        return self.default_model
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        return [
            "qwen2.5:3b",
            "qwen:7b",
            "llama3:8b",
            "llama3:70b",
            "mixtral:8x7b"
        ]
