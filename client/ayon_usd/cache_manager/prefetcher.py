"""Prefetch manager for caching system.

This module defines a prefetch manager that interacts with a cache client
to prefetch and store data, improving performance by reducing redundant
data fetching.

It takes all context associated with the current user - based
on tasks assigned, it will calculate folders and projects to
prefetch and store in cache.

"""
from __future__ import annotations

from typing import NamedTuple, TypedDict

import ayon_api


class PrefetchFolderRequest(NamedTuple):
    """Structure representing a prefetch request."""
    project_name: str
    folder_id: str


class PrefetchProjectRequest(NamedTuple):
    """Structure representing a prefetch request."""
    project_name: str


class PrefetchRequests(NamedTuple):
    """Structure representing prefetch requests."""
    folder_requests: set[PrefetchFolderRequest]
    project_requests: set[PrefetchProjectRequest]


class PrefetchError(Exception):
    """Custom exception for prefetching errors."""


class AssignedTask(TypedDict):
    """Structure representing an assigned task."""
    project_name: str
    folder_id: str
    parent_id: str
    task_id: str


class Prefetcher:
    """Prefetch manager for caching system."""

    def __init__(self, user: str) -> None:
        """Initialize the prefetcher with a cache client.

        Args:
            user: The name of the user whose data should be prefetched.
            cache_client: An instance of a cache client
            implementing the CacheClient protocol.
        """
        self._user = user

    @staticmethod
    def get_assigned_tasks(user_name: str) -> list[AssignedTask]:
        """Get assigned tasks across active projects for a specific user.

        This is a helper method that can be used to identify which folders
        and projects need to be prefetched based on the user's assigned tasks.

        Args:
            user_name: The name of the user whose assigned
            tasks are to be fetched.

        Returns:
            A list of assigned tasks for the user.

        Raises:
            PrefetchError: If there is an error fetching the assigned tasks.

        """
        assigned_tasks = []
        graphql_query = """query GetUserAssignedTasks($userName: String!) {
  projects {
    edges {
      node {
        projectName
        active
        tasks(assignees: [$userName]) {
          edges {
            node {
              id
              folderId
              folder {
                parentId
              }
            }
          }
        }
      }
    }
  }
}
"""
        response = ayon_api.query_graphql(
            graphql_query, variables={"userName": user_name})

        data = response.data["data"]

        if response.errors:
            msg = (f"Error fetching assigned tasks for user {user_name}: "
                   f"{response.errors}")
            raise PrefetchError(msg)
        for project_edge in data["projects"]["edges"]:
            project_node = project_edge["node"]
            if not project_node["active"]:
                continue
            project_name = project_node["projectName"]
            for task_edge in project_node["tasks"]["edges"]:
                task_node = task_edge["node"]
                assigned_tasks.append(
                    AssignedTask(
                        project_name=project_name,
                        folder_id=task_node["folderId"],
                        parent_id=task_node["folder"]["parentId"],
                        task_id=task_node["id"],
                    )
                )

        return assigned_tasks

    def prefetch_user_folders(
            self, user_name: str) -> set[PrefetchFolderRequest]:
        """Prefetch folder hierarchy for all tasks assigned to a user.

        This takes all folders associated with tasks assigned to the user
        and prefetches them and their parent folders into the cache.

        Args:
            user_name: The name of the user whose folders should be prefetched.

        Returns:
            A set of folder IDs that were prefetched.

        """
        assigned_tasks = self.get_assigned_tasks(user_name)

        # Collect unique folder IDs to prefetch and their parent folders
        folder_ids_to_prefetch = set()
        for task in assigned_tasks:
            folder_ids_to_prefetch.add(
                PrefetchFolderRequest(task["project_name"], task["folder_id"]))
            if task["parent_id"]:
                folder_ids_to_prefetch.add(
                    PrefetchFolderRequest(
                        task["project_name"], task["parent_id"]))
                # fetch parent folders recursively if needed
                parent_id = task["parent_id"]
                while parent_id:
                    folder_data = ayon_api.get_folder_by_id(
                        project_name=task["project_name"], folder_id=parent_id)
                    if folder_data and folder_data.get("parentId"):
                        parent_id = folder_data["parentId"]
                        folder_ids_to_prefetch.add(
                            PrefetchFolderRequest(
                                task["project_name"], parent_id))
                    else:
                        break
        return folder_ids_to_prefetch

    def prefetch(self) -> PrefetchRequests:
        """Prefetch folder hierarchy for the initialized user.

        This takes all folders associated with tasks assigned to the user
        and prefetches them and their parent folders into the cache.

        Returns:
            A set of folder IDs that were prefetched.

        """
        folder_requests = self.prefetch_user_folders(self._user)
        project_requests = {
            PrefetchProjectRequest(request.project_name)
            for request in folder_requests
        }

        return PrefetchRequests(folder_requests, project_requests)
