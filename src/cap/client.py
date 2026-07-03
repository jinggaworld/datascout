"""Production WebSocket client for CROO CAP Protocol.

Handles: connect, auto-reconnect, order lifecycle, delivery submission.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from src.config import get_settings

logger = logging.getLogger(__name__)


class CapClient:
    """WebSocket client for CAP Protocol communication with CROO Network."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ws_url = settings.cap_ws_url
        self.api_url = settings.cap_api_url
        self.agent_id = settings.cap_agent_id
        self.sdk_key = settings.cap_sdk_key
        self._ws: Any = None
        self._connected = False
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._message_handlers: list[Callable] = []
        self._reconnect_delay = 2.0
        self._max_reconnect_delay = 60.0
        self._should_run = False

    def on_message(self, handler: Callable) -> None:
        """Register a handler for incoming order events."""
        self._message_handlers.append(handler)

    async def connect(self) -> bool:
        """Connect to CAP WebSocket endpoint with auth headers."""
        if not self.agent_id:
            logger.warning("CAP_AGENT_ID not set — cannot connect to CROO")
            return False

        headers = {"X-Agent-ID": self.agent_id}
        if self.sdk_key:
            headers["X-SDK-Key"] = self.sdk_key
            headers["Authorization"] = f"Bearer {self.sdk_key}"

        try:
            self._ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._reconnect_delay = 2.0  # reset on success
            logger.info("Connected to CROO network at %s", self.ws_url)
            return True
        except Exception as e:
            logger.error("Failed to connect to CROO: %s", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from CROO."""
        self._should_run = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._connected = False
        logger.info("Disconnected from CROO network")

    async def listen(self) -> None:
        """Listen for incoming messages and dispatch to handlers."""
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to CROO network")

        try:
            async for message in self._ws:
                data = json.loads(message)
                msg_type = data.get("type", "unknown")
                logger.info("Received CROO message: type=%s", msg_type)

                for handler in self._message_handlers:
                    try:
                        await handler(data)
                    except Exception as e:
                        logger.error("Handler error for %s: %s", msg_type, e)
        except ConnectionClosed as e:
            logger.warning("CROO connection closed: code=%s", e.code)
            self._connected = False
        except asyncio.CancelledError:
            self._connected = False
        except Exception as e:
            logger.error("CROO listen error: %s", e)
            self._connected = False

    async def start_listener(self) -> None:
        """Start listening with auto-reconnect in background."""
        self._should_run = True
        connected = await self.connect()
        if connected:
            self._listen_task = asyncio.create_task(self.listen())
            self._listen_task.add_done_callback(self._on_listen_done)

    def _on_listen_done(self, task: asyncio.Task) -> None:
        """Handle listen task completion — trigger reconnect if needed."""
        if self._should_run and not task.cancelled():
            # Guard against multiple reconnect tasks
            if self._reconnect_task and not self._reconnect_task.done():
                return
            logger.info("Listen ended, scheduling reconnect...")
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Auto-reconnect with exponential backoff."""
        while self._should_run:
            delay = min(self._reconnect_delay, self._max_reconnect_delay)
            logger.info("Reconnecting to CROO in %.1fs...", delay)
            await asyncio.sleep(delay)
            self._reconnect_delay = min(
                self._reconnect_delay * 2, self._max_reconnect_delay
            )

            connected = await self.connect()
            if connected:
                self._listen_task = asyncio.create_task(self.listen())
                self._listen_task.add_done_callback(self._on_listen_done)
                return

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to CROO network."""
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to CROO network")
        await self._ws.send(json.dumps(message))
        logger.info("Sent CROO message: type=%s", message.get("type"))

    async def submit_delivery(self, delivery: dict[str, Any]) -> dict[str, Any]:
        """Submit delivery proof to CROO network."""
        try:
            await self.send({"type": "delivery", "payload": delivery})
            return {"status": "submitted", "order_id": delivery.get("order_id")}
        except Exception as e:
            logger.error("Failed to submit delivery: %s", e)
            return {"status": "error", "error": str(e)}

    async def acknowledge_clear(self, order_id: str) -> dict[str, Any]:
        """Acknowledge settlement clearance."""
        try:
            await self.send({"type": "clear_ack", "order_id": order_id})
            return {"status": "acknowledged", "order_id": order_id}
        except Exception as e:
            logger.error("Failed to acknowledge clear: %s", e)
            return {"status": "error", "error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> dict[str, Any]:
        """Return current connection status."""
        settings = get_settings()
        return {
            "connected": self._connected,
            "agent_id": self.agent_id,
            "wallet": settings.cap_agent_wallet,
            "ws_url": self.ws_url,
            "api_url": self.api_url,
            "has_sdk_key": bool(self.sdk_key),
        }
