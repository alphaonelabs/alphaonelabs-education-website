import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import StudyPlan, StudyTask
from .services.ai_provider import get_ai_provider

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.core.exceptions import PermissionDenied
import json
import random
import logging
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from django.views.generic import RedirectView
from django.urls import path, include
from django.conf import settings

from .models import Interaction, StudentProfile, ChatSession, Message, ProgressRecord, StudyPlan, Achievement, StudyGroup, GroupDiscussion, DiscussionReply, Topic, Subject, LearningStreak, UserAchievement, Feedback, LearningPath, Dashboard, StudyTask
from .services.ai_provider import get_ai_provider
from .services.config import get_ai_settings, is_ai_configured, log_ai_configuration

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
    """Render the chat interface."""
    # Get all subjects
    subjects = [
        {'value': 'general', 'label': 'General'},
        {'value': 'mathematics', 'label': 'Mathematics'},
        {'value': 'science', 'label': 'Science'},
        {'value': 'programming', 'label': 'Programming'},
        {'value': 'history', 'label': 'History'},
        {'value': 'languages', 'label': 'Languages'},
        {'value': 'physics', 'label': 'Physics'},
        {'value': 'chemistry', 'label': 'Chemistry'},
        {'value': 'biology', 'label': 'Biology'},
        {'value': 'literature', 'label': 'Literature'}
    ]
    
    # Get user's recent interactions
    recent_interactions = Interaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'subjects': subjects,
        'recent_interactions': recent_interactions,
        'page_title': 'AI Chat Assistant'
    }
    return render(request, 'ai/chat.html', context)

