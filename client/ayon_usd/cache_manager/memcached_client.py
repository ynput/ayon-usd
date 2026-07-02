"""Memcached client for caching AYON hierarchy data."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from pymemcache.client.base import Client
from pymemcache.client.hash import HashClient

from .cache_client import CacheClient


class MemcachedClient(CacheClient):
    """Wrapper for pymemcache with AYON-specific caching logic."""

    def __init__(self, hosts: list[str]):
        """Initialize memcached client.

        Args:
            hosts: List of Memcached server hosts in the format "host:port"

        """
        self.hosts = hosts
        self._client: Client | None = None

        self._key_tracker: set[str] = set()  # Track keys for invalidation

    def connect(self) -> None:
        """Connect to memcached server.

        Raises:
            ValueError: If no hosts are provided.

        """
        if not self.hosts:
            logger.error("No memcached hosts provided")
            msg = (
                "Memcached connection skipped because no "
                "hosts were provided."
            )
            raise ValueError(msg)

        try:
            if len(self.hosts) > 1:
                # when more than one host is provided, we will assume it's a cluster
                # and we'll create HashClient which will distribute keys across the cluster
                self._client = HashClient(self.hosts)
            else:
                self._client = Client(
                    self.hosts[0],
                    # serde=serde.CompressedSerde,
                    connect_timeout=5.0,
                    timeout=10.0
            )
            # Test connection
            self._client.version()
            if isinstance(self._client, HashClient):
                logger.info(f"Connected to memcached cluster at {', '.join(self.hosts)}")
            else:
                logger.info(f"Connected to memcached at {self.hosts[0]}")
        except Exception as e:
            logger.exception(f"Failed to connect to memcached: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from memcached server."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Disconnected from memcached")

    @staticmethod
    def _generate_key(
            project_name: str,
            folder_id: str,
            data_type: str = "folder") -> str:
        """Generate a cache key for the data.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder
            data_type: Type of data (folder, products, tasks)

        Returns:
            Cache key string
        """
        key_base = f"ayon:{project_name}:{folder_id}:{data_type}"
        # Use hash for consistent key length
        key_hash = hashlib.md5(key_base.encode()).hexdigest()  # noqa: S324
        return f"ayon_{key_hash}"

    @staticmethod
    def _generate_metadata_key(cache_key: str) -> str:
        """Generate metadata key for cache entry.

        Args:
            cache_key: Original cache key

        Returns:
            Metadata cache key string

        """
        return f"{cache_key}_meta"

    def set_data(
            self,
            key: str,
            value: Any,  # noqa: ANN401
            ttl: int = 3600) -> bool:
        """Set a value in cache.

        Args:
            key: The key under which to store the value
            value: The value to store in the cache
            ttl: Expiration time in seconds (default is 3600 seconds)

        Returns:
            True if the value was stored successfully, False otherwise

        """
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        success = False

        try:
            success = self._client.set(key=key, value=value, expire=ttl)
            logger.debug(f"Set data for key: {key}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to set data for key {key}: {e}")

        return bool(success)

    def set_folder_data(
            self,
            project_name: str,
            folder_id: str,
            data: dict[str, Any],
            ttl: int = 3600) -> bool:
        """Store folder data in cache.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder
            data: Folder data to store
            ttl: Time to live in seconds

        Returns:
            True if stored successfully, False otherwise
        """
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        try:
            cache_key = self._generate_key(project_name, folder_id, "folder")
            metadata_key = self._generate_metadata_key(cache_key)

            # Store main data
            success = self.set_data(cache_key, data, ttl)
            # success = self._client.set(cache_key, data, expire=ttl)

            if success:
                # Store metadata for tracking
                metadata = {
                    "project_name": project_name,
                    "folder_id": folder_id,
                    "cached_at": datetime.now(tz=UTC).isoformat(),
                    "ttl": ttl,
                    "data_type": "folder"
                }
                # Keep metadata a bit longer
                self.set_data(metadata_key, metadata, ttl + 300)

                # Track key for invalidation
                self._key_tracker.add(cache_key)

                logger.debug(
                    f"Stored folder data for {project_name}:{folder_id}")
                return True

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to store folder data: {e}")

        return False

    def get_data(self, key: str) -> Any:  # noqa: ANN401
        """Retrieve a value from the cache by key.

        Args:
            key: The key to look up in the cache.

        Returns:
            The cached value, or None if not found.

        """
        if not self._client:
            logger.error("Not connected to memcached")
            return None

        try:
            data = self._client.get(key)

            if not data:
                logger.debug(f"No cached data found for key {key}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to retrieve data for key {key}: {e}")
        else:
            return data

        return None

    def get_folder_data(
            self,
            project_name: str, folder_id: str) -> dict[str, Any] | None:
        """Retrieve folder data from cache.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder

        Returns:
            Cached folder data or None if not found
        """
        cache_key = self._generate_key(project_name, folder_id, "folder")
        return self.get_data(cache_key)

    def invalidate_folder(self, project_name: str, folder_id: str) -> bool:
        """Invalidate cached data for a specific folder.

        Args:
            project_name: Name of the project
            folder_id: ID of the folder

        Returns:
            True if invalidated successfully
        """
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        try:
            cache_key = self._generate_key(project_name, folder_id, "folder")
            metadata_key = self._generate_metadata_key(cache_key)

            # Delete both data and metadata
            self._client.delete(cache_key)
            self._client.delete(metadata_key)

            # Remove from tracker
            self._key_tracker.discard(cache_key)

            logger.info(f"Invalidated cache for {project_name}:{folder_id}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to invalidate folder cache: {e}")
            return False
        else:
            return True

    def invalidate_project(self, project_name: str) -> bool:
        """Invalidate all cached data for a project.

        Args:
            project_name: Name of the project

        Returns:
            True if invalidated successfully
        """
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        invalidated_count = 0

        # We need to track keys better for project-level invalidation
        # For now, we'll use a simple pattern matching approach
        try:
            # This is a simplified approach - in production you'd want
            # a more sophisticated key tracking system
            keys_to_remove = []
            for key in self._key_tracker.copy():
                # Get metadata to check project
                metadata_key = self._generate_metadata_key(key)
                metadata = self._client.get(metadata_key)

                if metadata and metadata.get("project_name") == project_name:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                metadata_key = self._generate_metadata_key(key)
                self._client.delete(key)
                self._client.delete(metadata_key)
                self._key_tracker.discard(key)
                invalidated_count += 1

            logger.info(
                f"Invalidated {invalidated_count} cache "
                f"entries for project {project_name}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to invalidate project cache: {e}")
            return False
        else:
            return True

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self._client:
            return {"error": "Not connected to memcached"}

        try:
            stats = self._client.stats()
            return {
                "memcached_stats": stats,
                "tracked_keys": len(self._key_tracker),
                "connected": True
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e), "connected": False}

    def flush_all(self) -> bool:
        """Flush all cache data.

        Returns:
            True if successful
        """
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        try:
            self._client.flush_all()
            self._key_tracker.clear()
            logger.info("Flushed all cache data")
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to flush cache: {e}")
            return False
        else:
            return True

    def delete_data(self, key: str) -> None:
        """Delete a value from the cache by key.

        Args:
            key: The key to delete from the cache.

        """
        if not self._client:
            logger.error("Not connected to memcached")
            return

        self._client.delete(key)
        self._key_tracker.discard(key)
        logger.debug(f"Deleted data for key: {key}")

    def invalidate_project_cache(self, project_name: str) -> None:
        """Invalidate all cache entries related to a specific project.

        Args:
            project_name: Name of the project
                whose cache entries should be invalidated.
        """
        self.invalidate_project(project_name)

    def get_project_data(
            self,
            project_name: str) -> dict[str, Any] | None:
        """Retrieve project data from the cache.

        Args:
            project_name: Name of the project.

        Returns:
            Cached project data or None if not found.

        """
        if not self._client:
            logger.error("Not connected to memcached")
            return None

        return self._client.get(project_name)

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
        if not self._client:
            logger.error("Not connected to memcached")
            return False

        try:
            success = self._client.set(
                key=project_name,
                value=data,
                expire=ttl
            )
            if success:
                logger.debug(f"Stored project data for {project_name}")
                return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to store project data: {e}")

        return False
