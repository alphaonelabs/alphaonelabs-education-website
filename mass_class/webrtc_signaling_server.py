from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
from typing import Dict, List
import json

# Create the FastAPI app instance
app = FastAPI()

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc_signaling_server")

class ConnectionManager:
    def __init__(self):
        # Map room identifier to list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        logger.info(f"New connection in room '{room}'. Total connections: {len(self.active_connections[room])}")

    def disconnect(self, room: str, websocket: WebSocket):
        if room in self.active_connections:
            self.active_connections[room].remove(websocket)
            logger.info(f"Disconnected from room '{room}'. Total connections: {len(self.active_connections[room])}")

    async def broadcast(self, room: str, message: str, sender: WebSocket):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                # Skip sending the message to the sender
                if connection != sender:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        logger.error(f"Error sending message in room '{room}': {e}")

# Initialize the connection manager instance
manager = ConnectionManager()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(room, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message in room '{room}': {data}")
            await manager.broadcast(room, data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
        logger.info(f"WebSocket disconnected from room '{room}'")
    except Exception as e:
        logger.error(f"Unexpected error in room '{room}': {e}")
        manager.disconnect(room, websocket)

if __name__ == "__main__":
    uvicorn.run("mass_class.webrtc_signaling_server:app", host="0.0.0.0", port=8000, reload=True)