"""WebSocket support for real-time build progress."""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from .domain import State

logger = logging.getLogger("api.websocket")


class ProgressManager:
    """Manages WebSocket connections and broadcasts build progress."""
    
    def __init__(self):
        # slug -> set of WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, slug: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if slug not in self.connections:
                self.connections[slug] = set()
            self.connections[slug].add(websocket)
        logger.info(f"WebSocket connected for slug: {slug} (total: {len(self.connections[slug])})")
    
    def disconnect(self, slug: str, websocket: WebSocket):
        if slug in self.connections:
            self.connections[slug].discard(websocket)
            if not self.connections[slug]:
                del self.connections[slug]
        logger.info(f"WebSocket disconnected for slug: {slug}")
    
    async def broadcast(self, slug: str, message: dict):
        """Broadcast a message to all connections for a slug."""
        if slug not in self.connections:
            return
        
        dead = set()
        for ws in self.connections[slug]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        
        # Clean up dead connections
        for ws in dead:
            self.disconnect(slug, ws)
    
    async def send_progress(self, slug: str, state: State, progress: int, message: str, details: dict = None):
        """Send a structured progress update."""
        await self.broadcast(slug, {
            "type": "progress",
            "slug": slug,
            "state": state.value if hasattr(state, 'value') else str(state),
            "progress": progress,
            "message": message,
            "details": details or {},
        })
    
    async def send_complete(self, slug: str, success: bool, final_state: State = None, error: str = None):
        """Send build completion notification."""
        await self.broadcast(slug, {
            "type": "complete",
            "slug": slug,
            "success": success,
            "final_state": final_state.value if final_state and hasattr(final_state, 'value') else str(final_state) if final_state else None,
            "error": error,
        })


# Global progress manager instance
progress_manager = ProgressManager()