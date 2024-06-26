"""Pre-launch hook to initialize asset resolver for the application."""

from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_usd import utils


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {"maya", "nuke", "nukestudio", "houdini", "blender", "unreal"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        """Pre-launch hook entry method."""

        self.log.debug(self.app_group)
        settings = utils.get_addon_settings()
        resolver_lake_fs_path = utils.get_resolver_to_download(settings, self.app_name)
        if not resolver_lake_fs_path:
            return

        local_resolver = utils.download_and_extract_resolver(
            resolver_lake_fs_path, str(utils.get_download_dir())
        )

        if not local_resolver:
            return

        self.log.info(f"Initializing USD asset resolver for [ {self.app_name} ] .")
        env_var_dict = utils.get_resolver_setup_info(
            local_resolver, settings, self.app_name, self.log
        )
        for key in env_var_dict:
            value = env_var_dict[key]
            self.launch_context.env[key] = value
