"""Dynamic configuration manager for cache service.

USD Resolver is using:

These are set from the settings and can be
overridden by environment variables:

AYON_ENABLE_MEMCACHED_CACHE=true       # Enable/disable memcached
AYON_MEMCACHED_SERVERS=localhost:11211 # Single or comma-separated servers
AYON_MEMCACHED_TIMEOUT_MS=1000

"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

import aiofiles
import aiofiles.os
import dotenv
from loguru import logger

if TYPE_CHECKING:
    from .cache_service import CacheService

WatcherCallback = Callable[[dict[str, list[str]]], None]


class CacheConfigManager:
    """Manager for dynamic cache configuration updates."""

    def __init__(self, cache_service: CacheService,
                config_file_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            cache_service: Reference to the CacheService instance
            config_file_path: Optional path to configuration
                file for persistence
        """
        self.cache_service = cache_service
        dotenv.load_dotenv()
        self.config_file_path = (
            config_file_path or "ayon_usd_cache_config.json"
        )
        self._config_watchers: list[WatcherCallback] = []
        self._file_watcher_task: Optional[asyncio.Task] = None
        self._last_file_mtime = 0

    def add_config_watcher(
            self, callback: WatcherCallback) -> None:
        """Add a callback that will be called when configuration changes.

        Args:
            callback: Function to call with new configuration

        """
        self._config_watchers.append(callback)

    def remove_config_watcher(
            self, callback: Callable[[dict[str, list[str]]], None]) -> None:
        """Remove a configuration watcher.

        Args:
            callback: Function to remove

        """
        if callback in self._config_watchers:
            self._config_watchers.remove(callback)

    def _notify_watchers(self, config: dict[str, list[str]]) -> None:
        """Notify all watchers of configuration changes.

        Args:
            config: New configuration

        """
        for callback in self._config_watchers:
            try:
                callback(config)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error in config watcher: {e}")

    async def load_config_from_file(
            self, file_path: Optional[Path] = None) -> dict[str, list[str]]:
        """Load configuration from JSON file.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary

        """
        file_path = file_path or Path(self.config_file_path)

        try:
            if await aiofiles.os.path.exists(file_path):
                async with aiofiles.open(file_path) as f:
                    content = await f.read()
                    config = json.loads(content)
                    logger.info(f"Loaded configuration from {file_path}")
                    return config
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to load config from {file_path}: {e}")

        return {}

    async def save_config_to_file(
            self,
            config: Optional[dict[str, list[str]]] = None,
            file_path: Optional[Path] = None) -> None:
        """Save current configuration to JSON file.

        Args:
            config: Configuration to save (uses current if None)
            file_path: Path to save to

        """
        file_path = file_path or Path(self.config_file_path)
        config = config or self.cache_service.get_cache_configuration()

        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(config, indent=2))

            logger.info(f"Saved configuration to {file_path}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to save config to {file_path}: {e}")

    async def apply_config_from_file(
            self, file_path: Optional[Path] = None) -> None:
        """Load and apply configuration from file.

        Args:
            file_path: Path to configuration file

        """
        config = await self.load_config_from_file(file_path)
        if config:
            self.cache_service.update_cache_configuration(config)
            self._notify_watchers(config)
            await self.cache_service.trigger_immediate_prefetch()

    async def start_file_watcher(
            self, file_path: Optional[Path] = None,
            check_interval: int = 5) -> None:
        """Start watching configuration file for changes.

        Args:
            file_path: Path to watch
            check_interval: How often to check for changes (seconds)

        """
        file_path = file_path or Path(self.config_file_path)

        if self._file_watcher_task:
            logger.warning("File watcher already running")
            return

        self._file_watcher_task = asyncio.create_task(
            self._watch_config_file(file_path, check_interval)
        )
        logger.info(f"Started watching {file_path} for changes")

    async def stop_file_watcher(self) -> None:
        """Stop watching configuration file."""
        if self._file_watcher_task:
            self._file_watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._file_watcher_task
            self._file_watcher_task = None
            logger.info("Stopped file watcher")

    async def _watch_config_file(
            self, file_path: Path, check_interval: int) -> None:
        """Watch configuration file for changes."""
        try:
            while True:
                try:
                    if await aiofiles.os.path.exists(file_path):
                        stat_result = await aiofiles.os.stat(file_path)
                        mtime = stat_result.st_mtime

                        if mtime != self._last_file_mtime:
                            self._last_file_mtime = mtime
                            logger.info(
                                f"Configuration file {file_path} changed, "
                                "reloading...")
                            await self.apply_config_from_file(file_path)

                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error checking config file: {e}")

                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.debug("File watcher cancelled")

    def update_config_from_dict(
            self, config_dict: dict[str, Any]) -> None:
        """Update configuration from various dictionary formats.

        Note: Per-folder configuration is not supported in CacheManager yet
            this method. Only project-level configuration is applied.

        Support multiple formats::

            - Format 1: {"ProjectName": ["folder1", "folder2"]}
            - Format 2: {"projects": [
                    {"name": "ProjectName", "folders": ["folder1", "folder2"]}
                ]}
            - Format 3: {
                    "cache_config": {"ProjectName": ["folder1", "folder2"]}
                }

        Args:
            config_dict: Configuration in various supported formats

        """
        if "cache_config" in config_dict:
            config = config_dict["cache_config"]
        elif "projects" in config_dict:
            # Convert from project list format
            config = {}
            for project in config_dict["projects"]:
                if "name" in project and "folders" in project:
                    config[project["name"]] = project["folders"]
        else:
            # Assume direct format
            config = config_dict

        # Validate and apply
        if isinstance(config, dict):
            # Ensure all values are lists
            validated_config = {}
            for project_name, folders in config.items():
                if isinstance(folders, list):
                    validated_config[project_name] = folders
                elif isinstance(folders, str):
                    # Single folder as string
                    validated_config[project_name] = [folders]
                else:
                    logger.warning(
                        f"Invalid folders format for project {project_name}")

            self.cache_service.update_cache_configuration(validated_config)
            self._notify_watchers(validated_config)
            logger.info(
                f"Updated configuration for {len(validated_config)} projects")
        else:
            logger.error("Invalid configuration format")

    def update_config_from_env(
            self, env_prefix: str = "AYON_USD_CACHE") -> None:
        """Update configuration from environment variables.

        Args:
            env_prefix: Prefix for environment variables
        """
        config = {}

        # Look for environment variables like:
        # AYON_USD_CACHE_PROJECT1=folder1,folder2,folder3
        # AYON_USD_CACHE_PROJECT2=folder4,folder5

        for key, value in os.environ.items():
            if key.startswith(f"{env_prefix}_"):
                project_name = key[len(f"{env_prefix}_"):]
                if project_name and value:
                    folders = [
                        f.strip() for f in value.split(",") if f.strip()
                    ]
                    config[project_name] = folders

        if config:
            self.cache_service.update_cache_configuration(config)
            self._notify_watchers(config)
            logger.info(
                "Updated configuration from environment "
                f"variables: {len(config)} projects")
        else:
            logger.info(
                "No cache configuration found in environment variables")


# Convenience functions for easy configuration management
async def load_cache_config_from_file(
        cache_service: CacheService, file_path: Path) -> bool:
    """Load and apply cache configuration from file.

    Args:
        cache_service: CacheService instance
        file_path: Path to JSON configuration file

    Returns:
        True if successful

    """
    manager = CacheConfigManager(cache_service)
    try:
        await manager.apply_config_from_file(file_path)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to load config: {e}")
        return False
    else:
        return True


def update_cache_config_from_env(
        cache_service: CacheService,
        prefix: str = "AYON_USD_CACHE") -> None:
    """Update cache configuration from environment variables.

    Args:
        cache_service: CacheService instance
        prefix: Environment variable prefix
    """
    manager = CacheConfigManager(cache_service)
    manager.update_config_from_env(prefix)
