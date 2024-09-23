"""Pre-launch hook to set USD pinning related environment variable."""
from typing import ClassVar

from ayon_applications import LaunchTypes, PreLaunchHook


class UsdPinningRoot(PreLaunchHook):
    """Pre-launch hook to set USD_ROOT environment variable."""

    app_groups: ClassVar = {"maya", "houdini", "blender", "unreal"}
    # this should be set to farm_render, but this issue
    # https://github.com/ynput/ayon-applications/issues/2
    # stands in the way
    launch_types: ClassVar = {LaunchTypes.farm_publish}

    def execute(self) -> None:
        """Set environments necessary for pinning."""
        if self.launch_context.env.get("PINNING_FILE_PATH"):
            return
        anatomy = self.launch_context.anatomy
        self.launch_context.env["PINNING_FILE_PATH"] = anatomy.fill_root(
            self.launch_context.env.get("PINNING_FILE_PATH"),
        )

        roots = anatomy.roots()
        self.launch_context.env[
            "PROJECT_ROOTS"
        ] = ",".join(f"{key}={value}"
                     for key, value in roots.items())
