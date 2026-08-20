"""Setup USD roots for memcached resolver."""
from __future__ import annotations

from typing import ClassVar

from ayon_applications import LaunchTypes, PreLaunchHook


class UsdRootsEnv(PreLaunchHook):
    """Pre-launch hook to set USD_ROOT environment variable."""

    app_groups: ClassVar[set[str]] = {
        "maya", "houdini", "blender", "unreal"
    }
    launch_types: ClassVar[set[LaunchTypes]] = {
        LaunchTypes.local, LaunchTypes.farm_publish
    }

    def execute(self) -> None:
        """Execute the pre-launch hook."""
        anatomy = self.data["anatomy"]
        roots = anatomy.roots
        pinning_roots = ",".join(
            f"{key}={value}" for key, value in roots.items()
        )

        self.launch_context.env[
            "AYON_USD_RESOLVER_PINNING_ROOTS"
        ] = pinning_roots
