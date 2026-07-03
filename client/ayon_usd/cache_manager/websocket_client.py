"""WebSocket client.

Receiving cache invalidation events from AYON server.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

import websockets
from loguru import logger
from websockets.exceptions import ConnectionClosed, WebSocketException

# Position of entity type in topic string
# e.g., "entity.folder.updated" -> "folder" is at position 2
ENTITY_STR_POSITION = 2


@dataclass
class InvalidationEvent:
    """Cache invalidation event."""
    event_type: str
    project_name: str
    entity_id: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def _entity_type_from_topic(cls, topic: str) -> str:
        """Extract entity type from topic string.

        Topic strings are like:
        - entity.folder.updated
        - entity.project.updated

        The entity type is the second part (e.g., "folder", "project").

        Args:
            topic: Topic string from the event.

        Returns:
            Entity type (e.g., "folder", "project", "task")

        """
        parts = topic.split(".")
        if len(parts) >= ENTITY_STR_POSITION:
            return parts[1]  # e.g., "folder" from "entity.folder.updated"
        return "unknown"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvalidationEvent:
        """Create event from dictionary.

        Args:
            data: Dictionary with event data.

        Returns:
            InvalidationEvent instance

        """
        summary = data.get("summary") or {}
        entity_type = cls._entity_type_from_topic(data.get("topic", ""))
        if entity_type == "folder":
            data["folder_id"] = summary.get("entityId")

        if entity_type == "task":
            data["task_id"] = summary.get("entityId")

        return cls(
            event_type=data.get("topic", ""),
            project_name=data.get("project", ""),
            entity_id=summary.get("entityId"),
            timestamp=data.get("timestamp")
        )


class WebSocketClient:
    """WebSocket client for receiving cache invalidation events."""

    def __init__(self, server_url: str, api_key: str):
        """Initialize WebSocket client.

        Args:
            server_url: AYON server URL
            api_key: API key for authentication
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        # replace scheme for websocket
        self.ws_url = self.server_url.replace(
            "http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{self.ws_url}/ws"

        self._websocket: websockets.ClientConnection | None = None
        self._running = False
        self._reconnect_delay = 5
        self._max_reconnect_delay = 60
        self._event_handlers: list[Callable[[InvalidationEvent], None]] = []
        logger.debug(f"Using websockets version: {websockets.__version__}")

    def add_event_handler(
            self,
            handler: Callable[[InvalidationEvent], None]) -> None:
        """Add an event handler for invalidation events.

        Args:
            handler: Function to call when an event is received

        """
        self._event_handlers.append(handler)

    def remove_event_handler(
            self,
            handler: Callable[[InvalidationEvent], None]) -> None:
        """Remove an event handler.

        Args:
            handler: Handler function to remove

        """
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message.

        Args:
            message: Raw message string
        """
        try:
            event = None
            data = json.loads(message)
            # Check if it's a cache invalidation event
            # Topics for invalidation events
            # TODO (antirotor): this needs to be more flexible/configurable
            #   as invalidation topics are more than just these and the changed
            #   topics are more specific - like entity.folder.attrib_changed.
            #   Maybe adding a wildcard match? Or some Cache Strategy interface
            #   so that would allow customization of cache invalidation logic.

            invalidation_topics = {
                "entity.project.deleted",
                "entity.folder.deleted",
                "entity.folder.attrib_changed",
                "entity.folder.status_changed",
                "entity.task.deleted",
                "entity.task.attrib_changed",
                "entity.task.status_changed",
            }

            if data.get("topic") in invalidation_topics:
                event = InvalidationEvent.from_dict(data)
                logger.debug(
                    f"Received invalidation event: {event.event_type} "
                    f"for {event.project_name}")

            if event is None:
                return

            # Notify all handlers
            for handler in self._event_handlers:
                try:
                    handler(event)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Message: {message}")
                    logger.exception(f"Error in event handler: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Message: {message}")
            logger.exception(f"Failed to decode WebSocket message: {e}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Message: {message}")
            logger.exception(f"Error handling WebSocket message: {e}")

    async def _connect(self) -> bool:
        """Establish WebSocket connection.

        Returns:
            True if connection successful
        """
        try:
            self._websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10
            )

            subscribe_data = json.dumps(
                    {
                        "topic": "auth",
                        "token": self.api_key,
                        "subscribe": [
                            "entity.folder",
                            "entity.project",
                            "entity.task"],
                     })
            await self._websocket.send(
                subscribe_data, text=True)  # Subscribe to all entity events
            logger.info(f"Connected to WebSocket at {self.ws_url}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
        return True

    async def _listen(self) -> None:
        """Listen for WebSocket messages."""
        if not self._websocket:
            return
        try:
            async for message in self._websocket:
                # logger.debug(f"WebSocket message received: {message}")
                await self._handle_message(str(message))

        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Unexpected error in WebSocket listener: {e}")

    async def start(self) -> None:
        """Start the WebSocket client with auto-reconnect."""
        self._running = True
        reconnect_delay = self._reconnect_delay

        while self._running:
            try:
                if await self._connect():
                    # Reset delay on successful connection
                    reconnect_delay = self._reconnect_delay
                    await self._listen()

                if not self._running:
                    break

                logger.info(f"Reconnecting in {reconnect_delay} seconds ...")
                await asyncio.sleep(reconnect_delay)

                # Exponential backoff with max limit
                reconnect_delay = min(
                    reconnect_delay * 2, self._max_reconnect_delay)
                logger.debug(
                    f"Next reconnect delay: {reconnect_delay} seconds")

            except Exception as e:  # noqa: BLE001
                logger.error(f"WebSocket client error: {e}")
                await asyncio.sleep(reconnect_delay)

    async def stop(self) -> None:
        """Stop the WebSocket client."""
        self._running = False

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        logger.info("WebSocket client stopped")

    async def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected
        """
        if not self._websocket:
            return False

        try:
            await self._websocket.recv()
        except (ConnectionClosed, WebSocketException):
            return False

        return (
            self._websocket is not None
            and not self._websocket.recv()
        )
