"""Pre-launch hook to set USD pinning related environment variable."""
from ayon_api import get_project
from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_core.pipeline import Anatomy


class UsdPinningRoot(PreLaunchHook):
    """Pre-launch hook to set USD_ROOT environment variable."""

    app_groups = {"maya", "houdini", "blender", "unreal"}
    # this should be set to farm_render, but this issue
    # https://github.com/ynput/ayon-applications/issues/2
    # stands in the way
    launch_types = {LaunchTypes.farm_publish}

    def execute(self) -> None:
        """Set environments necessary for pinning."""
        if not self.launch_context.env.get("PINNING_FILE_PATH"):
            return

        project_entity = get_project(self.data.project_name)
        anatomy = Anatomy(
            self.data.project_name, project_entity=project_entity)
        self.launch_context.env["PINNING_FILE_PATH"] = anatomy.fill_root(
            self.launch_context.env.get("PINNING_FILE_PATH"),
        )

        roots = anatomy.roots()
        self.launch_context.env[
            "PROJECT_ROOTS"
        ] = ",".join(f"{key}={value}"
                     for key, value in roots.items())
