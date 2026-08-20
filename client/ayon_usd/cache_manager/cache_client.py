"""Interface for caching clients.

This module provides an interface for caching clients, allowing for
different caching backends to be implemented and used interchangeably.

"""
from __future__ import annotations

from typing import Any, Optional, Protocol


class CacheClient(Protocol):
    """Protocol for cache clients."""

    def connect(self) -> None:
        """Connect to the cache server."""
        ...

    def disconnect(self) -> None:
        """Disconnect from the cache server."""
        ...

    def get_data(self, key: str) -> Any:  # noqa: ANN401
        """Retrieve a value from the cache by key.

        Args:
            key: The key to look up in the cache.

        Returns:
            The cached value, or None if not found.
        """
        ...

    def set_data(self, key: str, value: Any, ttl: int = 3600) -> bool:  # noqa: ANN401
        """Set a value in the cache with an optional expiration time.

        Args:
            key: The key under which to store the value.
            value: The value to store in the cache.
            ttl: Expiration time in seconds (default is 3600 seconds).

        Returns:
            True if the value was stored successfully, False otherwise.

        """
        ...

    def delete_data(self, key: str) -> None:
        """Delete a value from the cache by key.

        Args:
            key: The key to delete from the cache.
        """
        ...

    def get_folder_data(
            self,
            project_name: str,
            folder_id: str) -> Optional[dict[str, Any]]:
        """Retrieve folder data from the cache.

        Args:
            project_name: Name of the project.
            folder_id: ID of the folder.

        Returns:
            Cached folder data or None if not found.
        """
        ...

    def set_folder_data(
            self,
            project_name: str,
            folder_id: str,
            data: dict[str, Any],
            ttl: int = 3600) -> bool:
        """Store folder data in the cache.

        Args:
            project_name: Name of the project.
            folder_id: ID of the folder.
            data: Folder data to cache.
            ttl: Time to live in seconds (default is 3600 seconds).

        Returns:
            True if stored successfully, False otherwise.
        """
        ...

    def get_project_data(
            self,
            project_name: str) -> Optional[dict[str, Any]]:
        """Retrieve project data from the cache.

        Args:
            project_name: Name of the project.

        Returns:
            Cached project data or None if not found.

        """
        ...

    def set_project_data(
            self,
            project_name: str,
            data: dict[str, Any],
            ttl: int = 3600) -> bool:
        """Store project data in the cache.

        Args:
            project_name: Name of the project.
            data: Project data to cache.
            ttl: Time to live in seconds (default is 3600 seconds).

        Returns:
            True if stored successfully, False otherwise.

        """
        ...

    def invalidate_project_cache(self, project_name: str) -> None:
        """Invalidate all cache entries related to a specific project.

        Args:
            project_name: Name of the project
                whose cache entries should be invalidated.
        """
        ...

    def invalidate_folder(self, project_name: str, folder_id: str) -> int:
        """Invalidate cached data for a specific folder.

        Args:
            project_name: Name of the project.
            folder_id: ID of the folder.

        Returns:
            Number of invalidated entries.
        """
        ...

    def flush_all(self) -> bool:
        """Clear all entries in the cache.

        Returns:
            True if the cache was successfully cleared.

        """
        ...

    def invalidate_project(self, project_name: str) -> bool:
        """Invalidate cached data for a specific project.

        Args:
            project_name: Name of the project.

        Returns:
            True if invalidated successfully.

        """
        ...
