import os
import signal
import sys
import time
from typing import Optional, Dict, Any
from django.conf import settings
import google.generativeai as genai
from openai import OpenAI
import requests
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

class AIService:
    def __init__(self):
        self.openai_client = None
        self.gemini_api_key = None
        self._current_request = None
        self._request_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._initialize_services()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption."""
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Cleaning up...")
            with self._request_lock:
                if self._current_request:
                    print("Cancelling current request...")
                    self._current_request = None
                print("AI service cleanup complete")
            
            # Only raise KeyboardInterrupt if we're in the main thread
            if threading.current_thread() is threading.main_thread():
                raise KeyboardInterrupt("AI service interrupted by user")
            else:
                print("Interrupt received in non-main thread, continuing...")

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _initialize_services(self):
        """Initialize AI services with better error handling and logging."""
        try:
            # Initialize OpenAI if API key is available
            if settings.USE_OPENAI:
                if not settings.OPENAI_API_KEY:
                    print("Warning: USE_OPENAI is True but OPENAI_API_KEY is not set")
                else:
                    try:
                        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                        print("OpenAI client initialized successfully")
                    except Exception as e:
                        print(f"Error initializing OpenAI client: {str(e)}")

            # Initialize Gemini if API key is available
            if settings.USE_GEMINI:
                if not settings.GEMINI_API_KEY:
                    print("Warning: USE_GEMINI is True but GEMINI_API_KEY is not set")
                else:
                    try:
                        self.gemini_api_key = settings.GEMINI_API_KEY
                        genai.configure(api_key=self.gemini_api_key)
                        print("Gemini client initialized successfully")
                    except Exception as e:
                        print(f"Error initializing Gemini client: {str(e)}")

            # Log final state
            print(f"AI Service State:")
            print(f"- OpenAI enabled: {settings.USE_OPENAI}")
            print(f"- OpenAI client initialized: {self.openai_client is not None}")
            print(f"- Gemini enabled: {settings.USE_GEMINI}")
            print(f"- Gemini API key set: {bool(self.gemini_api_key)}")
            print(f"- Default service: {settings.DEFAULT_AI_SERVICE}")

        except Exception as e:
            print(f"Error in _initialize_services: {str(e)}")
            raise

    def _format_code_block(self, code: str, language: str = "python") -> str:
        """Format code blocks with syntax highlighting."""
        try:
            lexer = get_lexer_by_name(language)
            formatter = HtmlFormatter(style='monokai', linenos=True)
            highlighted = highlight(code, lexer, formatter)
            return f'<div class="code-block">{highlighted}</div>'
        except:
            return f'<pre><code class="language-{language}">{code}</code></pre>'

    def _format_math_expression(self, expression: str) -> str:
        """Format mathematical expressions using MathJax delimiters."""
        # Handle inline math
        expression = re.sub(r'\$(.+?)\$', r'\\[\1\\]', expression)
        # Handle display math
        expression = re.sub(r'\$\$(.+?)\$\$', r'\\[\1\\]', expression)
        return expression

    def _process_markdown(self, text: str) -> str:
        """Process markdown text with enhanced formatting."""
        # Convert markdown to HTML
        html = markdown.markdown(text, extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.attr_list',
            'markdown.extensions.def_list',
            'markdown.extensions.footnotes'
        ])
        
        # Add custom CSS classes for better styling
        html = html.replace('<code>', '<code class="inline-code">')
        html = html.replace('<pre>', '<pre class="code-block">')
        
        return html

    def get_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Get AI response using Gemini Flash 2.0 with OpenAI fallback."""
        try:
            with self._request_lock:
                self._current_request = prompt

            # Set timeout for the entire request
            timeout = 30  # 30 seconds timeout
            start_time = time.time()

            print(f"\nProcessing request with prompt: {prompt[:50]}...")
            print(f"Using context: {context}")

            # Try the default service first
            if settings.DEFAULT_AI_SERVICE == 'gemini' and settings.USE_GEMINI and self.gemini_api_key:
                try:
                    print("Attempting Gemini request...")
                    future = self._executor.submit(self._get_gemini_response, prompt, context)
                    response = future.result(timeout=timeout)
                    if response:
                        print("Gemini request successful")
                        return self._process_markdown(response)
                    else:
                        print("Gemini request returned empty response")
                        raise Exception("Gemini service returned an empty response")
                except TimeoutError:
                    print("Gemini request timed out")
                    raise Exception("Gemini service request timed out after 30 seconds")
                except Exception as e:
                    print(f"Gemini request failed: {str(e)}")
                    raise Exception(f"Gemini service error: {str(e)}")
            
            # If default service fails or is not configured, try OpenAI
            if settings.USE_OPENAI and self.openai_client:
                try:
                    print("Attempting OpenAI request...")
                    future = self._executor.submit(self._get_openai_response, prompt, context)
                    response = future.result(timeout=timeout)
                    if response:
                        print("OpenAI request successful")
                        return self._process_markdown(response)
                    else:
                        print("OpenAI request returned empty response")
                        raise Exception("OpenAI service returned an empty response")
                except TimeoutError:
                    print("OpenAI request timed out")
                    raise Exception("OpenAI service request timed out after 30 seconds")
                except Exception as e:
                    print(f"OpenAI request failed: {str(e)}")
                    raise Exception(f"OpenAI service error: {str(e)}")
            
            # If OpenAI fails, try Gemini again as last resort
            if settings.USE_GEMINI and self.gemini_api_key:
                try:
                    print("Attempting Gemini fallback request...")
                    future = self._executor.submit(self._get_gemini_response, prompt, context)
                    response = future.result(timeout=timeout)
                    if response:
                        print("Gemini fallback request successful")
                        return self._process_markdown(response)
                    else:
                        print("Gemini fallback request returned empty response")
                        raise Exception("Gemini fallback service returned an empty response")
                except TimeoutError:
                    print("Gemini fallback request timed out")
                    raise Exception("Gemini fallback service request timed out after 30 seconds")
                except Exception as e:
                    print(f"Gemini fallback request failed: {str(e)}")
                    raise Exception(f"Gemini fallback service error: {str(e)}")
            
            error_msg = "All AI services are currently unavailable. Please try again later."
            print(f"All AI services failed. Returning error message: {error_msg}")
            raise Exception(error_msg)
            
        except KeyboardInterrupt:
            print("\nAI service interrupted by user")
            raise Exception("Request was interrupted. Please try again.")
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            raise Exception(f"AI service error: {str(e)}")
        finally:
            with self._request_lock:
                self._current_request = None

    def _get_gemini_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get response from Gemini Flash 2.0."""
        try:
            # Configure the model
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Prepare the prompt with context if provided
            full_prompt = prompt
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_prompt = f"Context:\n{context_str}\n\nQuestion:\n{prompt}"
            
            # Generate response
            response = model.generate_content(full_prompt)
            
            # Process and return the response
            if response and response.text:
                return response.text
            return None
            
        except KeyboardInterrupt:
            print("\nGemini API request interrupted")
            return None
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return None

    def _get_openai_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get response from OpenAI as fallback."""
        try:
            # Prepare the prompt with context if provided
            full_prompt = prompt
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_prompt = f"Context:\n{context_str}\n\nQuestion:\n{prompt}"
            
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Process and return the response
            if response and response.choices:
                return response.choices[0].message.content
            return None
            
        except KeyboardInterrupt:
            print("\nOpenAI API request interrupted")
            return None
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return None

# Create a singleton instance
ai_service = AIService() 