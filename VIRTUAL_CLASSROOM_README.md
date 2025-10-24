# Virtual Classroom Feature

## Overview

The Virtual Classroom is an interactive, real-time online learning environment that simulates a physical classroom. Students can select seats, interact with each other through avatars, raise hands, and share content. Teachers control the flow of the class, initiate timed student updates, and interact with student-submitted content in real-time.

## Features

### 1. Virtual Seating Chart
- **Grid-style classroom layout** rendered on the page
- **Available seats** are shown as clickable
- When a student selects a seat:
  - Their avatar appears in that spot
  - Seat is marked as "occupied" for other users
  - Seat selections are persisted in the backend

### 2. Avatars & Roles
- Each student has a basic avatar displayed in their seat
- Teacher avatar is fixed in the front center of the class
- Teacher's view includes full control features
- Student view is limited to personal actions

### 3. Raise Hand & Speaking Queue
- Students can click a "Raise Hand" button
- A hand icon (✋) appears above their avatar
- Teacher sees a queue of raised hands in the sidebar
- Teacher can "select" a student to speak
- Selected student's seat highlights with animation
- Student receives notification to begin speaking

### 4. Mini Virtual Laptop per Seat
- Each occupied desk has a virtual laptop icon (💻)
- Clicking the laptop opens a modal for:
  - **Upload Screenshot**: Students can upload screenshots via Django forms + HTMX
  - **Share Screen**: Upload static preview/screenshot
- Teacher can click on a student's laptop to view uploads

### 5. Timed Update Rounds
- Teacher starts an "Update Round" with configurable duration (default: 2 minutes)
- System automatically selects students in random order
- Timer counts down visibly on the current speaker's area
- Student clicks "Done" when finished
- System automatically selects the next random student who hasn't spoken
- Continues until all students have shared

### 6. Real-Time Feedback & State Updates
- All interactions update via **WebSockets** for live changes
- Non-blocking, real-time updates for smooth experience
- Seat selection, hand raising, and speaking turns are synchronized across all clients

## Technical Architecture

### Backend Components

#### Models (`web/models.py`)
- **VirtualClassroom**: Stores classroom session info, grid dimensions, teacher, and active status
- **ClassroomSeat**: Individual seats with position (row, column), student assignment, and speaking status
- **RaisedHand**: Queue management for raised hands with timestamps
- **UpdateRound**: Manages timed update rounds with timer settings and current speaker
- **UpdateRoundParticipant**: Tracks participants and their speaking order in update rounds
- **ScreenShare**: Stores uploaded screenshots and shared content

#### Views (`web/virtual_classroom_views.py`)
- `virtual_classroom_list`: List all virtual classrooms
- `create_virtual_classroom`: Create new classroom (teachers only)
- `virtual_classroom_detail`: Main classroom interface
- `upload_screenshot`: Handle screenshot uploads via HTMX
- `view_screenshot`: View screenshot details
- `end_classroom`: Deactivate classroom (teachers only)

#### WebSocket Consumer (`web/consumers.py`)
- **VirtualClassroomConsumer**: Handles real-time WebSocket connections
  - Seat selection
  - Hand raising/lowering
  - Speaker selection
  - Update round management
  - Timer synchronization

#### Routing (`web/routing.py`)
- WebSocket URL patterns for classroom connections
- Connected to Django Channels

### Frontend Components

#### Templates
- **classroom_list.html**: Browse available classrooms
- **create_classroom.html**: Form to create new classroom with preview
- **classroom_detail.html**: Main classroom interface with:
  - Seating grid
  - Teacher position
  - Raised hands sidebar
  - Update round timer
  - Screenshot upload modal
  - Real-time WebSocket integration
- **screenshot_detail.html**: View uploaded screenshots
- **Partials**: HTMX partials for dynamic updates

#### JavaScript/WebSocket
- Real-time WebSocket connection to classroom
- Event handlers for:
  - Seat selection
  - Hand raising/lowering
  - Screenshot uploads
  - Timer countdown
  - UI updates based on server events

### Technologies Used

- **Django 5.x**: Backend framework
- **Django Channels**: WebSocket support
- **Redis**: Channel layer backend for WebSockets
- **HTMX**: Partial page updates (screenshot uploads)
- **Tailwind CSS**: Styling with dark mode support
- **Alpine.js**: Client-side interactivity (optional)
- **WebSocket API**: Real-time bidirectional communication

## Setup Instructions

### Prerequisites
- Django 5.x
- Django Channels
- Redis server running
- channels-redis

### Installation

1. **Ensure dependencies are installed** (already in `pyproject.toml`):
   ```toml
   channels = "^4.3.1"
   channels-redis = "^4.3.0"
   redis = "^6.4.0"
   ```

2. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Configure Redis** in `.env`:
   ```
   REDIS_URL=redis://127.0.0.1:6379/0
   ```

4. **Start Redis server**:
   ```bash
   redis-server
   ```

5. **Run the development server** with ASGI support:
   ```bash
   uvicorn web.asgi:application --reload
   ```
   or
   ```bash
   daphne -b 0.0.0.0 -p 8000 web.asgi:application
   ```

## Usage

### For Teachers

1. **Create a Classroom**:
   - Navigate to `/virtual-classrooms/`
   - Click "Create Classroom"
   - Set title, rows, and columns
   - Optionally link to a session
   - Click "Create Classroom"

2. **Manage Classroom**:
   - View all seated students
   - See raised hands in the sidebar
   - Click "Select" on a raised hand to give student permission to speak
   - Start update rounds with custom duration
   - View student screen shares
   - End classroom when done

