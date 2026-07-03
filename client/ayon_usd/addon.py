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

        Download USD if needed.
        """
        self._download_global_lakefs_binaries()
        self.log.info("Starting AYON USD addon tray service")

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

    def _download_global_lakefs_binaries(self) -> None:
        """Download USD binaries from lakeFS if needed.

        Raises:
            ValueError: If unable to find UsdLib date modified
                timestamp on LakeFS server.

        """
        dist_settings = self.settings["usd"]["distribution"]
        if not dist_settings["enabled"]:
            self.log.info("USD Binary distribution is disabled.")
            return

        if dist_settings["enabled"] and dist_settings["type"] == "local":
            self.log.info(
                "Local distribution; skipping LakeFS USD lib download."
            )
            return

        utils.create_addon_data_json_file()

        lakefs_repo: str = dist_settings["lake_fs"]["server_repo"]
        lakefs_repo = lakefs_repo.strip().rstrip("/")
        lake_fs_usd_lib_path = config.get_lakefs_usdlib_path(lakefs_repo)

        if not utils.is_usd_lib_download_needed(
                self.settings, lake_fs_usd_lib_path):
            self.log.info("USD Libs already available. Skipping download.")
            return

        # Get modified time on LakeFS
        lake_fs = config.get_global_lake_instance(self.settings)
        usd_lib_lake_fs_time_cest = (
            lake_fs
            .get_element_info(lake_fs_usd_lib_path)
            .get("Modified Time")
        )
        if not usd_lib_lake_fs_time_cest:
            msg = (
                "Unable to find UsdLib date modified timestamp on "
                f"LakeFs server: {lake_fs_usd_lib_path}"
            )
            raise ValueError(msg)

        with open(ADDON_DATA_JSON_PATH, "r+", encoding="utf-8") as json_file:
            addon_data_json = json.load(json_file)
            addon_data_json["usd_lib_lake_fs_time_cest"] = (
                usd_lib_lake_fs_time_cest
            )

            json_file.seek(0)
            json.dump(
                addon_data_json,
                json_file,
            )
            json_file.truncate()

        controller = worker.Controller()

        usd_download_work_item = controller.construct_work_item(
            func=lake_fs.clone_element,
            kwargs={
                "lake_fs_object_uir": lake_fs_usd_lib_path,
                "dist_path": DOWNLOAD_DIR,
            },
            progress_title="Download UsdLib",
        )

        usd_zip_path = os.path.join(
            DOWNLOAD_DIR,
            os.path.basename(lake_fs_usd_lib_path)
        )
        usd_lib_path = os.path.splitext(usd_zip_path)[0]
        controller.construct_work_item(
            func=zip.extract_zip_file,
            kwargs={
                "zip_file_path": usd_zip_path,
                "dest_dir": usd_lib_path,
            },
            progress_title="Unzip UsdLib",
            dependency_id=[usd_download_work_item.get_uuid()],
        )

        from .ayon_bin_client.ayon_bin_distro.gui import progress_ui
        download_ui = progress_ui.ProgressDialog(
            controller,
            close_on_finish=True,
            auto_close_timeout=1,
            delete_progress_bar_on_finish=False,
            title="ayon_usd-Addon [UsdLib Download]",
        )
        download_ui.setStyleSheet(style.load_stylesheet())
        download_ui.start()
        self._download_window = download_ui

    def _get_cache_config(self) -> Optional[CacheServiceConfig]:
        """Get cache service configuration from environment and settings.

        Returns:
            Cache configuration or None if not properly configured.

        """
        # Get server connection info from environment
        server_url = os.getenv("AYON_SERVER_URL")
        api_key = os.getenv("AYON_API_KEY")

        if not server_url or not api_key:
            logger.error("Missing AYON_SERVER_URL or "
                            "AYON_API_KEY environment variables")
            return None

        # Get memcached settings from environment
        memcache_hosts: list[str] = []
        if self.settings["usd"]["memcached"].get("enabled", False):
            memcache_hosts = self.settings["usd"]["memcached"].get(
                "servers", [])
            if os.getenv("AYON_MEMCACHED_SERVERS"):
                memcache_hosts = os.getenv(
                    "AYON_MEMCACHED_SERVERS", "").split(",")

        # Get rate limiting settings
        rate_limit_config = RateLimitConfig(
            requests_per_second=float(
                os.getenv("AYON_RATE_LIMIT_RPS", "5.0")),
            burst_limit=int(
                os.getenv("AYON_BURST_LIMIT", "10")),
            cooldown_period=float(
                os.getenv("AYON_COOLDOWN_PERIOD", "60.0")),
            per_project_limit=float(
                os.getenv("AYON_PROJECT_RATE_LIMIT", "2.0"))
        )

        # Get caching settings
        default_ttl = int(os.getenv("AYON_DEFAULT_TTL", "3600"))
        prefetch_interval = int(os.getenv("AYON_PREFETCH_INTERVAL", "300"))
        max_concurrent_fetches = int(os.getenv("AYON_MAX_CONCURRENT", "5"))

        # Get projects and folders to cache from environment
        folders_to_cache = {}

        # Example: AYON_PRECACHE_PROJECTS="TestProject,AnotherProject"
        projects_to_cache: list[str] = []
        projects_env = os.getenv("AYON_PRECACHE_PROJECTS", "")
        if projects_env:
            projects_to_cache = [
                p.strip()
                for p in projects_env.split(",")
                if p.strip()
            ]

        # Example: AYON_PRECACHE_FOLDERS_TestProject="folder1,folder2"
        for project in projects_to_cache:
            folders_env = os.getenv(f"AYON_PRECACHE_FOLDERS_{project}", "")
            if folders_env:
                folders_to_cache[project] = [
                    f.strip()
                    for f in folders_env.split(",")
                    if f.strip()
                ]

        config = CacheServiceConfig(
            server_url=server_url,
            api_key=api_key,
            memcache_hosts=memcache_hosts,
            default_ttl=default_ttl,
            rate_limit_config=rate_limit_config,
            prefetch_interval=prefetch_interval,
            max_concurrent_fetches=max_concurrent_fetches,
            projects_to_cache=projects_to_cache,
            folders_to_cache=folders_to_cache
        )

        logger.info(
            f"Cache config created for {len(projects_to_cache)} projects")
        return config
