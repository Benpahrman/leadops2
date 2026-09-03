"""WebSocket routes for real-time progress updates."""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import ClerkAuthService, ClerkUser
from ..websocket import progress_manager

logger = logging.getLogger("api.websocket")
router = APIRouter()


@router.websocket("/ws/progress/{slug}")
async def websocket_progress(
    websocket: WebSocket,
    slug: str,
):
    """WebSocket endpoint for real-time build progress.
    
    Accepts connections from the customer sandbox and admin dashboard,
    validating user token if present, and broadcasting real-time progress events.
    """
    # Extract token from query params, headers, or cookies
    token = (
        websocket.query_params.get("token")
        or websocket.headers.get("authorization", "").replace("Bearer ", "").strip()
        or websocket.cookies.get("__session")
        or websocket.cookies.get("__client_uat")
    )

    user: ClerkUser | None = None
    if token:
        try:
            auth_service = ClerkAuthService()
            user = auth_service.verify_token(token)
        except Exception as auth_err:
            logger.debug(f"WebSocket session notice for slug={slug}: {auth_err}")

    # Register and accept WebSocket connection
    await progress_manager.connect(slug, websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "slug": slug,
            "status": "connected",
            "user": user.email if user else "anonymous",
        })

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
        logger.debug(f"WebSocket connection closed for {slug}: {e}")
        progress_manager.disconnect(slug, websocket)