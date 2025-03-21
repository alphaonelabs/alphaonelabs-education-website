import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_file = Path(__file__).resolve().parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# Gemini AI Settings
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')  # Correct format: gemini-2.0-flash (not gemini-flash-2.0)

# OpenAI Settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')

# Temperature for AI responses (0.0 = deterministic, 1.0 = creative)
AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', '0.7'))

# Model configuration
AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', 1000))

# Check if API keys are configured
def is_gemini_configured():
    return bool(GEMINI_API_KEY)

def is_openai_configured():
    return bool(OPENAI_API_KEY)

# Get the proper provider to use based on configuration
API_KEYS_CONFIGURED = is_gemini_configured() or is_openai_configured()

# Log configuration status (without exposing the keys)
if API_KEYS_CONFIGURED:
    logger.info("AI provider API keys are configured")
    if is_gemini_configured():
        logger.info(f"Using Gemini model: {GEMINI_MODEL}")
    if is_openai_configured():
        logger.info(f"Using OpenAI model: {OPENAI_MODEL}")
else:
    logger.warning("AI provider API keys are not configured, will use demo mode")
