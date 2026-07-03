"""Production WebSocket client for CROO CAP Protocol.

Matches the CROO SDK EventStream protocol:
- WebSocket connects with sdkKey as query parameter
- Handles event types: negotiation_created, order.paid, order.delivered, order.cleared
- REST API calls for accept_negotiation, deliver_order
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import httpx
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
        self.wallet = settings.cap_agent_wallet
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
        """Connect to CAP WebSocket with sdkKey as query parameter.

        The CROO EventStream expects: wsURL + /ws?sdkKey=xxx
        """
        if not self.sdk_key:
            logger.warning("CAP_SDK_KEY not set — cannot connect to CROO")
            return False

        # Build WebSocket URL with sdkKey as query parameter (per SDK protocol)
        # SDK uses 'key' as the query parameter name
        ws_url = f"{self.ws_url}?key={self.sdk_key}"

        try:
            self._ws = await websockets.connect(
                ws_url,
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

                # CROO EventStream wraps events in {data: {...}} envelope
                if "data" in data:
                    event = data["data"]
                else:
                    event = data

                event_type = event.get("type", "unknown")
                negotiation_id = event.get("negotiation_id", "")
                order_id = event.get("order_id", "")

                logger.info(
                    "CROO event: type=%s, negotiation=%s, order=%s",
                    event_type,
                    negotiation_id,
                    order_id,
                )

                for handler in self._message_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error("Handler error for %s: %s", event_type, e)
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

    # ------------------------------------------------------------------
    # REST API operations (per CROO SDK AgentClient)
    # ------------------------------------------------------------------

    def _api_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-SDK-Key": self.sdk_key,
        }

    async def accept_negotiation(
        self, negotiation_id: str, provider_fund_address: str = ""
    ) -> dict[str, Any]:
        """Accept a negotiation (provider side) via REST API."""
        payload: dict[str, Any] = {}
        if provider_fund_address:
            payload["provider_fund_address"] = provider_fund_address

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_url}/backend/v1/orders/negotiate/{negotiation_id}/accept",
                    json=payload,
                    headers=self._api_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("Negotiation accepted: %s", negotiation_id)
                return data
        except httpx.HTTPStatusError as e:
            logger.error(
                "Accept negotiation failed (%d): %s",
                e.response.status_code,
                e.response.text[:200],
            )
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            logger.error("Accept negotiation error: %s", e)
            return {"error": str(e)}

    async def deliver_order(
        self,
        order_id: str,
        content: dict[str, Any],
        deliverable_type: str = "json",
    ) -> dict[str, Any]:
        """Submit delivery for an order via REST API."""
        payload = {
            "content": content,
            "deliverable_type": deliverable_type,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_url}/backend/v1/orders/{order_id}/deliver",
                    json=payload,
                    headers=self._api_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("Order delivered: %s", order_id)
                return data
        except httpx.HTTPStatusError as e:
            logger.error(
                "Deliver order failed (%d): %s",
                e.response.status_code,
                e.response.text[:200],
            )
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            logger.error("Deliver order error: %s", e)
            return {"error": str(e)}

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Get order details via REST API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.api_url}/backend/v1/orders/{order_id}",
                    headers=self._api_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Get order error: %s", e)
            return {"error": str(e)}

    async def get_negotiation(self, negotiation_id: str) -> dict[str, Any]:
        """Get negotiation details via REST API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.api_url}/backend/v1/orders/negotiate/{negotiation_id}",
                    headers=self._api_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Get negotiation error: %s", e)
            return {"error": str(e)}

    async def send(self, message: dict[str, Any]) -> None:
        """Send a raw message to CROO WebSocket."""
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to CROO network")
        await self._ws.send(json.dumps(message))
        logger.info("Sent CROO message: type=%s", message.get("type"))

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
