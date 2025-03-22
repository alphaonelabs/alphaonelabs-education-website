from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json
import random
import logging

from .models import Interaction, StudentProfile, ChatSession, Message

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
    
    # Get recent chat sessions for sidebar
    chat_sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:10]
    
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
        'page_title': 'AI Learning Assistant',
        'chat_sessions': chat_sessions
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
        
        # Extract response preferences
        preferences = data.get('preferences', {})
        response_format = preferences.get('responseFormat', 'paragraph')
        response_length = preferences.get('responseLength', 'detailed')
        response_style = preferences.get('responseStyle', 'formal')
        
        logger.info(f"Received chat request: subject={subject}, message={message[:50]}...")
        logger.info(f"Response preferences: format={response_format}, length={response_length}, style={response_style}")
        
        # Save the user's question to the database
        interaction = Interaction.objects.create(
            user=request.user,
            question=message,
            subject=subject,
            ai_provider='demo' if not AI_PROVIDER_AVAILABLE else 'ai'
        )
        
        # Get AI response with preferences
        response_text = get_ai_response(
            message, 
            subject,
            request.user,
            response_format=response_format,
            response_length=response_length,
            response_style=response_style
        )
        
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

def get_ai_response(message, subject, user, response_format='paragraph', response_length='detailed', response_style='formal'):
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
                },
                'preferences': {
                    'format': response_format,
                    'length': response_length,
                    'style': response_style
                }
            }
            
            # Get AI provider and generate response
            provider = get_ai_provider()
            return provider.generate_response(message, context)
        else:
            # Fallback to built-in demo responses with preferences
            return get_demo_response(message, subject, response_format, response_length, response_style)
            
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return f"I apologize, but I encountered an error while processing your request. Please try again later."

def get_demo_response(message, subject, response_format='paragraph', response_length='detailed', response_style='formal'):
    """Generate a demo response based on subject and preferences."""
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
    
    basic_response = random.choice(subject_responses)
    
    # Adapt response based on format preference
    if response_format == 'bullets':
        points = ["Point 1: " + basic_response, "Point 2: Consider these additional aspects...", "Point 3: Finally, remember that..."]
        return "Here's my response:\n\n* " + "\n* ".join(points)
    elif response_format == 'step-by-step':
        steps = ["Step 1: " + basic_response, "Step 2: Next, we need to consider...", "Step 3: Finally, we can conclude that..."]
        return "Let me walk you through this:\n\n1. " + "\n2. ".join(steps)
    elif response_format == 'conversational':
        return "Great question! " + basic_response + " What do you think about that? I'd be happy to elaborate further."
    
    # Adapt response based on length preference
    length_multiplier = {
        'concise': 0.5,
        'detailed': 1.0,
        'comprehensive': 2.0
    }.get(response_length, 1.0)
    
    # Adapt response based on style preference
    if response_style == 'simple':
        response = f"{basic_response} This is explained in simple terms."
    elif response_style == 'technical':
        response = f"{basic_response} From a technical standpoint, we can analyze this further using specific terminology and concepts."
    elif response_style == 'formal':
        response = f"{basic_response} Furthermore, it is important to consider the following aspects of this topic."
    elif response_style == 'casual':
        response = f"Hey there! {basic_response} Pretty cool, right? Let me know if you want to know more!"
    else:
        response = basic_response
    
    # Adjust length based on preference
    if length_multiplier < 1.0:
        return response.split('.')[0] + '.'
    elif length_multiplier > 1.0:
        return response + " In addition, we can explore several related concepts that help deepen our understanding of this topic. For instance, consider how this relates to other areas. There are also practical applications worth discussing."
    
    return response

@login_required
def dashboard_view(request):
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

@login_required
@require_POST
def save_chat(request):
    """Save a chat session with all messages."""
    try:
        data = json.loads(request.body)
        chat_id = data.get('chat_id')
        title = data.get('title', '')
        messages = data.get('messages', [])
        subject = data.get('subject', 'general')
        
        if not messages or len(messages) < 2:  # Require at least 1 user message and 1 AI response
            return JsonResponse({'success': False, 'error': 'Chat is too short to save'})
        
        # Auto-generate title if none provided or it's the default
        if not title or title == "New Conversation" or title == "Untitled Chat":
            # Find the first user message
            first_user_message = next((msg for msg in messages if msg.get('role') == 'user'), None)
            if first_user_message:
                # Generate a title from the first user message
                user_message = first_user_message.get('content', '')
                # Clean up the message and limit length
                title = user_message.strip()
                # Remove common punctuation and limit length
                title = ''.join(c for c in title if c not in '?!.,;:\'\"')
                if len(title) > 40:
                    title = title[:40] + '...'
            else:
                title = 'Untitled Chat'
                
        # If chat_id is provided, try to find existing chat
        chat = None
        is_new = False
        if chat_id:
            try:
                chat = ChatSession.objects.get(id=chat_id, user=request.user)
            except ChatSession.DoesNotExist:
                # If chat doesn't exist, create a new one
                pass
        
        # If no existing chat was found, create a new one
        if not chat:
            chat = ChatSession.objects.create(
                user=request.user,
                title=title,
                subject=subject
            )
            is_new = True
        else:
            # Update existing chat
            chat.title = title
            chat.subject = subject
            chat.save()
            
            # Clear existing messages for this chat
            chat.messages.all().delete()
        
        # Save all messages
        for idx, msg in enumerate(messages):
            Message.objects.create(
                chat=chat,
                role=msg.get('role', 'user'),
                content=msg.get('content', ''),
                order=idx
            )
        
        return JsonResponse({
            'success': True, 
            'chat_id': chat.id,
            'title': chat.title, # Return the title in case it was auto-generated
            'is_new': is_new
        })
        
    except Exception as e:
        logger.error(f"Error saving chat: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_chat(request):
    """Retrieve a chat session with all messages."""
    try:
        chat_id = request.GET.get('chat_id')
        
        if not chat_id:
            return JsonResponse({'success': False, 'error': 'No chat ID provided'})
        
        try:
            chat = ChatSession.objects.get(id=chat_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Chat not found'})
        
        # Get all messages for this chat in order
        messages = chat.messages.all().order_by('order')
        
        # Format messages for the response
        formatted_messages = [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
        ]
        
        return JsonResponse({
            'success': True,
            'chat_id': chat.id,
            'title': chat.title,
            'subject': chat.subject,
            'created_at': chat.created_at.isoformat(),
            'messages': formatted_messages
        })
        
    except Exception as e:
        logger.error(f"Error retrieving chat: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def rate_interaction(request, interaction_id):
    """Rate an AI interaction."""
    try:
        interaction = Interaction.objects.get(id=interaction_id)
        
        # Check if the user is authorized to rate this interaction
        if interaction.user != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
            
        # Parse the request body
        data = json.loads(request.body)
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate the rating
        if rating is None or not isinstance(rating, (int, float)) or int(rating) < 1 or int(rating) > 5:
            return JsonResponse({
                'success': False,
                'error': 'Invalid rating value. Must be between 1 and 5.'
            }, status=400)
            
        # Save the rating and comment
        interaction.feedback_rating = int(rating)
        if comment:
            interaction.feedback_comment = comment
        interaction.save()
        
        logger.info(f"Interaction {interaction_id} rated {rating}/5 by user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'interaction_id': interaction_id,
            'rating': rating
        })
        
    except Interaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Interaction not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in rate_interaction: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
