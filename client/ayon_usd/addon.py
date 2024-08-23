"""USD Addon for AYON."""

import json
import os
from datetime import datetime, timezone

from ayon_core.addon import AYONAddon, ITrayAddon

from ayon_core import style

from . import config, utils

from .ayon_bin_client.ayon_bin_distro.gui import progress_ui
from .ayon_bin_client.ayon_bin_distro.work_handler import worker
from .ayon_bin_client.ayon_bin_distro.util import zip

USD_ADDON_ROOT = os.path.dirname(os.path.abspath(__file__))


class USDAddon(AYONAddon, ITrayAddon):
    """Addon to add USD Support to AYON.

    Addon can also skip distribution of binaries from server and can
    use path/arguments defined by server.

    Cares about supplying USD Framework.
    """

    name = config.ADDON_NAME
    version = config.ADDON_VERSION
    _download_window = None

    def tray_init(self):
        """Initialize tray module."""
        super(USDAddon, self).tray_init()

    def initialize(self, module_settings):
        """Initialize USD Addon."""
        if not module_settings["ayon_usd"]["allow_addon_start"]:
            raise SystemError(
                "The experimental AyonUsd addon is currently activated, but you haven't yet acknowledged the user agreement indicating your understanding that this feature is experimental. Please go to the Studio settings and check the agreement checkbox."
            )
        self.enabled = True
        self._download_window = None

    def tray_start(self):
        """Start tray module.

        Download USD if needed.
        """
        super(USDAddon, self).tray_start()

        if not os.path.exists(config.DOWNLOAD_DIR):
            os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        if os.path.exists(str(config.DOWNLOAD_DIR) + ".zip"):
            os.remove(str(config.DOWNLOAD_DIR) + ".zip")
        if not os.path.exists(config.ADDON_DATA_JSON_PATH):
            with open(config.ADDON_DATA_JSON_PATH, "w+") as data_json:
                init_data = {}
                init_data["ayon_usd_addon_first_init_utc"] = str(
                    datetime.now().astimezone(timezone.utc)
                )
                json.dump(
                    init_data,
                    data_json,
                )

        if not utils.is_usd_lib_download_needed():
            print("usd is already downloaded")
            return

        lake_fs_usd_lib_path = f"{config.get_addon_settings_value(config.get_addon_settings(),config.ADDON_SETTINGS_LAKE_FS_REPO_URI)}{config.get_usd_lib_conf_from_lakefs()}"

        usd_lib_lake_fs_time_cest = (
            config.get_global_lake_instance()
            .get_element_info(lake_fs_usd_lib_path)
            .get("Modified Time")
        )
        if not usd_lib_lake_fs_time_cest:
            raise ValueError("could not find UsdLib time stamp on LakeFs server")

        with open(config.ADDON_DATA_JSON_PATH, "r+") as data_json:
            addon_data_json = json.load(data_json)
            addon_data_json["usd_lib_lake_fs_time_cest"] = usd_lib_lake_fs_time_cest

            data_json.seek(0)
            json.dump(
                addon_data_json,
                data_json,
            )
            data_json.truncate()

        controller = worker.Controller()

        usd_download_work_item = controller.construct_work_item(
            func=config.get_global_lake_instance().clone_element,
            kwargs={
                "lake_fs_object_uir": lake_fs_usd_lib_path,
                "dist_path": config.DOWNLOAD_DIR,
            },
            progress_title="Download UsdLib",
        )

        controller.construct_work_item(
            func=zip.extract_zip_file,
            kwargs={
                "zip_file_path": config.USD_ZIP_PATH,
                "dest_dir": config.USD_LIB_PATH,
            },
            progress_title="Unzip UsdLib",
            dependency_id=[usd_download_work_item.get_uuid()],
        )

        download_ui = progress_ui.ProgressDialog(
            controller,
            close_on_finish=True,
            auto_close_timeout=1,
            delet_progress_bar_on_finish=False,
            title=f"{config.ADDON_NAME}-Addon [UsdLib Download]",
        )
        download_ui.setStyleSheet(style.load_stylesheet())
        download_ui.start()
        self._download_window = download_ui

    def tray_exit(self):
        """Exit tray module."""
        pass

    def tray_menu(self, tray_menu):
        """Add menu items to tray menu."""
        pass

    def get_launch_hook_paths(self):
        """Get paths to launch hooks."""
        return [os.path.join(config.USD_ADDON_DIR, "hooks")]
