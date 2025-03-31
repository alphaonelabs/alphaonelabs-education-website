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
        # Test with a simple prompt
        response = provider.generate_response(
            "Demonstrate the capabilities of Gemini Flash 2.0 with a short response about AI education",
            {"subject": "programming"}
        )
        print("Response:", response)
        
        # Test performance
        import time
        start = time.time()
        response = provider.generate_response(
            "Explain how AI models have improved in speed over the past few years",
            {"subject": "technology"}
        )
        end = time.time()
        print(f"Response time: {end - start:.2f} seconds")
        print("Response:", response)
    else:
        print("Gemini provider is not available")
        print("Make sure your API key is set in the .env file and the gemini-flash-2.0 model is available for your API key")
