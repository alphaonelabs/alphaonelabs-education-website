import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_file = Path(__file__).resolve().parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# AI Service API Keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
DEFAULT_AI_PROVIDER = os.environ.get('DEFAULT_AI_PROVIDER', 'demo')

# Model configuration
AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', 0.7))
AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', 1000))
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-pro')

# Check if API keys are configured
def is_gemini_configured():
    return bool(GEMINI_API_KEY)

# Get the proper provider to use based on configuration
API_KEYS_CONFIGURED = is_gemini_configured()
