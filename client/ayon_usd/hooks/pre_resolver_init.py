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
    # TODO Use `farm_render` instead of `farm_publish`
    # once this issue is resolved
    # https://github.com/ynput/ayon-applications/issues/2
    launch_types = {LaunchTypes.local, LaunchTypes.farm_publish}

    def execute(self):
        """Pre-launch hook entry method."""
        project_settings = self.data["project_settings"]
        local_resolver = None

        is_farm = (
            hasattr(self, "launch_type")
            and self.launch_type == LaunchTypes.farm_publish
        )

        if project_settings["usd"]["local_ditribution"]["enabled"] \
        and (is_farm or project_settings["usd"]["local_ditribution"]["prefer"]):
            local_resolver = self._handle_local_distribution(project_settings)

        if not local_resolver and project_settings["usd"]["lake_fs_distribution"]["enabled"]:
            local_resolver = self._handle_lake_fs_distribution(project_settings)
            
        # fallback if LakeFS wasn't succesful or is disabled, but local distribution is enabled
        if not local_resolver and project_settings["usd"]["local_ditribution"]["enabled"]:
            local_resolver = self._handle_local_distribution(project_settings)

        if not local_resolver:
            return
        
        self._setup_resolver(local_resolver, project_settings)
    
    def _handle_lake_fs_distribution(self, settings):
        resolver_lake_fs_path = utils.get_resolver_to_download(
            settings,
            self.app_name
        )

        if not resolver_lake_fs_path:
            self.log.warning(
                "No USD Resolver could be found but AYON-Usd addon is"
                f" activated for application: {self.app_name}"
            )
            return None
    
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
            return None
        
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
            return local_resolver
        
        # If no existing match, download the resolver
        local_resolver = utils.lakefs_download_and_extract(
            resolver_lake_fs_path, str(utils.get_download_dir())
        )
        if not local_resolver:
            return None

        addon_data_json[local_resolver_key] = [
            lake_fs_resolver_time_stamp,
            local_resolver,
        ]
        with open(ADDON_DATA_JSON_PATH, "w") as addon_json:
            json.dump(addon_data_json, addon_json)
        
        return local_resolver

    def _handle_local_distribution(self, settings):
        resolver_path = utils.get_local_resolver_path(
            settings,
            self.app_name
        )

        if resolver_path:
            if not os.path.isdir(resolver_path):
                self.log.error(
                    f"Local resolver path does not exist: {resolver_path}"
                )
                return None
            self.log.info(
                f"Using local resolver path for {self.app_name}: {resolver_path}"
            )
        
        return resolver_path

    def _setup_resolver(self, local_resolver, settings):
        self.log.info(
            f"Initializing USD asset resolver for application: {self.app_name}"
        )

        updated_env = utils.get_resolver_setup_info(
            local_resolver, settings, env=self.launch_context.env
        )
        self.launch_context.env.update(updated_env)
