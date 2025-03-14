import os
import google.generativeai as genai
import openai
from typing import Dict, Any, Optional
import logging

class AIService:
    """Service for interacting with AI providers (Gemini and OpenAI)."""
    
    def __init__(self):
        # Try to initialize Gemini
        try:
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            else:
                self.gemini_model = None
                logging.warning("Gemini API key not found.")
        except Exception as e:
            self.gemini_model = None
            logging.error(f"Error initializing Gemini: {e}")
        
        # Try to initialize OpenAI
        try:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            if not openai.api_key:
                logging.warning("OpenAI API key not found.")
        except Exception as e:
            logging.error(f"Error initializing OpenAI: {e}")
    
    def get_response(self, user, message: str, subject: str = 'general',
                    provider: str = 'auto') -> Dict[str, Any]:
        """Get response from AI provider."""
        # Record the interaction start
        from .models import Interaction
        import time
        
        start_time = time.time()
        
        # Choose provider
        if provider == 'auto':
            # Try Gemini first, fall back to OpenAI
            if self.gemini_model:
                provider = 'gemini'
            else:
                provider = 'openai'
        
        # Get response from selected provider
        if provider == 'gemini' and self.gemini_model:
            response_text = self._get_gemini_response(message)
        else:
            response_text = self._get_openai_response(message)
        
        # Calculate duration
        duration = int((time.time() - start_time) * 1000)  # milliseconds
        
        # Save interaction
        interaction = Interaction.objects.create(
            user=user,
            question=message,
            answer=response_text,
            subject=subject,
            ai_provider=provider,
            duration=duration
        )
        
        return {
            'text': response_text,
            'provider': provider,
            'interaction_id': interaction.id
        }
    
    def _get_gemini_response(self, message: str) -> str:
        """Get response from Gemini."""
        try:
            response = self.gemini_model.generate_content(message)
            return response.text
        except Exception as e:
            logging.error(f"Gemini error: {e}")
            return f"I'm sorry, I encountered an error: {e}"
    
    def _get_openai_response(self, message: str) -> str:
        """Get response from OpenAI."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful educational assistant."},
                    {"role": "user", "content": message}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI error: {e}")
            return f"I'm sorry, I encountered an error: {e}"