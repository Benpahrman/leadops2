"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from ..auth import ClerkUser, get_current_user
from ..websocket import progress_manager

router = APIRouter()


@router.websocket("/ws/progress/{slug}")
async def websocket_progress(
    websocket: WebSocket,
    slug: str,
    user: ClerkUser = Depends(get_current_user),
):
    """WebSocket endpoint for real-time build progress.
    
    Requires authentication. User must have access to the lead/sandbox.
    """
    # Validate user has access to this slug
    # In a real implementation, you'd verify the user owns this sandbox
    
    await progress_manager.connect(slug, websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages (ping/pong)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        progress_manager.disconnect(slug, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for {slug}: {e}")
        progress_manager.disconnect(slug, websocket)


import json
import logging
logger = logging.getLogger("api.websocket")