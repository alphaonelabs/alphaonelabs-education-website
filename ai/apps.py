from django.apps import AppConfig
from django.conf import settings

class AIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'

    def ready(self):
        """Perform initialization when the app is ready."""
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Check AI service configuration
        if not (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY):
            logger.warning("AI service API keys not properly configured. Using demo mode.")
        else:
            logger.info("AI service API keys configured successfully.")
            if settings.GEMINI_API_KEY:
                logger.info(f"Using Gemini model: {settings.GEMINI_MODEL}")
            if settings.OPENAI_API_KEY:
                logger.info(f"Using OpenAI model: {settings.OPENAI_MODEL}")
            
        # Initialize NLTK for text processing if needed
        try:
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
        except Exception as e:
            logger.warning(f"Error initializing NLTK: {str(e)}")
