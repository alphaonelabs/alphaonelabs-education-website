import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_ai_settings():
    """Get AI settings from Django settings."""
    return {
        'provider': getattr(settings, 'AI_PROVIDER', 'demo'),
        'temperature': getattr(settings, 'AI_TEMPERATURE', 0.7),
        'max_tokens': getattr(settings, 'AI_MAX_TOKENS', 1024),
        'gemini': {
            'api_key': getattr(settings, 'GEMINI_API_KEY', None),
            'model': getattr(settings, 'GEMINI_MODEL', 'gemini-pro'),
        },
        'openai': {
            'api_key': getattr(settings, 'OPENAI_API_KEY', None),
            'model': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
        }
    }

def is_ai_configured():
    """Check if any AI provider is properly configured."""
    ai_settings = get_ai_settings()
    
    if ai_settings['provider'] == 'gemini' and ai_settings['gemini']['api_key']:
        return True
    elif ai_settings['provider'] == 'openai' and ai_settings['openai']['api_key']:
        return True
    
    return False

def log_ai_configuration():
    """Log AI configuration status without exposing sensitive data."""
    ai_settings = get_ai_settings()
    
    if is_ai_configured():
        provider = ai_settings['provider']
        model = ai_settings[provider]['model']
        logger.info(f"AI configured with {provider} provider using {model} model")
    else:
        logger.warning("No AI provider configured, using demo mode")

# Export the API keys configuration status
API_KEYS_CONFIGURED = is_ai_configured()
