"""Null client to disable caching functionality.

This module provides a NullCacheClient class that
implements the CacheClient interface and is used to
disable caching functionality in the application in
case other cache clients are not desired/available.

"""
from __future__ import annotations

from typing import Any

from ayon_usd.cache_manager.cache_client import CacheClient


class NullCacheClient(CacheClient):
    """Null cache client to disable caching functionality.

    It implements all methods of the CacheClient interface
    but does not perform any caching operations - instead,
    it queries the server directly for all data requests.

    """

    def __init__(self):
        """Initialize the NullCacheClient."""
        super().__init__()

    def connect(self) -> None:
        """Simulate connecting to a cache (no operation)."""

    def disconnect(self) -> None:
        """Simulate disconnecting from a cache (no operation)."""

    def get_data(self, key: str) -> Any:  # noqa: ANN401
        """Simulate getting a value from the cache (always returns None).

        Args:
            key (str): The key to retrieve.

        Returns:
            None: Always returns None since caching is disabled.
        """
        return None

    def set_data(self, key: str, value: Any, ttl: int = 0) -> bool:  # noqa: ANN401
        """Simulate setting a value in the cache (no operation).

        Args:
            key (str): The key to set.
            value (Any): The value to store.
            ttl (int, optional): Expiration time in seconds. Defaults to 0.

        Returns:
            bool: Always returns False since caching is disabled.

        """
        return False

    def delete_data(self, key: str) -> None:
        """Simulate deleting a value from the cache (no operation).

        Args:
            key (str): The key to delete.
        """
        pass

    def set_folder_data(
            self,
            project_name: str,
            folder_id: str,
            data: dict[str, Any],
            ttl: int = 3600) -> bool:
        """Simulate setting folder data in the cache (always returns False).

        Args:
            project_name (str): Name of the project.
            folder_id (str): ID of the folder.
            data (dict[str, Any]): Folder data to store.
            ttl (int, optional): Expiration time in seconds. Defaults to 3600.

        Returns:
            bool: Always returns False since caching is disabled.

        """
        return False

    def invalidate_project_cache(self, project_name: str) -> None:
        """Simulate invalidating project cache (no operation).

        Args:
            project_name (str): Name of the project.
        """

    def get_folder_data(self, project_name: str, folder_id: str) -> dict[str, Any] | None:
        """Retrieve folder data from the cache.

        Args:
            project_name: Name of the project.
            folder_id: ID of the folder.

        Returns:
            dict[str, Any] | None: The folder data from
            the cache or None if not found.

        """
        return None

    def get_project_data(self, project_name: str) -> dict[str, Any] | None:
        """Retrieve project data from the cache.

        Args:
            project_name: Name of the project.

        Returns:
            dict[str, Any] | None: The project data from
                the cache or None if not found.
        """
        return None

    def set_project_data(
            self,
            project_name: str,
            data: dict[str, Any],
            ttl: int = 3600) -> bool:
        """Set project data in the cache.

        Args:
            project_name: Name of the project.
            data: Project data to store.
            ttl: Expiration time in seconds. Defaults to 3600.

        Returns:
            bool: True if the data was set successfully.
        """
        return False

    def invalidate_folder(self, project_name: str, folder_id: str) -> bool:
        """Invalidate folder data in the cache.

        Args:
            project_name: Name of the project.
            folder_id: ID of the folder.

        Returns:
            bool: True if the folder was invalidated successfully.

        """
        return False

    def invalidate_project(self, project_name: str) -> int:
        """Invalidate project data in the cache.

        Args:
            project_name: Name of the project.

        Returns:
            int: Number of invalidated entries.
        """
        return 0

    def flush_all(self) -> bool:
        """Flush all cache data.

        Returns:
            bool: True if the cache was flushed successfully.
        """
        return False

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            dict[str, Any]: An empty dictionary since caching is disabled.
        """
        return {}