@login_required
@require_http_methods(['POST'])
def send_message(request):
    """Handle sending messages to the AI assistant."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        message = data.get('message')
        subject = data.get('subject', 'general')

        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Get AI provider
        ai_provider = get_ai_provider()
        
        # Prepare context for the AI
        context = {
            'subject': subject,
            'user': request.user.username,
            'message': message
        }
        
        # Get AI response
        response = ai_provider.generate_response(message, context)
        
        # Save the interaction
        interaction = Interaction.objects.create(
            user=request.user,
            question=message,
            answer=response,
            subject=subject
        )

        return JsonResponse({
            'success': True,
            'response': response,
            'interaction_id': interaction.id
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['POST'])
def clear_chat(request):
    """Clear the chat history."""
    # TODO: Implement chat history clearing logic
    return JsonResponse({'success': True})

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
                'provider': 'personalized_tutor',
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

@login_required
def progress_dashboard_view(request):
    """Display detailed progress dashboard."""
    # Get all study plans for the user
    study_plans = StudyPlan.objects.filter(user=request.user)
    
    # Calculate overall statistics
    total_study_hours = sum(plan.total_hours for plan in study_plans)
    completed_hours = sum(plan.completed_hours for plan in study_plans)
    total_tasks = sum(plan.tasks.count() for plan in study_plans)
    completed_tasks = sum(plan.tasks.filter(completed=True).count() for plan in study_plans)
    
    # Calculate subject-wise progress
    subject_progress = {}
    for plan in study_plans:
        if plan.subject not in subject_progress:
            subject_progress[plan.subject] = {
                'total_hours': 0,
                'completed_hours': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'progress': 0,
                'active_plans': 0,
                'upcoming_tasks': 0
            }
        subject_progress[plan.subject]['total_hours'] += plan.total_hours
        subject_progress[plan.subject]['completed_hours'] += plan.completed_hours
        subject_progress[plan.subject]['total_tasks'] += plan.tasks.count()
        subject_progress[plan.subject]['completed_tasks'] += plan.tasks.filter(completed=True).count()
        subject_progress[plan.subject]['active_plans'] += 1
        subject_progress[plan.subject]['upcoming_tasks'] += plan.tasks.filter(completed=False).count()
        subject_progress[plan.subject]['progress'] = round((plan.completed_hours / plan.total_hours * 100), 2) if plan.total_hours > 0 else 0
    
    # Get recent activity with more details
    recent_activity = []
    for plan in study_plans:
        recent_tasks = plan.tasks.filter(completed=True).order_by('-updated_at')[:5]
        for task in recent_tasks:
            recent_activity.append({
                'date': task.updated_at,
                'type': 'task_completed',
                'subject': plan.subject,
                'title': task.title,
                'hours': task.estimated_hours,
                'plan_title': plan.title,
                'description': task.description
            })
    
    # Sort recent activity by date
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    recent_activity = recent_activity[:10]  # Get only the 10 most recent activities
    
    # Get upcoming tasks
    upcoming_tasks = []
    for plan in study_plans:
        tasks = plan.tasks.filter(completed=False).order_by('created_at')[:5]
        for task in tasks:
            upcoming_tasks.append({
                'title': task.title,
                'subject': plan.subject,
                'plan_title': plan.title,
                'hours': task.estimated_hours,
                'description': task.description
            })
    
    # Sort upcoming tasks by hours (prioritize longer tasks)
    upcoming_tasks.sort(key=lambda x: x['hours'], reverse=True)
    upcoming_tasks = upcoming_tasks[:5]  # Get only the 5 most important upcoming tasks
    
    context = {
        'study_plans': study_plans,
        'total_study_hours': total_study_hours,
        'completed_hours': completed_hours,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'subject_progress': subject_progress,
        'recent_activity': recent_activity,
        'upcoming_tasks': upcoming_tasks,
        'overall_progress': round((completed_hours / total_study_hours * 100), 2) if total_study_hours > 0 else 0
    }
    
    return render(request, 'ai/progress_dashboard.html', context)

@login_required
def study_planner_view(request):
    """Display study planner interface."""
    # Get user's subjects from study plans
    user_study_plans = StudyPlan.objects.filter(user=request.user)
    user_subjects = user_study_plans.values_list('subject', flat=True).distinct()
    
    # Get completed topics using ProgressRecord
    completed_topics = ProgressRecord.objects.filter(
        user=request.user,
        subject__in=user_subjects,
        score=100
    ).count()
    
    # Get total topics
    total_topics = Topic.objects.filter(subject__in=user_subjects).count()
    
    # Calculate overall progress
    overall_progress = (completed_topics / total_topics * 100) if total_topics > 0 else 0
    
    # Get progress by subject
    subject_progress = {}
    for subject in user_subjects:
        subject_completed = ProgressRecord.objects.filter(
            user=request.user,
            subject=subject,
            score=100
        ).count()
        subject_total = Topic.objects.filter(subject=subject).count()
        subject_progress[subject] = {
            'completed': subject_completed,
            'total': subject_total,
            'percentage': (subject_completed / subject_total * 100) if subject_total > 0 else 0
        }
    
    context = {
        'overall_progress': overall_progress,
        'completed_topics': completed_topics,
        'total_topics': total_topics,
        'subject_progress': subject_progress,
        'subjects': user_subjects,
        'study_plans': user_study_plans
    }
    
    return render(request, 'ai/study_planner.html', context)

@login_required
def achievements_view(request):
    """Display user's achievements and available badges."""
    # Get all achievements
    all_achievements = Achievement.objects.all()
    
    # Get user's unlocked achievements
    user_achievements = UserAchievement.objects.filter(user=request.user)
    unlocked_achievement_ids = user_achievements.values_list('achievement_id', flat=True)
    
    # Get user's study plans and progress
    study_plans = StudyPlan.objects.filter(user=request.user)
    total_study_hours = sum(plan.total_hours for plan in study_plans)
    completed_hours = sum(plan.completed_hours for plan in study_plans)
    total_tasks = sum(plan.tasks.count() for plan in study_plans)
    completed_tasks = sum(plan.tasks.filter(completed=True).count() for plan in study_plans)
    
    # Get learning streaks
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get achievement categories
    categories = Achievement.objects.values('type').distinct()
    
    # Get recent unlocks
    recent_unlocks = UserAchievement.objects.filter(user=request.user).order_by('-earned_at')[:10]
    
    # Calculate achievement progress
    achievement_progress = {
        'study_time': {
            'current': completed_hours,
            'target': 100,  # 100 hours target
            'percentage': min(100, (completed_hours / 100) * 100) if completed_hours > 0 else 0
        },
        'topics_completed': {
            'current': completed_tasks,
            'target': 50,  # 50 topics target
            'percentage': min(100, (completed_tasks / 50) * 100) if completed_tasks > 0 else 0
        },
        'streak': {
            'current': streak.current_streak,
            'target': 30,  # 30 days streak target
            'percentage': min(100, (streak.current_streak / 30) * 100) if streak.current_streak > 0 else 0
        }
    }
    
    # Calculate category progress
    category_progress = {}
    for category in categories:
        category_name = category['type']
        total_achievements = Achievement.objects.filter(type=category_name).count()
        unlocked_achievements = UserAchievement.objects.filter(
            user=request.user,
            achievement__type=category_name
        ).count()
        category_progress[category_name] = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
    
    # Calculate overall achievement progress
    total_achievements = Achievement.objects.count()
    unlocked_count = user_achievements.count()
    achievement_progress_percentage = (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0
    
    return render(request, 'ai/achievements.html', {
        'page_title': 'Achievements',
        'all_achievements': all_achievements,
        'user_achievements': user_achievements,
        'categories': categories,
        'recent_unlocks': recent_unlocks,
        'achievement_progress': achievement_progress,
        'category_progress': category_progress,
        'unlocked_count': unlocked_count,
        'total_count': total_achievements,
        'study_plans': study_plans,
        'total_study_hours': total_study_hours,
        'completed_hours': completed_hours,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
    })

@login_required
def group_discussions_view(request):
    """Display group discussions and collaborative learning features."""
    # Get user's study groups
    study_groups = StudyGroup.objects.filter(members=request.user)
    
    # Get active discussions
    active_discussions = GroupDiscussion.objects.filter(
        group__in=study_groups
    ).order_by('-created_at')
    
    # Get user's recent contributions
    recent_contributions = DiscussionReply.objects.filter(
        author=request.user
    ).order_by('-created_at')[:5]
    
    return render(request, 'ai/group_discussions.html', {
        'page_title': 'Group Discussions',
        'study_groups': study_groups,
        'active_discussions': active_discussions,
        'recent_contributions': recent_contributions,
    })

# API Endpoints
@login_required
@require_POST
def create_study_plan(request):
    """Create a new study plan."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        study_plan = StudyPlan.objects.create(
            user=request.user,
            title=data['title'],
            description=data.get('description', ''),
            subject=data.get('subject', 'general'),
            start_date=data.get('start_date', timezone.now()),
            end_date=data.get('end_date', timezone.now() + timezone.timedelta(days=30)),
            total_hours=data.get('total_hours', 0)
        )
        return JsonResponse({
            'success': True,
            'id': study_plan.id,
            'title': study_plan.title,
            'description': study_plan.description
        })
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error creating study plan: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def update_study_plan(request, plan_id):
    """Update an existing study plan."""
    try:
        study_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
        data = json.loads(request.body)
        
        study_plan.title = data.get('title', study_plan.title)
        study_plan.subject = data.get('subject', study_plan.subject)
        study_plan.description = data.get('description', study_plan.description)
        study_plan.save()
        
        return JsonResponse({
            'success': True,
            'study_plan': {
                'id': study_plan.id,
                'title': study_plan.title,
                'subject': study_plan.subject,
                'description': study_plan.description
            }
        })
        
    except StudyPlan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study plan not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in update_study_plan: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def delete_study_plan(request, plan_id):
    """Delete a study plan."""
    try:
        study_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
        study_plan.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Study plan deleted successfully'
        })
        
    except StudyPlan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study plan not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in delete_study_plan: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def update_progress(request):
    """Update user's learning progress."""
    try:
        data = json.loads(request.body)
        # TODO: Implement progress update logic
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

@login_required
@require_POST
def unlock_achievement(request):
    """Unlock a new achievement."""
    try:
        data = json.loads(request.body)
        achievement = get_object_or_404(Achievement, id=data['achievement_id'])
        request.user.achievements.add(achievement)
        return JsonResponse({
            'success': True,
            'achievement': {
                'id': achievement.id,
                'title': achievement.title,
                'description': achievement.description
            }
        })
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

@login_required
def get_study_plan(request, plan_id):
    """Get details of a specific study plan."""
    study_plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    # Calculate progress percentage
    progress_percentage = study_plan.progress_percentage if hasattr(study_plan, 'progress_percentage') else 0
    
    return JsonResponse({
        'id': study_plan.id,
        'title': study_plan.title,
        'description': study_plan.description,
        'subject': study_plan.subject,
        'start_date': study_plan.start_date,
        'end_date': study_plan.end_date,
        'total_hours': study_plan.total_hours,
        'completed_hours': getattr(study_plan, 'completed_hours', 0),
        'progress_percentage': progress_percentage
    })

@login_required
def progress_dashboard(request):
    """View for the AI learning progress dashboard."""
    # Get all study plans for the user
    study_plans = StudyPlan.objects.filter(user=request.user)
    
    # Calculate overall statistics
    total_study_hours = sum(plan.total_hours for plan in study_plans)
    completed_hours = sum(plan.completed_hours for plan in study_plans)
    total_tasks = sum(plan.tasks.count() for plan in study_plans)
    completed_tasks = sum(plan.tasks.filter(completed=True).count() for plan in study_plans)
    
    # Calculate subject-wise progress
    subject_progress = {}
    for plan in study_plans:
        if plan.subject not in subject_progress:
            subject_progress[plan.subject] = {
                'total_hours': 0,
                'completed_hours': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'progress': 0,
                'active_plans': 0,
                'upcoming_tasks': 0
            }
        subject_progress[plan.subject]['total_hours'] += plan.total_hours
        subject_progress[plan.subject]['completed_hours'] += plan.completed_hours
        subject_progress[plan.subject]['total_tasks'] += plan.tasks.count()
        subject_progress[plan.subject]['completed_tasks'] += plan.tasks.filter(completed=True).count()
        subject_progress[plan.subject]['active_plans'] += 1
        subject_progress[plan.subject]['upcoming_tasks'] += plan.tasks.filter(completed=False).count()
        subject_progress[plan.subject]['progress'] = round((plan.completed_hours / plan.total_hours * 100), 2) if plan.total_hours > 0 else 0
    
    # Get recent activity with more details
    recent_activity = []
    for plan in study_plans:
        recent_tasks = plan.tasks.filter(completed=True).order_by('-updated_at')[:5]
        for task in recent_tasks:
            recent_activity.append({
                'date': task.updated_at,
                'type': 'task_completed',
                'subject': plan.subject,
                'title': task.title,
                'hours': task.estimated_hours,
                'plan_title': plan.title,
                'description': task.description
            })
    
    # Sort recent activity by date
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    recent_activity = recent_activity[:10]  # Get only the 10 most recent activities
    
    # Get upcoming tasks
    upcoming_tasks = []
    for plan in study_plans:
        tasks = plan.tasks.filter(completed=False).order_by('created_at')[:5]
        for task in tasks:
            upcoming_tasks.append({
                'title': task.title,
                'subject': plan.subject,
                'plan_title': plan.title,
                'hours': task.estimated_hours,
                'description': task.description
            })
    
    # Sort upcoming tasks by hours (prioritize longer tasks)
    upcoming_tasks.sort(key=lambda x: x['hours'], reverse=True)
    upcoming_tasks = upcoming_tasks[:5]  # Get only the 5 most important upcoming tasks
    
    context = {
        'study_plans': study_plans,
        'total_study_hours': total_study_hours,
        'completed_hours': completed_hours,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'subject_progress': subject_progress,
        'recent_activity': recent_activity,
        'upcoming_tasks': upcoming_tasks,
        'overall_progress': round((completed_hours / total_study_hours * 100), 2) if total_study_hours > 0 else 0
    }
    
    return render(request, 'ai/progress_dashboard.html', context)

@login_required
def achievements(request):
    """Render the achievements page."""
    context = {
        'achievements': Achievement.objects.all(),
        'user_achievements': request.user.achievements.all()
    }
    return render(request, 'ai/achievements.html', context)

@login_required
def group_discussions(request):
    """Render the group discussions page."""
    context = {
        'discussions': GroupDiscussion.objects.all().order_by('-created_at'),
        'user_discussions': request.user.discussions.all()
    }
    return render(request, 'ai/group_discussions.html', context)

@login_required
@require_http_methods(['POST'])
def create_discussion(request):
    """Create a new group discussion."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        group_id = data.get('group_id')
        group = get_object_or_404(StudyGroup, id=group_id, members=request.user)
        
        discussion = GroupDiscussion.objects.create(
            group=group,
            title=data['title'],
            content=data['content'],
            author=request.user
        )
        
        return JsonResponse({
            'success': True,
            'discussion': {
                'id': discussion.id,
                'title': discussion.title,
                'content': discussion.content,
                'author': discussion.author.username,
                'created_at': discussion.created_at.isoformat(),
                'likes_count': discussion.likes_count
            }
        })
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error creating discussion: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['POST'])
def create_discussion_reply(request, discussion_id):
    """Create a reply to a group discussion."""
    try:
        discussion = get_object_or_404(GroupDiscussion, id=discussion_id)
        data = json.loads(request.body.decode('utf-8'))
        
        reply = DiscussionReply.objects.create(
            discussion=discussion,
            content=data['content'],
            author=request.user
        )
        
        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'author': reply.author.username,
                'created_at': reply.created_at.isoformat(),
                'likes_count': reply.likes_count
            }
        })
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error creating discussion reply: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['POST'])
def like_discussion(request, discussion_id):
    """Like or unlike a discussion."""
    try:
        discussion = get_object_or_404(GroupDiscussion, id=discussion_id)
        
        if request.user in discussion.likes.all():
            discussion.likes.remove(request.user)
            liked = False
        else:
            discussion.likes.add(request.user)
            liked = True
            
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': discussion.likes_count
        })
    except Exception as e:
        logger.error(f"Error liking discussion: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['POST'])
def like_reply(request, reply_id):
    """Like or unlike a discussion reply."""
    try:
        reply = get_object_or_404(DiscussionReply, id=reply_id)
        
        if request.user in reply.likes.all():
            reply.likes.remove(request.user)
            liked = False
        else:
            reply.likes.add(request.user)
            liked = True
            
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': reply.likes_count
        })
    except Exception as e:
        logger.error(f"Error liking reply: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_group_discussion(request, discussion_id):
    """Get details of a specific group discussion."""
    try:
        discussion = get_object_or_404(GroupDiscussion, id=discussion_id)
        
        # Get all replies for this discussion
        replies = discussion.replies.all().order_by('created_at')
        
        # Format replies for the response
        formatted_replies = [{
            'id': reply.id,
            'content': reply.content,
            'author': reply.author.username,
            'created_at': reply.created_at.isoformat(),
            'likes_count': reply.likes_count,
            'is_liked': request.user in reply.likes.all()
        } for reply in replies]
        
        return JsonResponse({
            'success': True,
            'discussion': {
                'id': discussion.id,
                'title': discussion.title,
                'content': discussion.content,
                'author': discussion.author.username,
                'created_at': discussion.created_at.isoformat(),
                'likes_count': discussion.likes_count,
                'is_liked': request.user in discussion.likes.all(),
                'replies': formatted_replies
            }
        })
    except Exception as e:
        logger.error(f"Error getting group discussion: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def identify_learning_style(request):
    """Identify user's learning style based on interaction data."""
    try:
        data = json.loads(request.body)
        interaction_data = data.get('interaction_data', [])
        
        if not interaction_data:
            return JsonResponse({
                'success': False,
                'error': 'No interaction data provided'
            })
        
        # Count occurrences of each learning style
        style_counts = {
            'visual': 0,
            'auditory': 0,
            'reading': 0,
            'kinesthetic': 0
        }
        
        for style in interaction_data:
            if style in style_counts:
                style_counts[style] += 1
        
        # Determine dominant learning style
        max_count = max(style_counts.values())
        dominant_styles = [style for style, count in style_counts.items() if count == max_count]
        
        # If multiple styles have the same count, consider it a mixed style
        learning_style = 'mixed' if len(dominant_styles) > 1 else dominant_styles[0]
        
        # Update or create student profile
        student_profile, created = StudentProfile.objects.get_or_create(
            user=request.user,
            defaults={'learning_style': learning_style}
        )
        
        if not created:
            student_profile.learning_style = learning_style
            student_profile.save()
        
        return JsonResponse({
            'success': True,
            'learning_style': learning_style,
            'style_counts': style_counts
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_POST
def provide_feedback(request):
    """Provide instant feedback on student responses."""
    try:
        data = json.loads(request.body)
        interaction_id = data.get('interaction_id')
        student_response = data.get('student_response')
        
        # Get the interaction
        interaction = get_object_or_404(Interaction, id=interaction_id, user=request.user)
        
        # Get student's learning style
        profile = request.user.ai_student_profile
        
        # Create feedback
        feedback = Feedback.objects.create(
            interaction=interaction,
            feedback_type=data.get('feedback_type', 'explanation'),
            content=data.get('content', '')
        )
        
        # Adapt feedback to learning style
        feedback.adapt_to_learning_style(profile.learning_style)
        
        # Update feedback effectiveness
        feedback.update_effectiveness(student_response)
        
        # Update progress record
        progress_record, created = ProgressRecord.objects.get_or_create(
            user=request.user,
            subject=interaction.subject,
            topic=interaction.topic
        )
        
        progress_record.update_progress({
            'score': student_response.get('score', 0),
            'time_spent': student_response.get('time_spent', 0),
            'visual_elements': feedback.visual_elements,
            'audio_elements': feedback.audio_elements,
            'text_elements': feedback.text_elements,
            'interactive_elements': feedback.interactive_elements,
            'visual_score': student_response.get('visual_score', 0),
            'audio_score': student_response.get('audio_score', 0),
            'text_score': student_response.get('text_score', 0),
            'interactive_score': student_response.get('interactive_score', 0),
            'response_time': student_response.get('response_time', 0),
            'error_rate': student_response.get('error_rate', 0)
        })
        
        return JsonResponse({
            'success': True,
            'feedback': {
                'content': feedback.content,
                'type': feedback.feedback_type,
                'effectiveness': {
                    'clarity': feedback.clarity_score,
                    'relevance': feedback.relevance_score
                }
            }
        })
    except Exception as e:
        logger.error(f"Error providing feedback: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def rate_feedback(request):
    """Rate the effectiveness of feedback."""
    try:
        data = json.loads(request.body)
        feedback_id = data.get('feedback_id')
        rating = data.get('rating')
        
        # Get the feedback
        feedback = get_object_or_404(Feedback, id=feedback_id, interaction__user=request.user)
        
        # Update feedback rating
        feedback.helpful = rating > 3
        feedback.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Feedback rating saved successfully'
        })
    except Exception as e:
        logger.error(f"Error rating feedback: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def create_learning_path(request):
    """Create a personalized learning path for the student."""
    try:
        data = json.loads(request.body)
        subject_id = data.get('subject_id')
        target_completion_date = data.get('target_completion_date')
        
        # Get the subject
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Get student's learning style
        profile = request.user.ai_student_profile
        
        # Create learning path
        learning_path = LearningPath.objects.create(
            user=request.user,
            title=f"Personalized {subject.name} Learning Path",
            description=f"Custom learning path for {subject.name} based on your learning style",
            subject=subject,
            status='active',
            start_date=timezone.now(),
            target_completion_date=target_completion_date,
            preferred_learning_style=profile.learning_style,
            difficulty_level=profile.difficulty_level
        )
        
        return JsonResponse({
            'success': True,
            'learning_path': {
                'id': learning_path.id,
                'title': learning_path.title,
                'description': learning_path.description,
                'status': learning_path.status,
                'progress': learning_path.progress_percentage,
                'target_completion_date': learning_path.target_completion_date
            }
        })
    except Exception as e:
        logger.error(f"Error creating learning path: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_GET
def get_learning_path(request, path_id):
    """Get details of a specific learning path."""
    try:
        learning_path = get_object_or_404(LearningPath, id=path_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'learning_path': {
                'id': learning_path.id,
                'title': learning_path.title,
                'description': learning_path.description,
                'status': learning_path.status,
                'progress': learning_path.progress_percentage,
                'current_topic': learning_path.current_topic,
                'completed_topics': learning_path.completed_topics,
                'total_topics': learning_path.total_topics,
                'average_score': learning_path.average_score,
                'time_spent': learning_path.time_spent,
                'completion_rate': learning_path.completion_rate,
                'target_completion_date': learning_path.target_completion_date
            }
        })
    except Exception as e:
        logger.error(f"Error getting learning path: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_GET
def get_dashboard(request):
    """Get student's progress dashboard."""
    try:
        # Get or create dashboard
        dashboard, created = Dashboard.objects.get_or_create(user=request.user)
        
        # Update dashboard metrics
        dashboard.update_metrics()
        
        # Get recommendations
        recommendations = dashboard.get_recommendations()
        
        # Get progress summary
        progress_summary = dashboard.get_progress_summary()
        
        return JsonResponse({
            'success': True,
            'dashboard': {
                'overall_progress': {
                    'total_study_time': dashboard.total_study_time,
                    'total_topics_completed': dashboard.total_topics_completed,
                    'average_score': dashboard.average_score,
                    'completion_rate': dashboard.completion_rate
                },
                'learning_style_effectiveness': {
                    'visual': dashboard.visual_effectiveness,
                    'auditory': dashboard.auditory_effectiveness,
                    'reading': dashboard.reading_effectiveness,
                    'kinesthetic': dashboard.kinesthetic_effectiveness
                },
                'performance_metrics': {
                    'current_streak': dashboard.current_streak,
                    'longest_streak': dashboard.longest_streak,
                    'last_activity': dashboard.last_activity,
                    'average_response_time': dashboard.average_response_time,
                    'error_rate': dashboard.error_rate
                },
                'achievements': {
                    'unlocked': dashboard.achievements_unlocked,
                    'total': dashboard.total_achievements,
                    'recent': dashboard.recent_achievements
                },
                'learning_paths': {
                    'active': dashboard.active_paths,
                    'completed': dashboard.completed_paths,
                    'current': dashboard.current_path
                },
                'recommendations': recommendations,
                'progress_summary': progress_summary
            }
        })
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def update_dashboard_metrics(request):
    """Update dashboard metrics based on recent activity."""
    try:
        data = json.loads(request.body)
        activity_data = data.get('activity_data', {})
        
        # Get dashboard
        dashboard = get_object_or_404(Dashboard, user=request.user)
        
        # Update metrics with new activity data
        dashboard.update_metrics(activity_data)
        
        return JsonResponse({
            'success': True,
            'message': 'Dashboard metrics updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating dashboard metrics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def learning_style_view(request):
    """Render the learning style identification page."""
    return render(request, 'ai/learning_style.html')

@login_required
def feedback_view(request):
    """Render the instant feedback page."""
    return render(request, 'ai/feedback.html')

@login_required
def learning_path_view(request):
    """Render the learning path page."""
    return render(request, 'ai/learning_path.html')

@login_required
def learning_path_details_view(request, path_id):
    """Render the learning path details page."""
    return render(request, 'ai/learning_path_details.html')

@login_required
def dashboard_view(request):
    """Render the student progress dashboard page."""
    return render(request, 'ai/dashboard.html')

@login_required
@require_POST
def generate_study_tasks(request, plan_id):
    """Generate study tasks using AI for a study plan."""
    try:
        study_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
        
        # Get AI provider
        ai_provider = get_ai_provider()
        
        # Prepare prompt for AI
        prompt = f"""You are a study planning AI. Create a detailed study plan for {study_plan.subject} with the following details:
        - Total hours: {study_plan.total_hours}
        - Subject: {study_plan.subject}
        - Description: {study_plan.description}
        
        Generate a list of specific study tasks. Each task should be:
        1. Actionable and measurable
        2. Have a clear objective
        3. Include estimated hours
        4. Be broken down into manageable chunks
        
        IMPORTANT: Your response must be a valid JSON array containing objects with these exact fields:
        - title: A clear, concise task title (string)
        - description: Detailed task description (string)
        - estimated_hours: Number of hours (float)
        
        The response should look exactly like this example (but with your own tasks):
        [
            {{
                "title": "Review Basic Concepts",
                "description": "Study and understand fundamental concepts X, Y, Z",
                "estimated_hours": 2.0
            }},
            {{
                "title": "Practice Problems",
                "description": "Solve practice problems from textbook chapters 1-3",
                "estimated_hours": 3.0
            }}
        ]
        
        Rules:
        1. The response must be valid JSON
        2. The total estimated_hours must sum to {study_plan.total_hours}
        3. Each task must have all three fields: title, description, and estimated_hours
        4. Do not include any text before or after the JSON array
        5. Do not include any markdown formatting
        6. Do not include any explanations or additional text"""
        
        # Get AI response
        context = {
            'subject': study_plan.subject,
            'preferences': {
                'format': 'json',
                'style': 'educational'
            }
        }
        
        response = ai_provider.generate_response(prompt, context)
        
        try:
            # Clean the response - remove any markdown or extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Parse the JSON response
            ai_response = json.loads(response)
            
            # Validate the response format
            if not isinstance(ai_response, list):
                raise ValueError("AI response is not a list")
            
            # Validate total hours
            total_hours = sum(float(task.get('estimated_hours', 0)) for task in ai_response)
            if abs(total_hours - study_plan.total_hours) > 0.1:  # Allow small rounding differences
                raise ValueError(f"Total hours ({total_hours}) does not match required hours ({study_plan.total_hours})")
            
            # Create tasks from AI response
            tasks = []
            for task_data in ai_response:
                # Validate required fields
                if not all(key in task_data for key in ['title', 'description', 'estimated_hours']):
                    logger.warning(f"Skipping invalid task data: {task_data}")
                    continue
                    
                task = StudyTask.objects.create(
                    study_plan=study_plan,
                    title=task_data['title'],
                    description=task_data['description'],
                    estimated_hours=float(task_data['estimated_hours'])
                )
                tasks.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'estimated_hours': task.estimated_hours,
                    'completed': task.completed
                })
            
            if not tasks:
                raise ValueError("No valid tasks were created")
            
            return JsonResponse({
                'success': True,
                'tasks': tasks
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}\nResponse: {response}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid AI response format',
                'details': str(e)
            }, status=500)
            
    except StudyPlan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study plan not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error generating study tasks: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def toggle_task_completion(request, task_id):
    """Toggle the completion status of a study task."""
    try:
        task = StudyTask.objects.get(id=task_id, study_plan__user=request.user)
        study_plan = task.study_plan
        
        # Toggle task completion
        task.completed = not task.completed
        task.save()
        
        # Calculate completed hours based on completed tasks
        completed_hours = sum(task.estimated_hours for task in study_plan.tasks.filter(completed=True))
        
        # Update study plan's completed hours and progress
        study_plan.completed_hours = completed_hours
        study_plan.progress = round((completed_hours / study_plan.total_hours * 100), 2) if study_plan.total_hours > 0 else 0
        study_plan.save()
        
        # Get updated task data
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'estimated_hours': task.estimated_hours,
            'completed': task.completed,
            'study_plan_progress': study_plan.progress
        }
        
        return JsonResponse({
            'success': True,
            'task': task_data
        })
        
    except StudyTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study task not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error toggling task completion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_study_tasks(request, plan_id):
    """Get all tasks for a study plan."""
    try:
        study_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
        tasks = study_plan.tasks.all()
        
        tasks_data = [{
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'estimated_hours': task.estimated_hours,
            'completed': task.completed
        } for task in tasks]
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data
        })
        
    except StudyPlan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study plan not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting study tasks: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
