from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json
import random
import logging

from .models import Interaction, StudentProfile

logger = logging.getLogger(__name__)

# Try to import the AI provider, with fallback
try:
    from .services.ai_provider import get_ai_provider
    AI_PROVIDER_AVAILABLE = True
except ImportError:
    logger.warning("AI provider module not available, using built-in demo responses")
    AI_PROVIDER_AVAILABLE = False

@login_required
def chat_view(request):
    """Render the AI chat interface."""
    # Get recent interactions for this user
    recent_interactions = Interaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get or create student profile
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    subjects = [
        {'value': 'general', 'label': 'General'},
        {'value': 'mathematics', 'label': 'Mathematics'}, 
        {'value': 'science', 'label': 'Science'},
        {'value': 'programming', 'label': 'Programming'}, 
        {'value': 'history', 'label': 'History'},
        {'value': 'languages', 'label': 'Languages'}
    ]
    
    context = {
        'recent_interactions': recent_interactions,
        'profile': profile,
        'subjects': subjects,
        'page_title': 'AI Learning Assistant'
    }
    
    return render(request, 'ai/chat.html', context)

@login_required
@require_POST
def chat_completion(request):
    """API endpoint for AI chat interactions."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        subject = data.get('subject', 'general')
        
        logger.info(f"Received chat request: subject={subject}, message={message[:50]}...")
        
        # Save the user's question to the database
        interaction = Interaction.objects.create(
            user=request.user,
            question=message,
            subject=subject,
            ai_provider='demo' if not AI_PROVIDER_AVAILABLE else 'ai'
        )
        
        # Get AI response
        response_text = get_ai_response(message, subject, request.user)
        logger.info(f"Generated response: {response_text[:50]}...")
        
        # Update the interaction with the response
        interaction.answer = response_text
        interaction.save()
        
        return JsonResponse({
            'success': True,
            'response': {
                'text': response_text,
                'provider': interaction.ai_provider,
                'interaction_id': interaction.id
            }
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({
            'success': False,
            'error': "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        logger.error(f"Error in chat_completion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def get_ai_response(message, subject, user):
    """Generate AI response using the configured provider or fallback to demo."""
    try:
        # If AI provider module is available, use it
        if (AI_PROVIDER_AVAILABLE):
            # Get user preferences
            profile, created = StudentProfile.objects.get_or_create(user=user)
            
            # Prepare context for the AI
            context = {
                'subject': subject,
                'profile': {
                    'learning_style': profile.learning_style,
                    'difficulty_preference': profile.difficulty_preference,
                    'response_length': profile.response_length,
                    'include_examples': profile.include_examples,
                    'include_visuals': profile.include_visuals,
                },
                'user': {
                    'username': user.username,
                }
            }
            
            # Get AI provider and generate response
            provider = get_ai_provider()
            return provider.generate_response(message, context)
        else:
            # Fallback to built-in demo responses
            return get_demo_response(message, subject)
            
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return f"I apologize, but I encountered an error while processing your request. Please try again later."

def get_demo_response(message, subject):
    """Generate a demo response based on subject."""
    responses = {
        'mathematics': [
            "That's an interesting math question! In mathematics, we approach this by identifying the key principles involved.",
            "This mathematical concept connects to several important areas. First, let me explain the fundamental theory...",
            "To solve this mathematics problem, we need to apply these key formulas and techniques..."
        ],
        'science': [
            "From a scientific perspective, this phenomenon can be explained by several key principles.",
            "In science, we observe this effect due to the interaction between multiple factors.",
            "The scientific explanation for this involves understanding the underlying mechanisms..."
        ],
        'programming': [
            "When implementing this in code, you'll want to consider these best practices and algorithms.",
            "This programming challenge can be approached using several design patterns.",
            "To code this functionality, we should follow these steps and consider these edge cases..."
        ],
        'history': [
            "This historical period was shaped by several important events and social movements.",
            "Looking at this through a historical lens, we can identify these key influences.",
            "The historical context is essential to understand this event."
        ],
        'languages': [
            "This linguistic concept appears in many languages with interesting variations.",
            "When learning this language feature, it helps to compare it with concepts from other languages.",
            "This expression has both literal and cultural meanings."
        ]
    }
    
    # Select a response based on subject
    subject_responses = responses.get(subject, [
        "That's a great question! Here's what you need to know...",
        "I'd be happy to help you understand this topic better.",
        "Learning about this subject involves understanding these fundamental principles..."
    ])
    
    response = random.choice(subject_responses)
    
    return response

@login_required
def dashboard(request):
    """Display AI learning dashboard with progress stats."""
    # Get recent conversations
    recent_conversations = Interaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    recent_conversations_data = [
        {
            'subject': interaction.subject,
            'last_message': interaction.question,
            'updated_at': interaction.created_at,
            'url': f"/ai/chat/{interaction.id}/"
        }
        for interaction in recent_conversations
    ]
    
    # Get progress data
    from .progress import ProgressTracker
    tracker = ProgressTracker(request.user.id)
    progress_data = tracker.get_overall_progress()
    progress_percentage = int(progress_data.get('completion_percentage', 0))
    
    # Get suggested topics
    suggested_topics = tracker.get_suggested_topics(limit=5)
    
    return render(request, 'ai/dashboard.html', {
        'page_title': 'Learning Dashboard',
        'recent_conversations': recent_conversations_data,
        'progress_percentage': progress_percentage,
        'progress_details': progress_data,
        'suggested_topics': suggested_topics,
    })

@login_required
def progress_view(request):
    """Show detailed learning progress."""
    # Get user's interactions grouped by subject
    from django.db.models import Count
    subject_counts = Interaction.objects.filter(user=request.user).values('subject').annotate(count=Count('id'))
    
    # Get user's profile for preferences
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'ai/progress.html', {
        'page_title': 'Learning Progress',
        'subject_counts': subject_counts,
        'profile': profile,
    })

@login_required
def settings_view(request):
    """AI assistant settings."""
    # Get user's profile for current settings
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'ai/settings.html', {
        'page_title': 'AI Assistant Settings',
        'profile': profile,
    })

@login_required
def tutor_view(request):
    """Render the personalized tutor interface."""
    # Get recent interactions for this user
    recent_interactions = Interaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get or create student profile
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    subjects = [
        {'value': 'general', 'label': 'General'},
        {'value': 'mathematics', 'label': 'Mathematics'}, 
        {'value': 'science', 'label': 'Science'},
        {'value': 'programming', 'label': 'Programming'}, 
        {'value': 'history', 'label': 'History'},
        {'value': 'languages', 'label': 'Languages'}
    ]
    
    context = {
        'recent_interactions': recent_interactions,
        'profile': profile,
        'subjects': subjects,
        'page_title': 'Personalized Tutor'
    }
    
    return render(request, 'ai/tutor.html', context)

@login_required
@require_POST
def tutor_completion(request):
    """API endpoint for personalized tutor interactions."""
    try:
        from .tutors import PersonalizedTutor
        
        data = json.loads(request.body)
        message = data.get('message', '')
        subject = data.get('subject', 'general')
        difficulty = data.get('difficulty', 'moderate')
        
        # Create context for the tutor
        context = {
            'subject': subject,
            'difficulty': difficulty
        }
        
        # Initialize personalized tutor
        tutor = PersonalizedTutor(request.user.id)
        
        # Save the interaction
        interaction = Interaction.objects.create(
            user=request.user,
            question=message,
            subject=subject,
            ai_provider='personalized_tutor'  # Use a more specific identifier
        )
        
        # Get personalized response
        tutor_response = tutor.ask(message, context)
        response_text = tutor_response['text']
        
        # Update the interaction with the response
        interaction.answer = response_text
        interaction.save()
        
        return JsonResponse({
            'success': True,
            'response': {
                'text': response_text,
                'provider': 'personalized',
                'personalized': True,
                'interaction_id': interaction.id
            }
        })
        
    except Exception as e:
        logger.error(f"Error in tutor_completion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
