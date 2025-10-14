# Live Counters Feature

This feature adds real-time live statistics and activity feed to the Alpha One Labs education platform homepage.

## Overview

The live counters feature displays dynamic statistics about platform activity and shows recent user achievements in real-time, creating a sense of engagement and community.

## Features

### 1. Live Statistics Counters
- **Students Learning Now**: Shows the number of students currently in active sessions
- **Active This Month**: Displays students who have enrolled in courses in the last 30 days
- **Quizzes Today**: Shows the total number of quizzes completed today

### 2. Activity Feed
- Displays recent activities like "john_doe from NY just completed a quiz!"
- Shows up to 10 most recent events
- Auto-updates every 30 seconds
- Includes human-readable timestamps (e.g., "2 minutes ago")

## Implementation Details

### Backend Components

#### 1. LiveActivityEvent Model (`web/models.py`)
```python
class LiveActivityEvent(models.Model):
    """Model for tracking live activity events like quiz completions, enrollments, etc."""
    
    EVENT_TYPES = [
        ("quiz_completed", "Quiz Completed"),
        ("enrollment", "Course Enrollment"),
        ("achievement", "Achievement Earned"),
    ]
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_events")
    message = models.CharField(max_length=255)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 2. API Endpoints (`web/views.py`)

**Live Stats API** (`/api/live-stats/`)
- Returns JSON with current statistics

**Activity Feed API** (`/api/live-activity-feed/`)
- Returns JSON with last 10 activity events

#### 3. Quiz Completion Hook
Updated `UserQuiz.complete_quiz()` method to automatically create a LiveActivityEvent when a user completes a quiz.

### Frontend Components

#### 1. Live Counters Section (`web/templates/index.html`)
- Three counter cards with icons
- Gradient background for visual appeal
- Activity feed with scrollable list
- Responsive grid layout (1 column on mobile, 3 columns on desktop)

#### 2. JavaScript
- Fetches live stats every 30 seconds
- Fetches activity feed every 30 seconds
- Smooth counter animations
- Human-readable time formatting

## Testing

Test file: `tests/test_live_counters.py`

Test coverage includes:
- Live stats API returns correct data
- Activity feed API returns correct data
- Quiz completion creates activity event
- LiveActivityEvent model creation
- Anonymous quiz completion doesn't create event

## Code Quality

All code passes:
- ✅ Black formatting (120 char line length)
- ✅ isort import sorting
- ✅ flake8 linting
- ✅ djlint template formatting
