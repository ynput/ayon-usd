"""Pre-launch hook to initialize asset resolver for the application."""

import os
import sys
import pathlib
from platform import system

from ayon_applications import LaunchTypes, PreLaunchHook

# TODO fix the imports to import module not function
from ayon_usd import utils
from ayon_usd.ayon_bin_client.ayon_bin_distro import util
from ayon_usd import get_download_dir, config
from ayon_usd import utils

from ayon_usd.ayon_bin_client.ayon_bin_distro.work_handler import worker
from ayon_usd.ayon_bin_client.ayon_bin_distro.util import zip


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
            resolver_lake_fs_path, get_download_dir()
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
