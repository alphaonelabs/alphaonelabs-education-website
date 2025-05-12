import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from .models import ClassroomGameState, ChairOccupancy


@login_required
def virtual_classroom(request):
    """
    Render the virtual classroom template with the game state for the current user.
    """
    # Get classroom session ID (optional, for multiple classroom instances)
    session_id = request.GET.get('session_id', 'default')
    
    # Get player's game state from database, or create new if doesn't exist
    player_state, created = ClassroomGameState.objects.get_or_create(
        user=request.user,
        session_id=session_id,
    )
    
    # Get chair occupancy data for this classroom session
    chairs = ChairOccupancy.objects.filter(session_id=session_id)
    chair_data = {}
    
    for chair in chairs:
        if chair.user:
            chair_data[chair.chair_id] = {
                'userId': chair.user.id,
                'username': chair.user.username,
                'avatar': chair.user.profile.avatar_url if hasattr(chair.user, 'profile') and hasattr(chair.user.profile, 'avatar_url') else None
            }
    
    # Create game state to send to the template
    game_state = {
        'player_position': {
            'x': player_state.position_x,
            'y': player_state.position_y
        },
        'chairs_occupancy': chair_data
    }
    
    # Convert to JSON for template
    game_state_json = json.dumps(game_state)
    
    return render(request, 'classroom.html', {
        'game_state': game_state_json,
        'user': request.user
    })


@login_required
@require_POST
def save_classroom_state(request):
    """
    API endpoint to save the player's position and game state.
    """
    try:
        data = json.loads(request.body)
        state, created = ClassroomGameState.objects.update_or_create(
            user=request.user,
            defaults={
                'position_x': data['position']['x'],
                'position_y': data['position']['y']
            }
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def update_chair_state(request):
    """
    API endpoint to update chair occupancy status.
    """
    try:
        data = json.loads(request.body)
        chair_id = data['chairId']
        
        # If user is sitting down
        if data.get('sitting'):
            # Remove user from any other chairs
            ChairOccupancy.objects.filter(user=request.user).delete()
            # Assign user to new chair
            ChairOccupancy.objects.create(
                chair_id=chair_id,
                user=request.user
            )
        else:
            # User is standing up
            ChairOccupancy.objects.filter(
                chair_id=chair_id,
                user=request.user
            ).delete()
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400) 