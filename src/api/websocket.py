from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.last_update: Dict = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Send initial data
        if self.last_update:
            await websocket.send_json(self.last_update)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        self.last_update = message
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)
                
    async def broadcast_token_update(self, token_data: Dict):
        """Broadcast token update to all connected clients"""
        message = {
            "type": "token_update",
            "data": token_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        
    async def broadcast_pattern_alert(self, pattern_data: Dict):
        """Broadcast pattern detection alert"""
        message = {
            "type": "pattern_alert",
            "data": pattern_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)

websocket_manager = WebSocketManager() 