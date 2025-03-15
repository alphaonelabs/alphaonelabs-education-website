import logging
import random
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import (
    GEMINI_API_KEY, 
    GEMINI_MODEL, 
    AI_TEMPERATURE,
    API_KEYS_CONFIGURED
)

logger = logging.getLogger(__name__)

class AIProvider:
    """Base class for AI provider implementations."""
    
    def generate_response(self, prompt, context):
        """Generate a response from the AI model."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def is_available(self):
        """Check if this provider is available."""
        return False
    
    def _format_prompt(self, prompt, context):
        """Format the prompt with context for educational assistant."""
        subject = context.get('subject', 'general')
        profile = context.get('profile', {})
        
        learning_style = profile.get('learning_style', 'visual')
        difficulty = profile.get('difficulty_preference', 'moderate')
        response_length = profile.get('response_length', 'detailed')
        
        system_prompt = f"""You are an educational AI assistant helping a student learn about {subject}. 

Your goal is to provide accurate, helpful information that enhances their understanding.

Learning preferences:
- Learning style: {learning_style}
- Difficulty level: {difficulty}
- Response detail: {response_length}

Guidelines:
1. Be accurate and educational in your response
2. Adapt to the student's learning preferences
3. Match the difficulty level to their preference
4. If the student appears confused, simplify your explanation
5. If the question is unclear, ask for clarification
6. End with a thoughtful follow-up question to deepen understanding

Student question: {prompt}
"""
        return system_prompt

class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""
    
    def __init__(self):
        self.model = None
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel(GEMINI_MODEL)
                logger.info(f"Gemini model {GEMINI_MODEL} initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    def generate_response(self, prompt, context):
        """Generate a response using Gemini API."""
        if not self.is_available():
            return "Gemini API is not configured properly. Using demo mode instead."
        
        try:
            formatted_prompt = self._format_prompt(prompt, context)
            
            generation_config = {
                "temperature": AI_TEMPERATURE,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            response = self.model.generate_content(
                formatted_prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            return f"I encountered an error processing your request. Please try again or ask a different question."
    
    def is_available(self):
        """Check if Gemini API is available."""
        return self.model is not None

class DemoProvider(AIProvider):
    """Demo AI provider for development and testing."""
    
    def generate_response(self, prompt, context):
        """Generate a demo response based on the subject."""
        subject = context.get('subject', 'general')
        
        responses = {
            'mathematics': [
                "That's an interesting math question! In mathematics, we approach this by identifying the key principles involved. Let's break this down step by step...",
                "This mathematical concept connects to several important areas. First, let me explain the fundamental theory...",
                "To solve this mathematics problem, we need to apply these key formulas and techniques..."
            ],
            'science': [
                "From a scientific perspective, this phenomenon can be explained by several key principles. Let's explore how they work...",
                "In science, we observe this effect due to the interaction between multiple factors. The most significant are...",
                "The scientific explanation for this involves understanding the underlying mechanisms..."
            ],
            'programming': [
                "When implementing this in code, you'll want to consider these best practices and algorithms...",
                "This programming challenge can be approached using several design patterns. The most efficient solution would be...",
                "To code this functionality, we should follow these steps and consider these edge cases..."
            ],
            'history': [
                "This historical period was shaped by several important events and social movements...",
                "Looking at this through a historical lens, we can identify these key influences and consequences...",
                "The historical context is essential to understand this event. Let me explain the background and significance..."
            ],
            'languages': [
                "This linguistic concept appears in many languages with interesting variations across cultures...",
                "When learning this language feature, it helps to compare it with concepts from your native language...",
                "This expression has both literal and cultural meanings. Let me explain how to use it correctly..."
            ]
        }
        
        # Select a response based on subject
        subject_responses = responses.get(subject, [
            "That's a great question about " + subject + "! Here's what you need to know...",
            "I'd be happy to help you understand this " + subject + " topic better. Let's explore the key concepts...",
            "Learning about " + subject + " involves understanding these fundamental principles..."
        ])
        
        response = random.choice(subject_responses)
        
        # Add demo ending
        response += "\n\n(Note: I'm currently in demonstration mode. The full AI functionality will be available soon!)"
        
        return response
    
    def is_available(self):
        """Demo provider is always available."""
        return True

def get_ai_provider():
    """Get the appropriate AI provider based on configuration."""
    if API_KEYS_CONFIGURED:
        provider = GeminiProvider()
        if provider.is_available():
            return provider
    
    # Fall back to demo provider
    return DemoProvider()
