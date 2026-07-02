"""Main cache service.

Orchestrates GraphQL fetching, memcached storage, and event handling.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import ayon_api
from loguru import logger

from .memcached_client import MemcachedClient
from .null_client import NullCacheClient
from .rate_limiter import RateLimitConfig, RateLimiter
from .websocket_client import InvalidationEvent, WebSocketClient

if TYPE_CHECKING:
    from .cache_client import CacheClient


@dataclass
class CacheServiceConfig:
    """Configuration for the cache service."""
    # Server connection
    server_url: str
    api_key: str

    # Memcached settings
    memcache_hosts: list[str] = field(
        default_factory=lambda: ["localhost:11211"])
    default_ttl: int = 3600  # 1 hour

    # Rate limiting
    rate_limit_config: RateLimitConfig = field(
        default_factory=RateLimitConfig)

    # Pre-fetching settings
    prefetch_interval: int = 300  # 5 minutes
    max_concurrent_fetches: int = 5

    # Projects and folders to cache
    projects_to_cache: list[str] = field(default_factory=list)
    # project -> folder_ids
    folders_to_cache: dict[str, list[str]] = field(default_factory=dict)


class CacheService:
    """Main cache service for AYON hierarchy data."""

    def __init__(self,
                 config: CacheServiceConfig,
                 addon_name: str,
                 addon_version: str):
        """Initialize the cache service.

        Args:
            config: Service configuration
            addon_name: Name of the addon
            addon_version: Version of the addon

        Raises:
            RuntimeError: If current user cannot be determined

        """
        self.config = config

        # Initialize components
        try:
            self.cache_client: CacheClient = MemcachedClient(
                config.memcache_hosts)
        except Exception as e:
            logger.exception(f"Failed to initialize Memcached client: {e}")
            self.cache_client: CacheClient = NullCacheClient()
            logger.warning("Using NullCacheClient, caching is disabled")

        self.websocket_client = (WebSocketClient
                                 (config.server_url, config.api_key))
        self.rate_limiter = RateLimiter(config.rate_limit_config)
        self.current_user = ayon_api.get_user()
        if not self.current_user:
            msg = "Failed to get current user from AYON API"
            raise RuntimeError(msg)
        # self.prefetcher = Prefetcher(self.current_user["name"])
        self.addon_name = addon_name
        self.addon_version = addon_version

        # Service state
        self._running = False
        self._prefetch_task: Optional[asyncio.Task] = None
        self._websocket_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "fetch_successes": 0,
            "fetch_failures": 0,
            "invalidations": 0,
            "prefetch_cycles": 0
        }

        # Setup event handlers
        self.websocket_client.add_event_handler(self._handle_invalidation_event)

    async def start(self) -> None:
        """Start the cache service."""
        if self._running:
            logger.warning("Cache service is already running")
            return

        logger.info("Starting cache service...")

        try:
            # Connect to memcached
            self.cache_client.connect()

            # Start GraphQL client
            # await self.graphql_client.start()

            # Start WebSocket client for events
            self._websocket_task = asyncio.create_task(
                self.websocket_client.start())

            # Start pre-fetching task
            self._prefetch_task = asyncio.create_task(self._prefetch_loop())

            self._running = True
            logger.info("Cache service started successfully")

        except Exception as e:
            logger.error(f"Failed to start cache service: {e}")
            await self.stop()
            if not isinstance(self.cache_client, NullCacheClient):
                # try with NullCacheClient
                self.cache_client = NullCacheClient()
                logger.warning("Using NullCacheClient, caching is disabled")
                await self.start()
            else:
                raise

    async def stop(self) -> None:
        """Stop the cache service."""
        if not self._running:
            return

        logger.info("Stopping cache service...")

        self._running = False

        # Stop tasks
        if self._prefetch_task:
            self._prefetch_task.cancel()
            try:
                await self._prefetch_task
            except asyncio.CancelledError:
                logger.debug("Prefetch task cancelled")

        if self._websocket_task:
            await self.websocket_client.stop()
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                logger.debug("WebSocket task cancelled")

        # Close connections
        # await self.graphql_client.close()
        self.cache_client.disconnect()

        logger.info("Cache service stopped")

    async def get_paths_for_assigned_assets(
            self,
            project_name: str,
            user_name: str) -> bool:
        """Get asset paths assigned to the user.

        Args:
            project_name: Name of the project
            user_name: Name of the user
        
        Returns:
            bool: True if successful, False otherwise

        """
        # Check if we can make a request
        if not await self.rate_limiter.can_make_request(project_name):
            logger.debug(
                f"Skipping prefetch for {project_name} "
                "due to rate limiting")
            return False

        endpoint_root = ayon_api.get_addon_endpoint(
            self.addon_name, self.addon_version)

        # Fetch assigned asset paths from server
        try:
            response = ayon_api.get(
                f"{endpoint_root}/{project_name}/assigned_paths_for/{user_name}")

            # logger.debug(dir(response))

            path_list = json.loads(response.text)["pathList"]

            logger.debug(f"Fetched {len(path_list)} assigned paths for "
                         f"{user_name} in {project_name}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error fetching assigned asset paths for "
                         f"{user_name} in {project_name}: {e}")
            return False
        logger.debug(path_list)
        for path in path_list:
            self.cache_client.set_data(
                path["uri"], path["path"])

        logger.debug(f"Cached {len(path_list)} assigned paths for "
                     f"{user_name} in {project_name}")
        return True

    async def _prefetch_loop(self) -> None:
        """Background task for pre-fetching configured folders."""
        logger.info("Starting pre-fetch loop")

        while self._running:
            try:
                await self._run_prefetch_cycle()
                self.stats["prefetch_cycles"] += 1

                # Wait for next cycle
                await asyncio.sleep(self.config.prefetch_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error in prefetch loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

        logger.info("Pre-fetch loop stopped")

    async def _run_prefetch_cycle(self) -> None:
        """Run one cycle of pre-fetching."""
        logger.debug("Running prefetch cycle")

        # Collect all folder tasks
        fetch_tasks = []
        fetch_projects: set[str] = set()

        for project_name in self.config.projects_to_cache:
            fetch_projects.add(project_name)

            task = asyncio.create_task(
                self.get_paths_for_assigned_assets(
                    project_name, self.current_user["name"]))
            fetch_tasks.append(task)

        if fetch_tasks:
            # Wait for all tasks with a timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*fetch_tasks, return_exceptions=True),
                    timeout=300  # 5 minutes max for a prefetch cycle
                )

                success_count = sum(1 for r in results if r is True)
                logger.debug("Prefetch cycle completed: "
                             f"{success_count}/{len(results)} successful")

            except TimeoutError:
                logger.warning("Prefetch cycle timed out")
                # Cancel remaining tasks
                for task in fetch_tasks:
                    if not task.done():
                        task.cancel()

        if fetch_projects:
            logger.info(
                f"Prefetch cycle done for {len(fetch_projects)} projects")

    def _handle_invalidation_event(self, event: InvalidationEvent) -> None:
        """Handle cache invalidation events from WebSocket.

        Args:
            event: Invalidation event
        """
        logger.debug("Handling invalidation event: "
                     f"{event.event_type} for "
                     f"{event.project_name} - {event.entity_id}")

        try:
            if event.event_type.startswith(
                    "entity.folder") and event.entity_id:
                # Invalidate specific folder
                self.cache_client.invalidate_folder(
                    event.project_name, event.entity_id)
                self.stats["invalidations"] += 1

            elif event.event_type.startswith("entity.project"):
                # Invalidate entire project
                count = self.cache_client.invalidate_project(
                    event.project_name)
                self.stats["invalidations"] += count

        except Exception as e:  # noqa: BLE001
            logger.exception(f"Error handling invalidation event: {e}")

    def add_project_to_cache(
            self, project_name: str, folder_ids: list[str]) -> None:
        """Add a project and its folders to the caching list.

        Args:
            project_name: Name of the project
            folder_ids: List of folder IDs to cache

        """
        if project_name not in self.config.projects_to_cache:
            self.config.projects_to_cache.append(project_name)

        logger.info(
            f"Added project {project_name} to cache")

    def get_service_stats(self) -> dict[str, Any]:
        """Get comprehensive service statistics.

        Returns:
            Dictionary with service statistics

        """
        return {
            "service_stats": self.stats,
            "rate_limiter_stats": self.rate_limiter.get_stats(),
            # "memcache_stats": self.cache_client.get_cache_stats(),
            "websocket_connected": self.websocket_client.is_connected(),
            "running": self._running,
            "configured_projects": len(self.config.projects_to_cache),
        }

    def update_cache_configuration(
            self, projects_config: dict[str, list[str]]) -> None:
        """Dynamically update the projects and folders to cache.

        Args:
            projects_config: Dictionary mapping project
                names to lists of folder IDs
                Example::
                    {
                        "Project1": [
                            "folder1", "folder2"
                        ], "Project2": ["folder3"]
                    }

        """
        logger.info(
            "Updating cache configuration "
            f"with {len(projects_config)} projects")

        # Update the configuration
        self.config.projects_to_cache = list(projects_config.keys())
        self.config.folders_to_cache = projects_config.copy()

        logger.info("Cache configuration updated successfully")

    def get_cache_configuration(self) -> dict[str, list[str]]:
        """Get current cache configuration.

        Returns:
            Dictionary mapping project names to folder IDs
        """
        return self.config.folders_to_cache.copy()

    async def trigger_immediate_prefetch(
            self,
            project_name: Optional[str] = None) -> None:
        """Trigger immediate prefetch for specific projects/folders.

        Args:
            project_name: Specific project to prefetch.
                If None, prefetch all configured.

        """
        logger.info("Triggering immediate prefetch")

        if project_name and project_name not in self.config.projects_to_cache:
            logger.warning(
                f"Project {project_name} not configured for caching")
            return

        fetch_tasks = []

        if project_name:
            # Prefetch specific project
            task = asyncio.create_task(
                self.get_paths_for_assigned_assets(
                    project_name, self.current_user["name"])
            )
            fetch_tasks.append(task)

        else:
            # Prefetch all configured projects/folders
            for proj_name in self.config.projects_to_cache:
                task = asyncio.create_task(
                self.get_paths_for_assigned_assets(
                        proj_name, self.current_user["name"])
                )
                fetch_tasks.append(task)

        if fetch_tasks:
            try:
                results = await asyncio.gather(
                    *fetch_tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                logger.info(
                    "Immediate prefetch completed: "
                    f"{success_count}/{len(results)} successful")
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error in immediate prefetch: {e}")
