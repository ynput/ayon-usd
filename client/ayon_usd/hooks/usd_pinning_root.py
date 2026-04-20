"""Pre-launch hook to set USD pinning related environment variable."""
from ayon_applications import LaunchTypes, PreLaunchHook


class UsdPinningRoot(PreLaunchHook):
    """Pre-launch hook to set USD_ROOT environment variable."""

    app_groups = {"maya", "houdini", "blender", "unreal"}
    # this should be set to farm_render, but this issue
    # https://github.com/ynput/ayon-applications/issues/2
    # stands in the way
    launch_types = {LaunchTypes.farm_publish}

    def execute(self) -> None:
        """Set environments necessary for pinning."""
        if not self.launch_context.env.get("AYON_USD_RESOLVER_PINNING_FILE"):
            return

        anatomy = self.data["anatomy"]
        self.launch_context.env["AYON_USD_RESOLVER_PINNING_FILE"] = anatomy.fill_root(
            self.launch_context.env.get("AYON_USD_RESOLVER_PINNING_FILE"),
        )

        roots = anatomy.roots
        self.launch_context.env[
            "AYON_USD_RESOLVER_PINNING_ROOTS"
        ] = ",".join(f"{key}={value}"
                     for key, value in roots.items())
