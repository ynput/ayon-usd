from platform import system
from ayon_applications import PreLaunchHook, LaunchTypes


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {
        "maya",
        "nuke",
        "nukestudio",
        "houdini",
        "blender",
        "unreal"
    }
    launch_types = {LaunchTypes.local}

    def execute(self):

        resolver_settings = self.data["project_settings"]["usd"]["asset_resolvers"]  # noqa: E501
        # project_name = self.data["project_name"]
        host_name = self.application.host_name
        variant = self.application.variant

        host_variant = f"{host_name}/{variant}"
        for resolver in resolver_settings:
            if resolver["app_name"] != host_variant:
                continue

            if resolver["platform"].lower() != system().lower():
                continue



        if host_variant not in resolver_settings[""]:
            self.log.info(f"No asset resolver settings for {host_variant}.")
            return

        if system().lower() == "windows":
            self.launch_context.env["AYON_ASSET_RESOLVER"] = "1"
        else:
            self.launch_context.env["AYON_ASSET_RESOLVER"] = "0"
        self.log.info("Asset resolver initialized.")