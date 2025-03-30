import logging
import random
import time
from django.conf import settings
from .gemini_provider import GeminiProvider
from .demo_provider import DemoProvider

# Make tenacity optional
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Create dummy decorator when tenacity is not available
    def retry(*args, **kwargs):
        def decorator(func):
            # Simple retry mechanism when tenacity is not available
            def wrapper(*args, **kwargs):
                max_attempts = 2
                attempt = 0
                last_exception = None
                
                while attempt < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        attempt += 1
                        last_exception = e
                        logger.warning(f"Attempt {attempt}/{max_attempts} failed: {str(e)}")
                        if attempt < max_attempts:
                            time.sleep(1 * (2 ** (attempt - 1)))  # Simple exponential backoff
                
                # If we get here, all attempts failed
                logger.error(f"All {max_attempts} attempts failed. Last error: {str(last_exception)}")
                raise last_exception
            return wrapper
        return decorator

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
                "In science, we observe this effect due to the interaction between multiple factors. Here's what's happening...",
                "The scientific explanation for this involves understanding the underlying mechanisms. Let me explain..."
            ],
            'programming': [
                "When implementing this in code, you'll want to consider these best practices and algorithms. Here's how we can approach it...",
                "This programming challenge can be approached using several design patterns. Let's look at the most suitable one...",
                "To code this functionality, we should follow these steps and consider these edge cases. Here's the plan..."
            ],
            'history': [
                "This historical period was shaped by several important events and social movements. Let's explore the key factors...",
                "Looking at this through a historical lens, we can identify these key influences. Here's what happened...",
                "The historical context is essential to understand this event. Let me provide some background..."
            ],
            'languages': [
                "This linguistic concept appears in many languages with interesting variations. Let's explore some examples...",
                "When learning this language feature, it helps to compare it with concepts from other languages. Here's how...",
                "This expression has both literal and cultural meanings. Let me explain both aspects..."
            ]
        }
        
        # Select a response based on subject
        subject_responses = responses.get(subject, [
            "That's a great question! Here's what you need to know...",
            "I'd be happy to help you understand this topic better. Let's explore it together...",
            "Learning about this subject involves understanding these fundamental principles. Here's what you should know..."
        ])
        
        # Get response preferences
        response_format = context.get('preferences', {}).get('format', 'paragraph')
        response_length = context.get('preferences', {}).get('length', 'detailed')
        response_style = context.get('preferences', {}).get('style', 'formal')
        
        # Select a basic response
        basic_response = random.choice(subject_responses)
        
        # Adapt response based on format preference
        if response_format == 'bullets':
            points = [
                "Point 1: " + basic_response,
                "Point 2: Consider these additional aspects...",
                "Point 3: Finally, remember that..."
            ]
            return "Here's my response:\n\n* " + "\n* ".join(points)
        elif response_format == 'step-by-step':
            steps = [
                "Step 1: " + basic_response,
                "Step 2: Next, we need to consider...",
                "Step 3: Finally, we can conclude that..."
            ]
            return "Let me walk you through this:\n\n1. " + "\n2. ".join(steps)
        else:
            return basic_response
    
    def is_available(self):
        """Demo provider is always available."""
        return True

def get_ai_provider():
    """Get the appropriate AI provider based on settings."""
    if settings.AI_PROVIDER == 'gemini' and settings.GEMINI_API_KEY:
        return GeminiProvider()
    else:
        return DemoProvider()
