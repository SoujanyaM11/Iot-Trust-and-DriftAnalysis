import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("sentineltrust")

class WebSocketManager:
    """Manage active WebSocket connections per user.

    The manager keeps a mapping of ``user_email`` → set of :class:`fastapi.WebSocket`
    objects. It provides ``connect``, ``disconnect`` and ``broadcast`` helpers.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept the WebSocket and register it using the ``x-user-email`` header.
        If the header is missing, the connection is accepted but not tracked.
        """
        await websocket.accept()
        user_email = websocket.headers.get("x-user-email")
        if not user_email:
            logger.debug("WebSocket connected without x-user-email – not tracking")
            return
        async with self.lock:
            self.active_connections.setdefault(user_email, set()).add(websocket)
        logger.info(f"WebSocket connected: {user_email} (total={len(self.active_connections[user_email])})")

    async def disconnect(self, websocket: WebSocket) -> None:
        user_email = websocket.headers.get("x-user-email")
        if not user_email:
            return
        async with self.lock:
            connections = self.active_connections.get(user_email)
            if connections and websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del self.active_connections[user_email]
        logger.info(f"WebSocket disconnected: {user_email}")

    async def broadcast(self, user_email: str, message: dict) -> None:
        """Send a JSON‑serialisable ``message`` to all sockets for ``user_email``.
        Faulty sockets are removed.
        """
        async with self.lock:
            sockets = list(self.active_connections.get(user_email, []))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket send error for {user_email}: {e}")
                await self.disconnect(ws)
