"""Pre-launch hook to initialize asset resolver for the application."""

import json
from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_usd import config, utils


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {"maya", "nuke", "nukestudio", "houdini", "blender", "unreal"}
    launch_types = {LaunchTypes.local}

    def _setup_resolver(self, local_resolver, settings):
        self.log.info(f"Initializing USD asset resolver for [ {self.app_name} ] .")
        env_var_dict = utils.get_resolver_setup_info(
            local_resolver, settings, self.app_name, self.log
        )
        for key in env_var_dict:
            value = env_var_dict[key]
            self.launch_context.env[key] = value

    def execute(self):
        """Pre-launch hook entry method."""

        self.log.debug(self.app_group)
        settings = utils.get_addon_settings()
        resolver_lake_fs_path = utils.get_resolver_to_download(settings, self.app_name)
        if not resolver_lake_fs_path:
            raise RuntimeError(
                "no Resolver could be found but AYON-Usd addon is activated"
            )

        with open(config.ADDON_DATA_JSON_PATH, "r") as data_json:
            addon_data_json = json.load(data_json)

        try:
            key = str(self.app_name).replace("/", "_")
            local_resolver_data = addon_data_json[f"resolver_data_{key}"]

        except KeyError:
            local_resolver_data = None

        lake_fs_resolver_time_stamp = (
            config.get_global_lake_instance().get_element_info(resolver_lake_fs_path)[
                "Modified Time"
            ]
        )

        if (
            local_resolver_data
            and lake_fs_resolver_time_stamp == local_resolver_data[0]
        ):

            self._setup_resolver(local_resolver_data[1], settings)
            return

        local_resolver = utils.download_and_extract_resolver(
            resolver_lake_fs_path, str(utils.get_download_dir())
        )

        if not local_resolver:
            return

        key = str(self.app_name).replace("/", "_")
        addon_data_json[f"resolver_data_{key}"] = [
            config.get_global_lake_instance().get_element_info(resolver_lake_fs_path)[
                "Modified Time"
            ],
            local_resolver,
        ]
        with open(config.ADDON_DATA_JSON_PATH, "w") as addon_json:
            json.dump(addon_data_json, addon_json)

        self._setup_resolver(local_resolver, settings)