3. **Start Update Round**:
   - Click "Start Update Round"
   - Set duration per student (seconds)
   - System randomly selects students
   - Timer counts down for each speaker
   - Round completes when all students have spoken

### For Students

1. **Join a Classroom**:
   - Navigate to `/virtual-classrooms/`
   - Click "Enter Classroom" on an active classroom

2. **Select a Seat**:
   - Click on any empty seat (gray)
   - Your avatar will appear in that seat
   - Seat becomes unavailable to others

3. **Raise Your Hand**:
   - Click "✋ Raise Hand" button
   - Hand icon appears above your seat
   - Wait for teacher to select you
   - When selected, your seat will highlight

4. **Upload Screenshot**:
   - Click "📸 Upload Screenshot"
   - Fill in optional title and description
   - Select image file
   - Click "Upload"

5. **Participate in Update Round**:
   - When it's your turn, timer appears
   - Share your update
   - Click "I'm Done" when finished
   - Next student is automatically selected

## URL Patterns

- `/virtual-classrooms/` - List all classrooms
- `/virtual-classrooms/create/` - Create new classroom (teachers only)
- `/virtual-classrooms/<id>/` - Classroom detail view
- `/virtual-classrooms/<id>/upload-screenshot/` - Upload screenshot
- `/virtual-classrooms/screenshot/<id>/` - View screenshot
- `/virtual-classrooms/<id>/end/` - End classroom (teachers only)
- `ws://localhost:8000/ws/classroom/<id>/` - WebSocket connection

## WebSocket Message Types

### Client → Server
- `select_seat`: Select a seat (row, column)
- `raise_hand`: Raise hand
- `lower_hand`: Lower hand
- `select_speaker`: Teacher selects speaker (student_id)
- `start_update_round`: Start update round (duration)
- `next_speaker`: Move to next speaker (round_id)
- `complete_speaking`: Student completes turn (round_id)

### Server → Client
- `classroom_state`: Initial classroom state
- `seat_update`: Seat assignment changed
- `hand_raised`: Student raised hand
- `hand_lowered`: Student lowered hand
- `speaker_selected`: Teacher selected speaker
- `update_round_started`: Update round started
- `next_speaker_update`: Next speaker in round
- `error`: Error message

## Database Schema

### VirtualClassroom
- `id`: Primary key
- `title`: Classroom name
- `teacher`: Foreign key to User
- `session`: Optional foreign key to Session
- `rows`: Number of seat rows
- `columns`: Number of seat columns
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

### ClassroomSeat
- `id`: Primary key
- `classroom`: Foreign key to VirtualClassroom
- `row`, `column`: Position in grid
- `student`: Optional foreign key to User
- `is_occupied`: Occupation status
- `is_speaking`: Speaking status
- `created_at`, `updated_at`: Timestamps
- **Unique together**: (classroom, row, column)

### RaisedHand
- `id`: Primary key
- `classroom`: Foreign key to VirtualClassroom
- `student`: Foreign key to User
- `seat`: Foreign key to ClassroomSeat
- `is_active`: Active status
- `selected_at`: When teacher selected
- `created_at`: Timestamp

### UpdateRound
- `id`: Primary key
- `classroom`: Foreign key to VirtualClassroom
- `title`: Round title
- `duration_seconds`: Duration per speaker
- `current_speaker`: Optional foreign key to User
- `is_active`: Active status
- `started_at`, `completed_at`: Timestamps
- `created_at`: Timestamp

### UpdateRoundParticipant
- `id`: Primary key
- `update_round`: Foreign key to UpdateRound
- `student`: Foreign key to User
- `has_spoken`: Spoken status
- `spoken_at`: When spoke
- `order`: Speaking order
- **Unique together**: (update_round, student)

### ScreenShare
- `id`: Primary key
- `classroom`: Foreign key to VirtualClassroom
- `student`: Foreign key to User
- `seat`: Foreign key to ClassroomSeat
- `title`: Optional title
- `screenshot`: Image file
- `description`: Optional description
- `is_visible_to_teacher`: Visibility flag
- `created_at`: Timestamp

## Admin Interface

All models are registered in the Django admin interface at `/admin/`:

- VirtualClassroom management
- Seat assignments
- Raised hands queue
- Update rounds and participants
- Screen shares

## Testing

Run tests with:
```bash
python manage.py test tests.test_virtual_classroom
```

Test coverage includes:
- Model creation and relationships
- Seat assignment logic
- View permissions (teacher vs student)
- Classroom lifecycle (create, use, end)
- Authentication requirements

## Future Enhancements

- [ ] Voice/video chat integration
- [ ] Whiteboard functionality
- [ ] Breakout rooms
- [ ] Attendance tracking
- [ ] Session recording
- [ ] Chat functionality
- [ ] Emoji reactions
- [ ] Custom avatar creation
- [ ] Mobile responsive improvements
- [ ] Accessibility enhancements

## Troubleshooting

### WebSocket Connection Issues
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check REDIS_URL in settings
- Verify ASGI server is running (not WSGI)

### Seats Not Updating
- Check browser console for WebSocket errors
- Verify JavaScript is enabled
- Check network tab for WebSocket connection

### Permissions Issues
- Ensure user has Profile created
- Check `is_teacher` flag on Profile
- Verify user is authenticated

## Contributing

When contributing to the virtual classroom feature:

1. Follow the existing code style (Black, isort, flake8)
2. Run pre-commit hooks before committing
3. Add tests for new functionality
4. Update documentation
5. Test WebSocket functionality manually

## License

This feature is part of the Alpha One Labs Education Platform and follows the same license.
