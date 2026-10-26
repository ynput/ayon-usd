"""Pre-launch hook to set USD pinning related environment variable."""
from typing import ClassVar

from ayon_applications import LaunchTypes, PreLaunchHook


class UsdPinningRoot(PreLaunchHook):
    """Pre-launch hook to set USD_ROOT environment variable."""

    app_groups: ClassVar[set[str]] = {"maya", "houdini", "blender", "unreal"}
    # this should be set to farm_render, but this issue
    # https://github.com/ynput/ayon-applications/issues/2
    # stands in the way
    launch_types: ClassVar[set[str]] = {LaunchTypes.farm_publish}

    def execute(self) -> None:
        """Set environments necessary for pinning."""
        if not self.launch_context.env.get("AYON_USD_RESOLVER_PINNING_FILE") \
        and not self.launch_context.env.get("PINNING_FILE_PATH"):
            return

        anatomy = self.data["anatomy"]
        env = self.launch_context.env
        env["AYON_USD_RESOLVER_PINNING_FILE"] = anatomy.fill_root(
            env.get("AYON_USD_RESOLVER_PINNING_FILE"),
        )

        # Backwards compatibility (deprecated)
        self.launch_context.env["PINNING_FILE_PATH"] = anatomy.fill_root(
            self.launch_context.env.get("PINNING_FILE_PATH"),
        )

        roots = anatomy.roots
        pinning_roots = ",".join(
            f"{key}={value}" for key, value in roots.items()
        )

        self.launch_context.env[
            "AYON_USD_RESOLVER_PINNING_ROOTS"
        ] = pinning_roots

        # Backwards compatibility (deprecated)
        self.launch_context.env["PROJECT_ROOTS"] = pinning_roots
