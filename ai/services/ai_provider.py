import logging
import random
import time

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
                logger.info(f"Gemini model {GEMINI_MODEL} initialized successfully")
            except ImportError:
                logger.error("Failed to import google.generativeai module. Make sure the package is installed.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {str(e)}")
    
    # Define which exceptions should trigger a retry
    def _should_retry_exception(exception):
        # Retry on connection errors, timeouts, and specific API errors
        import google.api_core.exceptions as google_exceptions
        
        if TENACITY_AVAILABLE:
            retry_exceptions = (
                ConnectionError, 
                TimeoutError,
                google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded
            )
            return isinstance(exception, retry_exceptions)
        return False
    
    # Enhance retry decorator with exception filtering if tenacity is available
    retry_decorator = (
        retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=10),
            retry=retry_if_exception_type((ConnectionError, TimeoutError))
        ) if TENACITY_AVAILABLE else 
        retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    )
    
    @retry_decorator
    def generate_response(self, prompt, context):
        """Generate a response using Gemini API."""
        if not self.is_available():
            logger.warning("Gemini API is not available, using demo mode instead.")
            return "Gemini API is not configured properly. Using demo mode instead."
        
        try:
            logger.info(f"Generating Gemini response for prompt: {prompt[:50]}...")
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
            
            # Check if we received a valid response
            if not hasattr(response, 'text') or not response.text:
                logger.warning("Empty or invalid response from Gemini")
                return "I'm sorry, I couldn't generate a proper response. Please try rephrasing your question."
            
            logger.info("Gemini response generated successfully")
            return response.text
            
        except ImportError as e:
            logger.error(f"Missing dependency for Gemini: {str(e)}")
            return "I couldn't access the AI service due to a configuration issue. Please contact support."
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            
            # Check if this is the last retry attempt
            retry_state = getattr(self.generate_response, 'retry_state', None)
            is_last_attempt = retry_state and retry_state.attempt_number >= retry_state.retry_object.stop.max_attempt_number if TENACITY_AVAILABLE else True
            
            if is_last_attempt:
                # After all retries fail, fall back to the demo provider
                try:
                    logger.info("All retries failed, falling back to DemoProvider")
                    demo_provider = DemoProvider()
                    return demo_provider.generate_response(prompt, context)
                except Exception as fallback_error:
                    logger.error(f"Even fallback to DemoProvider failed: {str(fallback_error)}")
            
            # For retries that aren't the last attempt, raise the exception to trigger retry
            raise
    
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
        
        return response
    
    def is_available(self):
        """Demo provider is always available."""
        return True

def get_ai_provider():
    """Get the appropriate AI provider based on configuration."""
    # Check if Gemini API key is configured
    if GEMINI_API_KEY:
        provider = GeminiProvider()
        logger.info(f"Checking Gemini provider availability: {provider.is_available()}")
        if provider.is_available():
            logger.info("Using Gemini provider")
            return provider
        else:
            logger.warning("Gemini provider not available despite API key being set")
    else:
        logger.warning("Gemini API key not configured")
    
    # Fall back to demo provider
    logger.info("Using Demo provider as fallback")
    return DemoProvider()
