# Virtual Classroom Quick Reference

## 🚀 Quick Start (Development)

```bash
# 1. Start Redis
redis-server

# 2. Run migrations
python manage.py migrate

# 3. Create a teacher account (or make existing user a teacher)
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from web.models import Profile
>>> user = User.objects.get(username='your_username')
>>> profile = user.profile
>>> profile.is_teacher = True
>>> profile.save()
>>> exit()

# 4. Start the server with ASGI
uvicorn web.asgi:application --reload --host 0.0.0.0 --port 8000

# 5. Visit http://localhost:8000/virtual-classrooms/
```

## 📱 User Flows

### Teacher Flow (5 steps)
1. **Create Classroom**: `/virtual-classrooms/create/` → Set title, rows, columns
2. **Share Link**: Give students the classroom URL
3. **Monitor Activity**: See students join, raise hands, upload screenshots
4. **Manage Speaking**: Click "Select" on raised hands to give permission
5. **Run Update Round**: Click "Start Update Round" → Set timer → System auto-rotates speakers

### Student Flow (4 steps)
1. **Browse Classrooms**: `/virtual-classrooms/` → Find active classroom
2. **Select Seat**: Click empty seat → Your avatar appears
3. **Interact**: 
   - Raise hand with "✋ Raise Hand" button
   - Upload screenshot with "📸 Upload Screenshot" button
4. **Participate**: When it's your turn in update round, share and click "I'm Done"

## 🎨 UI Elements Guide

### Seat States
- **Empty (Gray)**: Available, click to sit
- **Occupied (Teal)**: Student seated, shows username
- **Speaking (Yellow, Pulsing)**: Currently has the floor
- **Hand Raised (✋)**: Student requesting to speak

### Buttons
- **✋ Raise Hand**: Request permission to speak
- **📸 Upload Screenshot**: Share your screen/work
- **💻 Laptop Icon**: View student's uploads (teacher only)
- **Select**: Give student permission to speak (teacher only)
- **I'm Done**: Complete your speaking turn
- **Start Update Round**: Begin timed speaking round (teacher only)
- **End Classroom**: Deactivate classroom (teacher only)

## 🔌 WebSocket Events Reference

### Client → Server
```javascript
// Select a seat
ws.send(JSON.stringify({
    type: 'select_seat',
    row: 2,
    column: 3
}));

// Raise hand
ws.send(JSON.stringify({
    type: 'raise_hand'
}));

// Lower hand
ws.send(JSON.stringify({
    type: 'lower_hand'
}));

// Teacher: Select speaker
ws.send(JSON.stringify({
    type: 'select_speaker',
    student_id: 123
}));

// Teacher: Start update round
ws.send(JSON.stringify({
    type: 'start_update_round',
    duration: 120  // seconds
}));

// Student: Complete speaking
ws.send(JSON.stringify({
    type: 'complete_speaking',
    round_id: 456
}));
```

### Server → Client
```javascript
ws.onmessage = function(e) {
    const message = JSON.parse(e.data);
    
    switch(message.type) {
        case 'classroom_state':
            // Initial state when connecting
            // Contains: seats, raised_hands, active_round
            break;
            
        case 'seat_update':
            // Someone selected a seat
            // Contains: row, column, student, student_id, is_occupied
            break;
            
        case 'hand_raised':
            // Student raised hand
            // Contains: student, student_id, seat_id, timestamp
            break;
            
        case 'hand_lowered':
            // Student lowered hand
            // Contains: student, student_id
            break;
            
        case 'speaker_selected':
            // Teacher selected speaker
            // Contains: student_id, student
            break;
            
        case 'update_round_started':
            // Update round began
            // Contains: round_id, duration, current_speaker_id, current_speaker
            break;
            
        case 'next_speaker_update':
            // Next speaker's turn
            // Contains: round_id, current_speaker_id, current_speaker, is_complete
            break;
            
        case 'error':
            // Something went wrong
            // Contains: message
            break;
    }
};
```

