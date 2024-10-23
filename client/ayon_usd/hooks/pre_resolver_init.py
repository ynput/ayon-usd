"""Pre-launch hook to initialize asset resolver for the application."""

import json
import os
from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_usd import config, utils
from ayon_usd.addon import ADDON_DATA_JSON_PATH


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {"maya", "houdini", "unreal"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        """Pre-launch hook entry method."""
        project_settings = self.data["project_settings"]
        if not project_settings["usd"]["distribution"].get("enabled", False):
            self.log.info(
                "USD Binary distribution for AYON USD Resolver is"
                " disabled.")
            return

        resolver_lake_fs_path = utils.get_resolver_to_download(
            project_settings, self.app_name)
        if not resolver_lake_fs_path:
            self.log.warning(
                "No USD Resolver could be found but AYON-Usd addon is"
                f" activated for application: {self.app_name}"
            )
            return

        self.log.info(f"Using resolver from lakeFS: {resolver_lake_fs_path}")
        lake_fs = config.get_global_lake_instance()
        lake_fs_resolver_time_stamp = (
            lake_fs.get_element_info(resolver_lake_fs_path).get(
                "Modified Time"
            )
        )
        if not lake_fs_resolver_time_stamp:
            self.log.error(
                "Could not find resolver timestamp on lakeFS server "
                f"for application: {self.app_name}"
            )
            return

        # Check for existing local resolver that matches the lakefs timestamp
        with open(ADDON_DATA_JSON_PATH, "r") as data_json:
            addon_data_json = json.load(data_json)

        key = str(self.app_name).replace("/", "_")
        local_resolver_key = f"resolver_data_{key}"
        local_resolver_timestamp, local_resolver = (
            addon_data_json.get(local_resolver_key, [None, None])
        )

        if (
            local_resolver
            and lake_fs_resolver_time_stamp == local_resolver_timestamp
            and os.path.exists(local_resolver)
        ):
            self._setup_resolver(local_resolver, project_settings)
            return

        # If no existing match, download the resolver
        local_resolver = utils.lakefs_download_and_extract(
            resolver_lake_fs_path, str(utils.get_download_dir())
        )
        if not local_resolver:
            return

        addon_data_json[local_resolver_key] = [
            lake_fs_resolver_time_stamp,
            local_resolver,
        ]
        with open(ADDON_DATA_JSON_PATH, "w") as addon_json:
            json.dump(addon_data_json, addon_json)

        self._setup_resolver(local_resolver, project_settings)

    def _setup_resolver(self, local_resolver, settings):
        self.log.info(
            f"Initializing USD asset resolver for application: {self.app_name}"
        )

        updated_env = utils.get_resolver_setup_info(
            local_resolver, settings, env=self.launch_context.env
        )
        self.launch_context.env.update(updated_env)
