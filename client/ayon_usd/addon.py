"""USD Addon for AYON."""
from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING, Any, Optional

from ayon_core import style
from ayon_core.addon import AYONAddon, IPluginPaths, ITrayService
from loguru import logger

from . import config, utils
from .ayon_bin_client.ayon_bin_distro.util import zip
from .ayon_bin_client.ayon_bin_distro.work_handler import worker
from .cache_manager import CacheService, CacheServiceConfig, RateLimitConfig
from .utils import ADDON_DATA_JSON_PATH, DOWNLOAD_DIR
from .version import __version__

if TYPE_CHECKING:
    from ayon_core.addon import AddonsManager

USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


class USDAddon(AYONAddon, IPluginPaths, ITrayService):
    """Addon to add USD Support to AYON.

    Addon can also skip distribution of binaries from server and can
    use path/arguments defined by server.

    Cares about supplying USD Framework.
    """

    name = "usd"
    version = __version__
    _download_window = None

    def __init__(self, addon_manager: AddonsManager, settings: dict[str, Any]):
        """Initialize the USD addon."""
        super().__init__(addon_manager, settings)
        self._cache_service: Optional[CacheService] = None
        self._cache_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self.log = logger.bind(addon=self.name)
        self.settings = settings

    @property
    def label(self) -> str:
        """Get the addon label.

        Returns:
            str: The addon label.

        """
        return "AYON USD Addon Cache Service"

    def tray_init(self) -> None:
        """Initialize tray module."""
        super().tray_init()
        self.log.info("Initializing AYON USD addon tray service")

        # Create event loop for async operations
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # Create an asyncio.Event to signal the cache task to stop
        self._stop_event = asyncio.Event()

        # Get configuration from environment or settings
        config = self._get_cache_config()

        if config:
            # Initialize cache service
            self._cache_service = CacheService(config, self.name, self.version)
            self.log.info("Cache service initialized")
        else:
            self.log.warning(
                "Cache service not configured - missing required settings")

    def initialize(self, studio_settings: dict[str, Any]) -> None:
        """Initialize USD Addon."""
        self._download_window = None

    def tray_start(self) -> None:
        """Start tray module.

        Skip downloading base USD, not needed now.
        """
        if not self._cache_service or not self._loop:
            self.log.error("Cache service not initialized")
            return

        try:
            # Start cache service in background task
            self._cache_task = self._loop.create_task(
                self._run_cache_service())

            # Run the event loop in a separate thread to avoid blocking
            import threading

            def run_loop() -> None:
                """Run the asyncio event loop."""
                if not self._loop:
                    return
                self._loop.run_forever()

            self._loop_thread = threading.Thread(target=run_loop, daemon=True)
            self._loop_thread.start()

            self.log.info("AYON USD addon cache service started successfully")

        except Exception:
            msg = "Failed to start AYON USD addon cache service"
            self.log.exception(msg)

    def tray_exit(self) -> None:
        """Exit tray module."""
        if (self._cache_service and
                self._loop and not self._loop.is_closed()):
            # Schedule the stop coroutine
            future = asyncio.run_coroutine_threadsafe(
                self._cache_service.stop(),
                self._loop
            )
            future.result(timeout=10)  # Wait up to 10 seconds

        # Signal the cache task to exit and stop the event loop
        if self._loop and not self._loop.is_closed():
            if self._stop_event is not None:
                # Set the event in the event loop thread to wake the cache task
                self._loop.call_soon_threadsafe(self._stop_event.set)
            self._loop.call_soon_threadsafe(self._loop.stop)
        # Stop the event loop
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _run_cache_service(self) -> None:
        """Run the cache service."""
        if not self._cache_service:
            self.log.error("Cache service not initialized")
            return
        try:
            await self._cache_service.start()
            # Wait until stop event is set instead of busy sleeping
            if self._stop_event is None:
                self._stop_event = asyncio.Event()
            await self._stop_event.wait()
        except asyncio.CancelledError:
            self.log.exception("Cache service task cancelled")
        except Exception:
            self.log.exception("Cache service error")

    def tray_menu(self, _tray_menu: Any) -> None:
        """Add menu items to tray menu."""

    @staticmethod
    def get_launch_hook_paths() -> list[str]:
        """Get paths to launch hooks.

        Returns:
            list[str]: List of paths to launch hooks.

        """
        return [os.path.join(USD_ADDON_DIR, "hooks")]

    @staticmethod
    def get_publish_plugin_paths(_host_name: str) -> list[str]:
        """Get paths to publish plugins.

        Returns:
            list[str]: List of paths to publish plugins.

        """
        return [
            os.path.join(USD_ADDON_DIR, "plugins", "publish")
        ]
