import os
import openai
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ModelHandler:
    def __init__(self):
        # Initialize the model - using a lightweight model for demo purposes
        self.use_openai = os.getenv('USE_OPENAI', 'false').lower() == 'true'
        
        if self.use_openai:
            # Using OpenAI API
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.model_name = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        else:
            # Using Hugging Face model
            model_name = os.getenv('HF_MODEL', 'gpt2')
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForCausalLM.from_pretrained(model_name)
                # Add padding token if it doesn't exist
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
            except Exception as e:
                logger.error(f'Error loading model: {str(e)}')
                # Fallback to a simple pipeline if model loading fails
                self.generator = pipeline('text-generation', model='gpt2')

    def generate_response(self, prompt: str) -> str:
        """Generate response based on the input prompt"""
        if self.use_openai:
            return self._generate_with_openai(prompt)
        else:
            return self._generate_with_hf(prompt)
    
    def _generate_with_openai(self, prompt: str) -> str:
        """Generate response using OpenAI API"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for a chatbot application. Respond to the user's message."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            logger.error(f'Error generating response with OpenAI: {str(e)}')
            return self._fallback_response(prompt)
    
    def _generate_with_hf(self, prompt: str) -> str:
        """Generate response using Hugging Face model"""
        try:
            # Prepare the input
            input_text = f"User: {prompt}\nAssistant:"
            inputs = self.tokenizer.encode(input_text, return_tensors='pt', truncation=True, max_length=512)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs, 
                    max_length=inputs.shape[1] + 100, 
                    num_return_sequences=1,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id,
                    do_sample=True
                )
            
            # Decode the response
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the assistant's part
            assistant_response = response_text[len(input_text):].strip()
            
            # If the response is empty or too similar to input, use fallback
            if not assistant_response or assistant_response == prompt:
                return self._fallback_response(prompt)
            
            return assistant_response
        except Exception as e:
            logger.error(f'Error generating response with Hugging Face model: {str(e)}')
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Fallback response if model generation fails"""
        # Simple fallback responses based on keywords in the prompt
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! How can I assist you today?"
        elif any(word in prompt_lower for word in ['thank', 'thanks']):
            return "You're welcome! Is there anything else I can help with?"
        elif any(word in prompt_lower for word in ['help', 'assist']):
            return "I'd be happy to help. What do you need assistance with?"
        elif '?' in prompt:
            return "That's an interesting question. Could you tell me more about what you're looking for?"
        else:
            return "I understand. Could you provide more details so I can better assist you?"