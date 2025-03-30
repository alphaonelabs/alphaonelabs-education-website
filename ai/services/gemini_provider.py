import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiProvider:
    """Google Gemini AI provider using the new API format."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        logger.info(f"Gemini provider initialized with model: {self.model}")
    
    def generate_response(self, prompt, context=None):
        """Generate a response using Gemini API."""
        if not self.api_key:
            logger.warning("Gemini API key not configured")
            return "Gemini API is not configured properly."
        
        try:
            # Format the prompt with context if provided
            formatted_prompt = self._format_prompt(prompt, context)
            
            # Add formatting instructions for code and math
            formatting_instructions = """
When providing code examples:
1. Use triple backticks with language specification
2. Include proper indentation
3. Add comments for clarity
4. Use consistent code style

When providing mathematical content:
1. Use LaTeX-style formatting with $ for inline math
2. Use $$ for block equations
3. Use proper mathematical notation
4. Include step-by-step explanations

For text formatting:
1. Use ** for bold text
2. Use * for italic text
3. Use ` for code snippets
4. Use > for blockquotes
5. Use - or * for bullet points
6. Use 1. 2. 3. for numbered lists

Example:
```python
def calculate_sum(a, b):
    # Add two numbers
    return a + b
```

Math example:
$E = mc^2$

**Important points:**
* Key concept 1
* Key concept 2
"""
            
            # Combine the instructions with the prompt
            final_prompt = f"{formatting_instructions}\n\nStudent question: {formatted_prompt}"
            
            # Prepare the request data
            data = {
                "contents": [{
                    "parts": [{"text": final_prompt}]
                }]
            }
            
            # Make the API request
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return "I encountered an error while processing your request. Please try again."
            
            # Parse the response
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and result['candidates']:
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Process the response to ensure proper formatting
                processed_text = self._process_response(generated_text, context)
                
                logger.info("Successfully generated response from Gemini")
                return processed_text
            else:
                logger.warning("No response generated from Gemini")
                return "I couldn't generate a proper response. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            return "I encountered an error while processing your request. Please try again."
    
    def _format_prompt(self, prompt, context=None):
        """Format the prompt with context for educational assistant."""
        if not context:
            return prompt
            
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

    def _process_response(self, text, context=None):
        """Process the response to ensure proper formatting."""
        if not context:
            return text
        
        subject = context.get('subject', 'general')
        
        # Add subject-specific formatting
        if subject in ['mathematics', 'physics', 'chemistry']:
            # Ensure math expressions are properly formatted
            text = text.replace('$', '$$')
            
            # Format bold text properly
            text = text.replace('** ', '**')
            text = text.replace(' **', '**')
            text = text.replace('**', '**')
            
            # Format lists properly
            text = text.replace('\n* ', '\n* ')
            text = text.replace('\n- ', '\n* ')
            
            # Format code blocks
            text = text.replace('```', '```python')
        elif subject == 'programming':
            # Ensure code blocks have proper language specification
            text = text.replace('```', '```python')
            
            # Format bold text properly
            text = text.replace('** ', '**')
            text = text.replace(' **', '**')
            text = text.replace('**', '**')
            
            # Format lists
            text = text.replace('\n* ', '\n* ')
            text = text.replace('\n- ', '\n* ')
        else:
            # General formatting for all subjects
            text = text.replace('** ', '**')
            text = text.replace(' **', '**')
            text = text.replace('**', '**')
            text = text.replace('\n* ', '\n* ')
            text = text.replace('\n- ', '\n* ')
        
        # Clean up any remaining spacing issues
        text = text.replace('** ', '**')
        text = text.replace(' **', '**')
        
        return text 