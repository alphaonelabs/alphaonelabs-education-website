import logging
import random

logger = logging.getLogger(__name__)

class DemoProvider:
    """Demo AI provider for development and testing."""
    
    def generate_response(self, prompt, context=None):
        """Generate a demo response based on the subject."""
        subject = context.get('subject', 'general') if context else 'general'
        
        responses = {
            'mathematics': [
                "That's an interesting math question! In mathematics, we approach this by identifying the key principles involved. Let's break this down step by step...",
                "This mathematical concept connects to several important areas. First, let me explain the fundamental theory...",
                "To solve this mathematics problem, we need to apply these key formulas and techniques..."
            ],
            'science': [
                "From a scientific perspective, this phenomenon can be explained by several key principles. Let's explore how they work...",
                "In science, we observe this effect due to the interaction between multiple factors. Here's what's happening...",
                "The scientific explanation for this involves understanding the underlying mechanisms. Let me explain..."
            ],
            'programming': [
                "When implementing this in code, you'll want to consider these best practices and algorithms. Here's how we can approach it...",
                "This programming challenge can be approached using several design patterns. Let's look at the most suitable one...",
                "To code this functionality, we should follow these steps and consider these edge cases. Here's the plan..."
            ],
            'history': [
                "This historical period was shaped by several important events and social movements. Let's explore the key factors...",
                "Looking at this through a historical lens, we can identify these key influences. Here's what happened...",
                "The historical context is essential to understand this event. Let me provide some background..."
            ],
            'languages': [
                "This linguistic concept appears in many languages with interesting variations. Let's explore some examples...",
                "When learning this language feature, it helps to compare it with concepts from other languages. Here's how...",
                "This expression has both literal and cultural meanings. Let me explain both aspects..."
            ]
        }
        
        # Select a response based on subject
        subject_responses = responses.get(subject, [
            "That's a great question! Here's what you need to know...",
            "I'd be happy to help you understand this topic better. Let's explore it together...",
            "Learning about this subject involves understanding these fundamental principles. Here's what you should know..."
        ])
        
        # Get response preferences if context is provided
        if context and 'preferences' in context:
            response_format = context['preferences'].get('format', 'paragraph')
            response_length = context['preferences'].get('length', 'detailed')
            response_style = context['preferences'].get('style', 'formal')
        else:
            response_format = 'paragraph'
            response_length = 'detailed'
            response_style = 'formal'
        
        # Select a basic response
        basic_response = random.choice(subject_responses)
        
        # Adapt response based on format preference
        if response_format == 'bullets':
            points = [
                "Point 1: " + basic_response,
                "Point 2: Consider these additional aspects...",
                "Point 3: Finally, remember that..."
            ]
            return "Here's my response:\n\n* " + "\n* ".join(points)
        elif response_format == 'step-by-step':
            steps = [
                "Step 1: " + basic_response,
                "Step 2: Next, we need to consider...",
                "Step 3: Finally, we can conclude that..."
            ]
            return "Let me walk you through this:\n\n1. " + "\n2. ".join(steps)
        else:
            return basic_response 