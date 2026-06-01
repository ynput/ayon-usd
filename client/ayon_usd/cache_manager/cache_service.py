"""Main cache service.

Orchestrates GraphQL fetching, memcached storage, and event handling.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

import ayon_api
from loguru import logger

from .graphql_client import GraphQLClient
from .memcached_client import MemcachedClient
from .null_client import NullCacheClient
from .prefetcher import Prefetcher
from .rate_limiter import RateLimitConfig, RateLimiter
from .websocket_client import InvalidationEvent, WebSocketClient


@dataclass
class CacheServiceConfig:
    """Configuration for the cache service."""
    # Server connection
    server_url: str
    api_key: str

    # Memcached settings
    memcache_hosts: list[str] = field(default_factory=lambda: ["localhost:11211"])
    default_ttl: int = 3600  # 1 hour

    # Rate limiting
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)

    # Pre-fetching settings
    prefetch_interval: int = 300  # 5 minutes
    max_concurrent_fetches: int = 5

    # Projects and folders to cache
    projects_to_cache: list[str] = field(default_factory=list)
    # project -> folder_ids
    folders_to_cache: dict[str, list[str]] = field(default_factory=dict)


class CacheService:
    """Main cache service for AYON hierarchy data."""

    def __init__(self, config: CacheServiceConfig):
        """Initialize the cache service.

        Args:
            config: Service configuration

        Raises:
            RuntimeError: If current user cannot be determined

        """
        self.config = config

        # Initialize components
        self.graphql_client = GraphQLClient(config.server_url, config.api_key)
        try:
            self.cache_client = MemcachedClient(
                config.memcache_hosts)
        except Exception as e:
            logger.exception(f"Failed to initialize Memcached client: {e}")
            self.cache_client = NullCacheClient()
            logger.warning("Using NullCacheClient, caching is disabled")

        self.websocket_client = (WebSocketClient
                                 (config.server_url, config.api_key))
        self.rate_limiter = RateLimiter(config.rate_limit_config)
        current_user = ayon_api.get_user()
        if not current_user:
            msg = "Failed to get current user from AYON API"
            raise RuntimeError(msg)
        self.prefetcher = Prefetcher(current_user["name"])

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
            await self.graphql_client.start()

            # Start WebSocket client for events
            self._websocket_task = asyncio.create_task(
                self.websocket_client.start())

            # Start pre-fetching task
            self._prefetch_task = asyncio.create_task(self._prefetch_loop())

            self._running = True
            logger.info("Cache service started successfully")

            await self.seed_cache()

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
        await self.graphql_client.close()
        self.cache_client.disconnect()

        logger.info("Cache service stopped")

    async def get_folder_data(
            self,
            project_name: str,
            folder_id: str,
            *,
            force_refresh: bool = False) -> Optional[dict[str, Any]]:
        """Get folder data from cache or fetch from server.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Folder data with products and tasks
        """
        # Try cache first unless force refresh
        if not force_refresh:
            cached_data = self.cache_client.get_folder_data(
                project_name, folder_id)
            if cached_data:
                self.stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {project_name}:{folder_id}")
                return cached_data

        self.stats["cache_misses"] += 1
        logger.debug(f"Cache miss for {project_name}:{folder_id}, "
                     "fetching from server")

        # Fetch from server with rate limiting
        if not await self.rate_limiter.acquire(project_name):
            logger.warning(f"Rate limit exceeded for {project_name}, "
                           f"cannot fetch {folder_id}")
            return None

        try:
            data = await self.graphql_client.fetch_folder_data(
                project_name, folder_id)
            if data:
                # Store in cache
                self.cache_client.set_folder_data(
                    project_name,
                    folder_id,
                    data,
                    self.config.default_ttl
                )
                self.stats["fetch_successes"] += 1
                logger.debug("Fetched and cached data for "
                             f"{project_name}:{folder_id}")
                return data

            self.stats["fetch_failures"] += 1
            logger.warning(
                f"Failed to fetch data for {project_name}:{folder_id}")

        except Exception as e:  # noqa: BLE001
            self.stats["fetch_failures"] += 1
            logger.error(
                f"Error fetching data for {project_name}:{folder_id}: {e}")

        return None
    
    async def get_project_data(
            self,
            project_name: str,
            force_refresh: bool = False) -> Optional[dict[str, Any]]:
        """Get project data from cache or fetch from server.

        Args:
            project_name: Name of the project

        Returns:
            Project data with folders, products, and tasks
        """
        if not force_refresh:
            cached_data = self.cache_client.get_project_data(
                project_name)
            if cached_data:
                self.stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {project_name}")
                return cached_data

        self.stats["cache_misses"] += 1
        logger.debug(f"Cache miss for {project_name}, fetching from server")

        # Fetch from server with rate limiting
        if not await self.rate_limiter.acquire(project_name):
            logger.warning(
                f"Rate limit exceeded for {project_name}, cannot fetch data")
            return None

        try:
            data = await self.graphql_client.fetch_project_data(
                project_name)
            if data:
                # Store in cache
                self.cache_client.set_project_data(
                    project_name,
                    data,
                    self.config.default_ttl
                )
                self.stats["fetch_successes"] += 1
                logger.debug("Fetched and cached data for "
                             f"{project_name}")
                return data

            self.stats["fetch_failures"] += 1
            logger.warning(
                f"Failed to fetch data for {project_name}")

        except Exception as e:  # noqa: BLE001
            self.stats["fetch_failures"] += 1
            logger.error(
                f"Error fetching data for {project_name}: {e}")

        return None

    async def prefetch_folder_data(
            self, project_name: str, folder_id: str) -> bool:
        """Pre-fetch folder data in the background.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder

        Returns:
            True if successful
        """
        # Check if we can make a request
        if not await self.rate_limiter.can_make_request(project_name):
            logger.debug(
                f"Skipping prefetch for {project_name}:{folder_id} "
                "due to rate limiting")
            return False

        # Check if data is already fresh in cache
        cached_folder_data = self.cache_client.get_folder_data(
            project_name, folder_id)
        cached_project_data = self.cache_client.get_project_data(
            project_name)
        if cached_folder_data or cached_project_data:
            # Could check timestamp here to determine if refresh is needed
            logger.debug(
                f"Data already cached for {project_name}:{folder_id}")
            return True

        project_result = None
        folder_result = None
        # Fetch with rate limiting
        if not cached_project_data:
            project_result = await self.get_project_data(project_name)
        if not cached_folder_data:
            folder_result = await self.get_folder_data(project_name, folder_id)

        return (project_result is not None) or (folder_result is not None)

    async def seed_cache(self) -> None:
        """Seed the cache with initial data for configured projects/folders."""
        logger.info("Seeding cache with initial data")

        ids_to_fetch = self.prefetcher.prefetch()
        seed = {}
        for project_name, folder_id in ids_to_fetch.folder_requests:
            if project_name not in seed:
                seed[project_name] = set()
            seed[project_name].add(folder_id)

        for project_name, folder_ids in seed.items():
            self.add_project_to_cache(project_name, list(folder_ids))
        logger.info("Cache seeding completed")

    async def _prefetch_loop(self) -> None:
        """Background task for pre-fetching configured folders."""
        logger.info("Starting pre-fetch loop")

        while self._running:
            try:
                await self._run_prefetch_cycle()
                self.stats["prefetch_cycles"] += 1

                # Wait for next cycle
                await asyncio.sleep(self.config.prefetch_interval)

            except asyncio.CancelledError:  # noqa: PERF203
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
            folder_ids = self.config.folders_to_cache.get(project_name, [])

            for folder_id in folder_ids:
                if len(fetch_tasks) >= self.config.max_concurrent_fetches:
                    break

                task = asyncio.create_task(
                    self.prefetch_folder_data(project_name, folder_id)
                )
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

            except asyncio.TimeoutError:
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

        if project_name not in self.config.folders_to_cache:
            self.config.folders_to_cache[project_name] = []

        # Add new folder IDs (avoid duplicates)
        for folder_id in folder_ids:
            if folder_id not in self.config.folders_to_cache[project_name]:
                self.config.folders_to_cache[project_name].append(folder_id)

        logger.info(
            f"Added project {project_name} with "
            f"{len(folder_ids)} folders to cache")

    def remove_project_from_cache(self, project_name: str) -> None:
        """Remove a project from the caching list and invalidate its cache.

        Args:
            project_name: Name of the project to remove

        """
        if project_name in self.config.projects_to_cache:
            self.config.projects_to_cache.remove(project_name)

        if project_name in self.config.folders_to_cache:
            del self.config.folders_to_cache[project_name]

        # Invalidate cached data
        self.cache_client.invalidate_project(project_name)

        logger.info(f"Removed project {project_name} from cache")

    def get_service_stats(self) -> dict[str, Any]:
        """Get comprehensive service statistics.

        Returns:
            Dictionary with service statistics

        """
        return {
            "service_stats": self.stats,
            "rate_limiter_stats": self.rate_limiter.get_stats(),
            "memcache_stats": self.cache_client.get_cache_stats(),
            "websocket_connected": self.websocket_client.is_connected(),
            "running": self._running,
            "configured_projects": len(self.config.projects_to_cache),
            "configured_folders": (
                sum(len(folders)
                for folders in self.config.folders_to_cache.values())
            )
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

    def add_folders_to_project(
            self,
            project_name: str,
            folder_ids: list[str],
            *,
            replace: bool = False) -> None:
        """Add or update folders for a specific project.

        Args:
            project_name: Name of the project
            folder_ids: List of folder IDs to add/set
            replace: If True, replace existing folders;
                if False, merge with existing
        """
        if project_name not in self.config.projects_to_cache:
            self.config.projects_to_cache.append(project_name)
            self.config.folders_to_cache[project_name] = []

        if replace:
            self.config.folders_to_cache[project_name] = folder_ids.copy()
            logger.info(
                f"Replaced folders for {project_name} "
                f"with {len(folder_ids)} folders")
        else:
            # Merge with existing, avoiding duplicates
            existing = set(self.config.folders_to_cache[project_name])
            new_folders = [fid for fid in folder_ids if fid not in existing]
            self.config.folders_to_cache[project_name].extend(new_folders)
            logger.info(
                f"Added {len(new_folders)} new folders to {project_name}")

    def remove_folders_from_project(
            self, project_name: str,
            folder_ids: Optional[list[str]] = None) -> None:
        """Remove specific folders or entire project from caching.

        Args:
            project_name: Name of the project
            folder_ids: Specific folder IDs to remove.
                If None, removes entire project.
        """
        if project_name not in self.config.folders_to_cache:
            logger.warning(
                f"Project {project_name} not found in cache configuration")
            return

        if folder_ids is None:
            # Remove entire project
            if project_name in self.config.projects_to_cache:
                self.config.projects_to_cache.remove(project_name)
            del self.config.folders_to_cache[project_name]

            # Invalidate cached data for the project
            self.cache_client.invalidate_project(project_name)
            logger.info(
                "Removed entire project "
                f"{project_name} from cache configuration")
        else:
            # Remove specific folders
            for folder_id in folder_ids:
                if folder_id in self.config.folders_to_cache[project_name]:
                    self.config.folders_to_cache[project_name].remove(folder_id)
                    # Invalidate cached data for the specific folder
                    self.cache_client.invalidate_folder(
                        project_name, folder_id)

            # Remove project if no folders left
            if not self.config.folders_to_cache[project_name]:
                if project_name in self.config.projects_to_cache:
                    self.config.projects_to_cache.remove(project_name)
                del self.config.folders_to_cache[project_name]
                logger.info(
                    f"Removed project {project_name} (no folders remaining)")
            else:
                logger.info(
                    f"Removed {len(folder_ids)} folders from {project_name}")

    async def trigger_immediate_prefetch(
            self,
            project_name: Optional[str] = None,
            folder_ids: Optional[list[str]] = None) -> None:
        """Trigger immediate prefetch for specific projects/folders.

        Args:
            project_name: Specific project to prefetch.
                If None, prefetch all configured.
            folder_ids: Specific folder IDs to prefetch.
                If None, prefetch all in project.
        """
        logger.info("Triggering immediate prefetch")

        if project_name and project_name not in self.config.projects_to_cache:
            logger.warning(
                f"Project {project_name} not configured for caching")
            return

        fetch_tasks = []

        if project_name:
            # Prefetch specific project
            target_folders = folder_ids or self.config.folders_to_cache.get(
                project_name, [])

            for folder_id in target_folders:
                if folder_id in self.config.folders_to_cache.get(
                        project_name, []):
                    
                    project_task = asyncio.create_task(
                        self.prefetch_project_data(project_name, folder_id)
                    )
                    folder_task = asyncio.create_task(
                        self.prefetch_folder_data(project_name, folder_id)
                    )
                    fetch_tasks.append(folder_task)

        else:
            # Prefetch all configured projects/folders
            for proj_name in self.config.projects_to_cache:
                for folder_id in self.config.folders_to_cache.get(
                        proj_name, []):
                    task = asyncio.create_task(
                        self.prefetch_folder_data(proj_name, folder_id)
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
