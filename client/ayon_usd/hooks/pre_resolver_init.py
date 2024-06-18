"""Pre-launch hook to initialize asset resolver for the application."""

import os
import sys
import pathlib
from platform import system

from ayon_applications import LaunchTypes, PreLaunchHook

from ayon_usd.utils import get_addon_settings
from ayon_usd import get_download_dir, extract_zip_file, config

from ayon_bin_bridge_client.ayon_bin_distro.work_handler import worker


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {"maya", "nuke", "nukestudio", "houdini", "blender", "unreal"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        """Pre-launch hook entry method."""

        self.log.debug(self.app_group)
        settings = get_addon_settings()

        resolver_lake_fs_path = self._get_resolver_to_download(settings)
        if not resolver_lake_fs_path:
            return

        local_resolver = self._download_and_extract_resolver(
            resolver_lake_fs_path, get_download_dir()
        )
        if not local_resolver:
            return

        self.log.info(f"Initializing USD asset resolver for [ {self.app_name} ] .")
        self._setup_resolver(local_resolver, settings)

    def _download_and_extract_resolver(
        self, resolver_lake_fs_path, download_dir
    ) -> str:
        controller = worker.Controller()
        download_item = controller.construct_work_item(
            func=config.lake_ctl_instance_glob.clone_element,
            args=[resolver_lake_fs_path, download_dir],
        )
        # zip_path = config.lake_ctl_instance_glob.clone_element(
        #     None, resolver_lake_fs_path, download_dir
        # )
        extract_zip_item = controller.construct_work_item(
            func=extract_zip_file, args=[download_item.func_return, download_dir, dependency_id=download_item.get_uuid()]
        )
        # extract_zip_file(None, zip_path, download_dir)

        return os.path.abspath(
            os.path.join(
                download_dir,
                os.path.basename(extract_zip_item.func_return).split(".")[0],
            )
        )

    def _get_resolver_to_download(self, settings) -> str:
        """
        gets lakeFs path that can be used with copy element to download specific resolver, this will priorities lake_fs_overwrites over asset_resolvers entry's

        Returns: str: lakeFs object path to be used with lake_fs_py wrapper

        """

        resolver_overwrite = next(
            (
                item
                for item in settings["lake_fs_overwrites"]
                if item["app_name"] == self.app_name
                and item["platform"] == sys.platform.lower()
            ),
            None,
        )
        if resolver_overwrite:
            return resolver_overwrite["lake_fs_path"]

        resolver = next(
            (
                item
                for item in settings["asset_resolvers"]
                if item["app_name"] == self.app_name
                and item["platform"] == sys.platform.lower()
            ),
            None,
        )
        if not resolver:
            return ""
        lake_base_path = settings["ayon_usd_lake_fs_server_repo"]
        resolver_lake_path = lake_base_path + resolver["lake_fs_path"]
        return resolver_lake_path

    def _setup_resolver(self, resolver_dir, settings):
        pxr_plugin_paths = []
        ld_path = []
        python_path = []

        resolver_plugin_info_path = os.path.join(
            resolver_dir, "ayonUsdResolver", "resources", "plugInfo.json"
        )
        resolver_ld_path = os.path.join(resolver_dir, "ayonUsdResolver", "lib")
        resolver_python_path = os.path.join(
            resolver_dir, "ayonUsdResolver", "lib", "python"
        )

        if (
            not os.path.exists(resolver_python_path)
            and os.path.exists(resolver_ld_path)
            and os.path.exists(resolver_python_path)
        ):
            raise RuntimeError(
                f"Cant start Resolver missing path resolver_python_path: {resolver_python_path}, resolver_ld_path: {resolver_ld_path}, resolver_python_path: {resolver_python_path}"
            )
        pxr_plugin_paths.append(pathlib.Path(resolver_plugin_info_path).as_posix())
        ld_path.append(pathlib.Path(resolver_ld_path).as_posix())
        python_path.append(pathlib.Path(resolver_python_path).as_posix())

        self.log.info(f"Asset resolver {self.app_name} initiated.")

        if self.launch_context.env.get("PXR_PLUGINPATH_NAME"):
            pxr_plugin_paths.append(
                self.launch_context.env["PXR_PLUGINPATH_NAME"].split(os.pathsep)
            )

        self.launch_context.env["PXR_PLUGINPATH_NAME"] = os.pathsep.join(
            pxr_plugin_paths
        )

        self.launch_context.env["PYTHONPATH"] += os.pathsep.join(python_path)

        if system().lower() == "windows":
            self.launch_context.env["PATH"] += os.pathsep.join(ld_path)
        else:
            self.launch_context.env["LD_LIBRARY_PATH"] = os.pathsep.join(ld_path)

        self.launch_context.env["TF_DEBUG"] = settings["usd_tf_debug"]

        self.launch_context.env["AYONLOGGERLOGLVL"] = settings["ayon_log_lvl"]
        self.launch_context.env["AYONLOGGERSFILELOGGING"] = settings[
            "ayon_file_logger_enabled"
        ]
        self.launch_context.env["AYONLOGGERSFILEPOS"] = ["file_logger_file_path"]

        self.launch_context.env["AYON_LOGGIN_LOGGIN_KEYS"] = ["file_logger_file_path"]