## 🗄️ Database Quick Reference

### Get Active Classrooms
```python
VirtualClassroom.objects.filter(is_active=True)
```

### Get Classroom with Seats
```python
classroom = VirtualClassroom.objects.get(id=1)
seats = classroom.seats.all().order_by('row', 'column')
```

### Get Raised Hands
```python
raised_hands = RaisedHand.objects.filter(
    classroom=classroom,
    is_active=True
).order_by('created_at')
```

### Get Active Update Round
```python
active_round = UpdateRound.objects.filter(
    classroom=classroom,
    is_active=True
).first()
```

### Get Student's Seat
```python
seat = ClassroomSeat.objects.filter(
    classroom=classroom,
    student=user
).first()
```

## 🛠️ Common Admin Tasks

### Make User a Teacher
```python
# In Django shell or admin
user.profile.is_teacher = True
user.profile.save()
```

### Clear All Seats in Classroom
```python
ClassroomSeat.objects.filter(classroom=classroom).update(
    student=None,
    is_occupied=False,
    is_speaking=False
)
```

### End All Active Update Rounds
```python
from django.utils import timezone
UpdateRound.objects.filter(is_active=True).update(
    is_active=False,
    completed_at=timezone.now()
)
```

### View Screenshot Uploads
```python
screenshots = ScreenShare.objects.filter(
    classroom=classroom
).order_by('-created_at')
```

## 🐛 Troubleshooting

### WebSocket Not Connecting
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check ASGI server is running (not WSGI)
# Should see: uvicorn or daphne in process list
ps aux | grep -E "uvicorn|daphne"

# Check browser console for errors
# F12 → Console → Look for WebSocket errors
```

### Seats Not Updating
```javascript
// In browser console, check WebSocket status
console.log(ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
```

### Can't Create Classroom
```python
# Make sure user is a teacher
user = User.objects.get(username='your_username')
user.profile.is_teacher
# Should return: True
```

### Timer Not Syncing
```bash
# Ensure only one browser tab is connected
# Multiple tabs can cause timer conflicts

# Check server logs for WebSocket errors
# Look for: "WebSocket connected" messages
```

## 📊 Performance Tips

### For Best Performance
1. **Limit concurrent classrooms**: 10-20 active classrooms per server
2. **Optimize Redis**: Use Redis with persistence enabled
3. **Clean up old data**: Regularly archive ended classrooms
4. **Monitor connections**: Watch WebSocket connection count
5. **Use CDN**: Serve static assets from CDN in production

### Recommended Server Specs
- **Development**: 2 CPU cores, 4GB RAM, Redis 6.x
- **Production (50 users)**: 4 CPU cores, 8GB RAM, Redis cluster
- **Production (200 users)**: 8 CPU cores, 16GB RAM, Redis cluster + Load balancer

## 🔐 Security Checklist

- [ ] Redis has password authentication in production
- [ ] WebSocket uses WSS (not WS) in production
- [ ] File upload size limits configured
- [ ] CSRF protection enabled
- [ ] Rate limiting on screenshot uploads
- [ ] User authentication required for all endpoints
- [ ] Teacher permissions verified before classroom creation

## 📞 Support

- **Documentation**: See VIRTUAL_CLASSROOM_README.md
- **Implementation Details**: See IMPLEMENTATION_SUMMARY.md
- **Code Issues**: Check GitHub Issues
- **WebSocket Debugging**: Use browser DevTools → Network → WS

## 🎓 Learning Resources

- [Django Channels Tutorial](https://channels.readthedocs.io/en/stable/tutorial/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Redis Quick Start](https://redis.io/topics/quickstart)
- [HTMX Documentation](https://htmx.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)

---

**Need Help?** Check the full documentation in VIRTUAL_CLASSROOM_README.md or open a GitHub issue.
