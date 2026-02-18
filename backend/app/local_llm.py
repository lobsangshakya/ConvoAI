import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LocalLLM:
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        """
        Initialize local LLM with transformers.
        Default model is DialoGPT-medium which is good for conversational AI.
        Other options: facebook/blenderbot-400M-distill, gpt2, etc.
        """
        self.model_name = os.getenv("LOCAL_LLM_MODEL", model_name)
        self.tokenizer = None
        self.model = None
        self.generator = None
        self.conversation_history = {}
        
        try:
            logger.info(f"Loading local model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
            
            # Add padding token if it doesn't exist
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Create text generation pipeline
            self.generator = pipeline(
                'text-generation',
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            logger.info("Local LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize local LLM: {e}")
            raise
    
    def generate_response(self, prompt: str, session_id: str = "default", max_length: int = 200, **kwargs) -> str:
        """
        Generate response using the local LLM.
        Incorporates conversation history for context.
        """
        try:
            # Get conversation history for this session
            history = self.conversation_history.get(session_id, [])
            
            # Combine history with current prompt
            full_prompt = self._build_conversation_context(history, prompt)
            
            # Generate response
            outputs = self.generator(
                full_prompt,
                max_length=len(self.tokenizer.encode(full_prompt)) + max_length,
                num_return_sequences=1,
                temperature=kwargs.get('temperature', 0.7),
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                truncation=True
            )
            
            # Extract the new response part
            generated_text = outputs[0]['generated_text']
            response = generated_text[len(full_prompt):].strip()
            
            # Update conversation history
            self._update_conversation_history(session_id, prompt, response)
            
            # Clean up the response
            response = self._clean_response(response)
            
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error processing your request."
    
    def _build_conversation_context(self, history: list, current_input: str) -> str:
        """Build conversation context from history"""
        if not history:
            return f"User: {current_input}\nAssistant:"
        
        context = ""
        for entry in history[-3:]:  # Use last 3 exchanges for context
            context += f"User: {entry['user']}\nAssistant: {entry['assistant']}\n"
        
        context += f"User: {current_input}\nAssistant:"
        return context
    
    def _update_conversation_history(self, session_id: str, user_input: str, assistant_response: str):
        """Update conversation history for the session"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            'user': user_input,
            'assistant': assistant_response
        })
        
        # Keep only last 10 exchanges to prevent memory issues
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]
    
    def _clean_response(self, response: str) -> str:
        """Clean up the generated response"""
        # Remove any trailing text after newlines that might be part of the prompt
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if 'User:' in line or 'Assistant:' in line:
                break
            cleaned_lines.append(line.strip())
        
        result = '\n'.join(cleaned_lines).strip()
        
        # Limit response length to avoid overly long answers
        if len(result) > 300:
            # Find a good stopping point
            sentences = result.split('. ')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) < 300:
                    truncated += sentence + ". "
                else:
                    break
            result = truncated.strip()
        
        return result