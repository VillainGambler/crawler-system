from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Maps Character ID to a list of active connections
        # Example: {"carl_001": [socket1, socket2], "donut_001": [socket3]}
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, character_id: str):
        await websocket.accept()
        if character_id not in self.active_connections:
            self.active_connections[character_id] = []
        self.active_connections[character_id].append(websocket)
        print(f"DEBUG: Client connected to {character_id}. Total: {len(self.active_connections[character_id])}")

    def disconnect(self, websocket: WebSocket, character_id: str):
        if character_id in self.active_connections:
            if websocket in self.active_connections[character_id]:
                self.active_connections[character_id].remove(websocket)
            if not self.active_connections[character_id]:
                del self.active_connections[character_id]
        print(f"DEBUG: Client disconnected from {character_id}.")

    async def broadcast(self, character_id: str, message: dict):
        """
        Send a message to everyone looking at this specific character.
        """
        if character_id in self.active_connections:
            for connection in self.active_connections[character_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting: {e}")
                    # Usually means client closed connection abruptly
                    pass