import os
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

class AIService:
    def __init__(self):
        self.openai_client = None
        self.gemini_api_key = None
        self._initialize_services()

    def _initialize_services(self):
        # Initialize OpenAI if API key is available
        if settings.USE_OPENAI:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Initialize Gemini if API key is available
        if settings.USE_GEMINI:
            self.gemini_api_key = settings.GEMINI_API_KEY
            genai.configure(api_key=self.gemini_api_key)

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
            # Try Gemini Flash 2.0 first
            if settings.USE_GEMINI and self.gemini_api_key:
                response = self._get_gemini_response(prompt, context)
                if response:
                    return self._process_markdown(response)
            
            # Fallback to OpenAI if Gemini fails or is not configured
            if settings.USE_OPENAI and self.openai_client:
                response = self._get_openai_response(prompt, context)
                if response:
                    return self._process_markdown(response)
            
            return "I apologize, but I'm unable to process your request at the moment. Please try again later."
            
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again later."

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
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return None

# Create a singleton instance
ai_service = AIService() 