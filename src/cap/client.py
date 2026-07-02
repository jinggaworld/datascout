import json
import logging
from typing import Any, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from src.config import get_settings

logger = logging.getLogger(__name__)


class CapClient:
    """WebSocket client for CAP Protocol communication."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ws_url = settings.cap_ws_url
        self.agent_id = settings.cap_agent_id
        self._ws: Any = None
        self._connected = False
        self._message_handlers: list[Callable] = []

    def on_message(self, handler: Callable) -> None:
        """Register a handler for incoming order events."""
        self._message_handlers.append(handler)

    async def connect(self) -> None:
        """Connect to CAP WebSocket endpoint."""
        try:
            self._ws = await websockets.connect(
                self.ws_url,
                additional_headers={"X-Agent-ID": self.agent_id},
            )
            self._connected = True
            logger.info("Connected to CAP network at %s", self.ws_url)
        except Exception as e:
            logger.error("Failed to connect to CAP: %s", e)
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from CAP WebSocket."""
        if self._ws:
            await self._ws.close()
            self._connected = False
            logger.info("Disconnected from CAP network")

    async def listen(self) -> None:
        """Listen for incoming messages and dispatch to handlers."""
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to CAP network")

        try:
            async for message in self._ws:
                data = json.loads(message)
                logger.info("Received CAP message: type=%s", data.get("type"))
                for handler in self._message_handlers:
                    try:
                        await handler(data)
                    except Exception as e:
                        logger.error("Handler error: %s", e)
        except ConnectionClosed:
            logger.warning("CAP connection closed")
            self._connected = False

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to CAP network."""
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to CAP network")
        await self._ws.send(json.dumps(message))
        logger.info("Sent CAP message: type=%s", message.get("type"))

    async def submit_delivery(self, delivery: dict[str, Any]) -> dict[str, Any]:
        """Submit delivery proof to CAP network."""
        await self.send({"type": "delivery", "payload": delivery})
        # In production, wait for acknowledgment
        return {"status": "submitted", "order_id": delivery.get("order_id")}

    async def acknowledge_clear(self, order_id: str) -> dict[str, Any]:
        """Acknowledge settlement clearance."""
        await self.send({"type": "clear_ack", "order_id": order_id})
        return {"status": "acknowledged", "order_id": order_id}

    @property
    def is_connected(self) -> bool:
        return self._connected
