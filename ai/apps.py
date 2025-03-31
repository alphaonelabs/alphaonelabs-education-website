from django.apps import AppConfig

class AIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'

    def ready(self):
        """Perform initialization when the app is ready."""
        # Import and check AI service configuration
        from .services.config import API_KEYS_CONFIGURED
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not API_KEYS_CONFIGURED:
            logger.warning("AI service API keys not properly configured. Using demo mode.")
        else:
            logger.info("AI service API keys configured successfully.")
            
        # Initialize NLTK for text processing if needed
        try:
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
        except Exception as e:
            logger.warning(f"Error initializing NLTK: {str(e)}")
