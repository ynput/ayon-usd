"""Add the AYON USD Maya startup script."""

import os

from ayon_applications import LaunchTypes, PreLaunchHook


ADDON_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MAYA_STARTUP_DIR = os.path.join(
    ADDON_ROOT,
    "startup",
    "maya",
)


class SetupAssetResolver(PreLaunchHook):
    """Add AYON USD initialization to Maya startup."""

    app_groups = {"maya"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        env = self.launch_context.env

        current_pythonpath = env.get("PYTHONPATH") or ""

        python_paths = [MAYA_STARTUP_DIR]

        for path in current_pythonpath.split(os.pathsep):
            if not path:
                continue

            normalized_path = os.path.normpath(path)
            if normalized_path not in python_paths:
                python_paths.append(normalized_path)

        env["PYTHONPATH"] = os.pathsep.join(python_paths)

        self.log.debug(
            "Added AYON USD Maya startup path: %s",
            MAYA_STARTUP_DIR,
        )