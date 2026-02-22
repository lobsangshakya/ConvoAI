"""
Groq LLM Service - OpenAI-compatible wrapper for Groq API
"""

import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class GroqService:
    """Groq LLM service using OpenAI-compatible API"""
    
    def __init__(self):
        self.client = None
        self.available = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq client"""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("GROQ_API_KEY not set - Groq service unavailable")
                return
            
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            self.available = True
            logger.info("Groq client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self.available = False
    
    def is_available(self) -> bool:
        """Check if Groq service is available"""
        return self.available and self.client is not None
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "llama-3.1-8b-instant",
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> str:
        """Generate response using Groq API"""
        
        if not self.is_available():
            return self._get_fallback_response()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._get_error_response(str(e))
    
    def _get_fallback_response(self) -> str:
        """Return fallback response when service is unavailable"""
        return (
            "🤖 ConvoAI is not configured properly. "
            "Please set the GROQ_API_KEY environment variable to enable AI responses. "
            "You can get a free API key from https://console.groq.com/"
        )
    
    def _get_error_response(self, error: str) -> str:
        """Return error response"""
        return f"Sorry, I encountered an error: {error}. Please try again later."
    
    def get_default_model(self) -> str:
        """Get default Groq model"""
        return "llama-3.1-8b-instant"
    
    def get_available_models(self) -> List[str]:
        """Get list of available Groq models"""
        return [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile", 
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ]
