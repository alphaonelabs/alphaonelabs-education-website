# Virtual Lobby - Quick Start Guide

## What is the Virtual Lobby?

The Virtual Lobby is a real-time collaborative space where all users can:
- 👥 See other active users
- 🗨️ Chat with everyone
- 🎨 Move around in a visual space
- 🔄 Experience real-time updates

## How to Access

1. **Login** to your account
2. **Navigate** to the Virtual Lobby:
   - Click "Virtual Lobby" in the main navigation
   - Or visit `/lobby/` directly

## Features at a Glance

### 📊 Dashboard Stats
- **Active Users**: See how many people are online
- **Your Status**: Connection status (Connected/Disconnected)
- **Messages**: Total chat messages in current session

### 🎮 Interactive Canvas
- **See Everyone**: All users displayed as colored avatars with initials
- **Move Around**: Click and drag to move your avatar
- **Real-time**: Watch others move in real-time
- **Visual Grid**: Background grid for orientation

### 👥 Participants List
- Shows all active users (within last 5 minutes)
- Display names and usernames
- Your avatar is highlighted

### 💬 Chat System
- Send messages to everyone in the lobby
- See system notifications (joins/leaves)
- Message history during your session
- Real-time message delivery

## Quick Actions

### Join the Lobby
```
Simply visit /lobby/ - you're automatically connected!
```

### Move Your Avatar
```
1. Click on the canvas
2. Hold and drag to desired position
3. Release to confirm position
4. Everyone sees your new position instantly
```

### Send a Chat Message
```
1. Type your message in the chat box
2. Press Enter or click "Send"
3. Message appears for everyone immediately
```

### Leave the Lobby
```
Simply navigate away or close the tab
You'll be automatically removed from the participant list
```

## WebSocket Connection

The lobby uses WebSocket for real-time features:
- Automatic connection on page load
- Auto-reconnect if connection drops
- Status indicator shows connection state
- Max 5 reconnection attempts

## User Experience

### First Visit
1. Page loads with lobby interface
2. WebSocket connects automatically
3. You see current active participants
4. You can start moving and chatting immediately

### During Session
- Your position updates as you drag
- Chat messages appear instantly
- You see when others join/leave
- System messages keep you informed

### When Leaving
- Your participation is automatically removed
- Others are notified you left
- No manual "logout" needed

## Browser Requirements

Works best on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires:
- JavaScript enabled
- WebSocket support
- Canvas support

## Keyboard Shortcuts

- **Enter** in chat: Send message
- **Escape**: Clear chat input
- **Mouse drag**: Move avatar

## Tips & Tricks

1. **Finding People**: Look at the participant list to see who's online
2. **Greeting**: Send a chat message when you join
3. **Moving**: Drag smoothly for best experience
4. **Reconnecting**: If disconnected, page will auto-reconnect
5. **Capacity**: Lobbies have max capacity (default 100)

## Common Issues

### Can't Connect?
- Check internet connection
- Ensure JavaScript is enabled
- Refresh the page
- Check browser console for errors

### Can't Move?
- Make sure you're clicking on the canvas
- Try clicking and holding before dragging
- Refresh if avatar doesn't appear

### Can't Chat?
- Ensure WebSocket is connected (check status)
- Try refreshing the page
- Check if message box is active

### Others Not Showing?
- They might have left (inactive > 5 min)
- Refresh to update participant list
- Check WebSocket connection

## Admin Features

Admins can:
- Create multiple lobbies
- Set capacity limits
- Enable/disable lobbies
- View all participants
- Monitor activity

Access admin at `/admin/` → Virtual Lobbies

## Security

- Login required for access
- WebSocket authenticated
- Capacity limits enforced
- Chat messages sanitized
- CSRF protection enabled

## Mobile Support

The lobby works on mobile with:
- Responsive design
- Touch-friendly controls
- Stacked layout on small screens
- Optimized chat interface

## What's Next?

Future enhancements may include:
- Video/audio chat
- Private rooms
- User profiles
- Custom avatars
- Themes
- And more!

## Need Help?

- Check documentation: `docs/VIRTUAL_LOBBY.md`
- View UI guide: `docs/VIRTUAL_LOBBY_UI.md`
- Read implementation: `IMPLEMENTATION_SUMMARY.md`
- Contact support or create an issue

---

**Enjoy connecting with other learners in the Virtual Lobby! 🎉**
