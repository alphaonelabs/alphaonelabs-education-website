import os
import sys

# Add project root to path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Gemini provider
from ai.services.config import GEMINI_API_KEY, GEMINI_MODEL
from ai.services.ai_provider import GeminiProvider

if __name__ == "__main__":
    print(f"Testing Gemini API with key: {'configured' if GEMINI_API_KEY else 'not configured'}")
    print(f"Using model: {GEMINI_MODEL}")

    provider = GeminiProvider()
    print(f"Provider available: {provider.is_available()}")
    
    if provider.is_available():
        response = provider.generate_response(
            "Tell me a short joke about programming",
            {"subject": "programming"}
        )
        print("Response:", response)
    else:
        print("Gemini provider is not available")
