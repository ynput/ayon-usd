"""Add the AYON USD startup script to Maya's Python path."""

import os

from ayon_applications import LaunchTypes, PreLaunchHook


MAYA_STARTUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "startup",
    "maya",
)


class SetupAssetResolver(PreLaunchHook):
    """Configure the AYON USD startup script for Maya."""

    # Must run after InitializeAssetResolver.
    order = 20

    app_groups = {"maya"}
    launch_types = {
        LaunchTypes.local,
        LaunchTypes.farm_publish,
    }

    def execute(self):
        """Add the AYON USD Maya startup directory to PYTHONPATH."""
        project_settings = self.data["project_settings"]
        if not project_settings["usd"]["app_setup"]["maya"]:
            return

        user_setup_path = os.path.join(
            MAYA_STARTUP_DIR,
            "userSetup.py",
        )

        if not os.path.isfile(user_setup_path):
            raise RuntimeError(
                "AYON USD Maya userSetup.py was not found: "
                f"{user_setup_path}"
            )

        env = self.launch_context.env
        paths = [MAYA_STARTUP_DIR]
        current_pythonpath = env.get("PYTHONPATH")
        if current_pythonpath:
            paths.append(current_pythonpath)

        env["PYTHONPATH"] = os.pathsep.join(paths)

        self.log.info(
            "Added AYON USD Maya startup directory: %s",
            MAYA_STARTUP_DIR,
        )
