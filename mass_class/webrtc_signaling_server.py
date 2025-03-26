from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
from typing import Dict, List
import json

# Set up basic logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        # Dictionary that maps room identifiers to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        logging.info(f"Client connected to room '{room}'. Total connections: {len(self.active_connections[room])}")

    def disconnect(self, room: str, websocket: WebSocket):
        if room in self.active_connections:
            self.active_connections[room].remove(websocket)
            logging.info(f"Client disconnected from room '{room}'. Remaining connections: {len(self.active_connections[room])}")
            if not self.active_connections[room]:
                del self.active_connections[room]

    async def broadcast(self, room: str, message: str, sender: WebSocket):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                if connection is not sender:
                    await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(room, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Message received in room '{room}': {data}")
            await manager.broadcast(room, data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
        logging.info(f"WebSocket disconnected from room '{room}'")

if __name__ == "__main__":
    uvicorn.run("mass_class.webrtc_signaling_server:app", host="0.0.0.0", port=8000, reload=True)