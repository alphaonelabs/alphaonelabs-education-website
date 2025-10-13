"""Views for virtual lobby functionality."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from .models import VirtualLobby, LobbyParticipant


@login_required
def lobby_list(request):
    """Display list of available virtual lobbies."""
    lobbies = VirtualLobby.objects.filter(is_active=True).order_by('-created_at')
    
    # Add online count for each lobby
    lobbies = VirtualLobby.objects.filter(is_active=True).annotate(
        online_count=Count('participants', filter=Q(participants__is_online=True))
    ).order_by('-created_at')
    
    context = {
        'lobbies': lobbies,
        'user_participations': LobbyParticipant.objects.filter(
            user=request.user,
            is_online=True
        ).select_related('lobby')
    }
    
    return render(request, 'lobby/lobby_list.html', context)


@login_required
def lobby_detail(request, lobby_id):
    """Display virtual lobby interface."""
    lobby = get_object_or_404(VirtualLobby, id=lobby_id, is_active=True)
    
    # Check if user can join the lobby
    can_join, message = lobby.can_user_join(request.user)
    if not can_join:
        messages.error(request, message)
        return redirect('lobby_list')
    
    # Get or create participant
    participant, created = LobbyParticipant.objects.get_or_create(
        user=request.user,
        lobby=lobby,
        defaults={
            'position_x': 100.0,
            'position_y': 100.0,
            'display_name': request.user.username,
            'is_online': True
        }
    )
    
    # Mark as online
    participant.mark_online()
    
    # Get other online participants
    online_participants = lobby.get_online_participants().exclude(user=request.user)
    
    context = {
        'lobby': lobby,
        'participant': participant,
        'online_participants': online_participants,
        'websocket_url': f'ws://{request.get_host()}/ws/lobby/{lobby.id}/'
    }
    
    return render(request, 'lobby/lobby_detail.html', context)


@login_required
def leave_lobby(request, lobby_id):
    """Leave a virtual lobby."""
    try:
        participant = LobbyParticipant.objects.get(
            user=request.user,
            lobby_id=lobby_id
        )
        lobby_name = participant.lobby.name
        participant.mark_offline()
        messages.success(request, f"You have left {lobby_name}")
    except LobbyParticipant.DoesNotExist:
        # User might not be in the lobby, but that's okay
        messages.info(request, "You are no longer in this lobby")
    
    return redirect('lobby_list')


@login_required
@require_http_methods(["POST"])
def create_lobby(request):
    """Create a new virtual lobby."""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    max_users = int(request.POST.get('max_users', 100))
    is_public = request.POST.get('is_public') == 'on'
    
    if not name:
        messages.error(request, "Lobby name is required")
        return redirect('lobby_list')
    
    try:
        with transaction.atomic():
            lobby = VirtualLobby.objects.create(
                name=name,
                description=description,
                max_users=max_users,
                is_public=is_public,
                created_by=request.user
            )
            
            # Create participant for the creator
            LobbyParticipant.objects.create(
                user=request.user,
                lobby=lobby,
                position_x=100.0,
                position_y=100.0,
                display_name=request.user.username,
                is_online=True
            )
            
            messages.success(request, f"Lobby '{lobby.name}' created successfully!")
            return redirect('lobby_detail', lobby_id=lobby.id)
            
    except Exception as e:
        messages.error(request, f"Error creating lobby: {str(e)}")
        return redirect('lobby_list')


@login_required
@require_http_methods(["POST"])
def update_participant_settings(request, lobby_id):
    """Update participant settings like display name and avatar."""
    participant = get_object_or_404(
        LobbyParticipant,
        user=request.user,
        lobby_id=lobby_id
    )
    
    display_name = request.POST.get('display_name', '').strip()
    avatar_color = request.POST.get('avatar_color', '#3B82F6')
    
    if display_name:
        participant.display_name = display_name
    
    participant.avatar_color = avatar_color
    participant.save()
    
    return JsonResponse({
        'success': True,
        'display_name': participant.get_display_name(),
        'avatar_color': participant.avatar_color
    })


@login_required
def lobby_participants_api(request, lobby_id):
    """API endpoint to get lobby participants."""
    lobby = get_object_or_404(VirtualLobby, id=lobby_id)
    participants = lobby.get_online_participants().select_related('user')
    
    participants_data = []
    for participant in participants:
        participants_data.append({
            'user_id': participant.user.id,
            'username': participant.user.username,
            'display_name': participant.get_display_name(),
            'position_x': participant.position_x,
            'position_y': participant.position_y,
            'avatar_color': participant.avatar_color,
            'is_online': participant.is_online,
            'last_activity': participant.last_activity.isoformat()
        })
    
    return JsonResponse({
        'participants': participants_data,
        'lobby': {
            'id': lobby.id,
            'name': lobby.name,
            'online_count': len(participants_data),
            'max_users': lobby.max_users
        }
    })


@login_required
def lobby_stats(request):
    """Get lobby statistics for dashboard."""
    total_lobbies = VirtualLobby.objects.filter(is_active=True).count()
    total_online_users = LobbyParticipant.objects.filter(is_online=True).count()
    
    # Get user's lobby participation
    user_participations = LobbyParticipant.objects.filter(
        user=request.user,
        is_online=True
    ).select_related('lobby')
    
    return JsonResponse({
        'total_lobbies': total_lobbies,
        'total_online_users': total_online_users,
        'user_lobbies': [
            {
                'id': p.lobby.id,
                'name': p.lobby.name,
                'online_count': p.lobby_online_count
            }
            for p in user_participations
        ]
    })
