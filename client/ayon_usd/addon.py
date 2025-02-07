"""USD Addon for AYON."""

import json
import os
from datetime import datetime, timezone

from ayon_core import style
from ayon_core.addon import AYONAddon, IPluginPaths, ITrayAddon

from ayon_core.settings import get_studio_settings

from . import config, utils
from .utils import ADDON_DATA_JSON_PATH, DOWNLOAD_DIR
from .version import __version__

from .ayon_bin_client.ayon_bin_distro.work_handler import worker
from .ayon_bin_client.ayon_bin_distro.util import zip

USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


class USDAddon(AYONAddon, ITrayAddon, IPluginPaths):
    """Addon to add USD Support to AYON.

    Addon can also skip distribution of binaries from server and can
    use path/arguments defined by server.

    Cares about supplying USD Framework.
    """

    name = "usd"
    version = __version__
    _download_window = None

    def tray_init(self):
        """Initialize tray module."""
        super(USDAddon, self).tray_init()

    def initialize(self, studio_settings):
        """Initialize USD Addon."""
        self._download_window = None

    def tray_start(self):
        """Start tray module.

        Download USD if needed.
        """
        self._download_global_lakefs_binaries()

    def tray_exit(self):
        """Exit tray module."""
        pass

    def tray_menu(self, tray_menu):
        """Add menu items to tray menu."""
        pass

    def get_launch_hook_paths(self):
        """Get paths to launch hooks."""
        return [os.path.join(USD_ADDON_DIR, "hooks")]

    def get_plugin_paths(self):
        return {
            "publish": [
                os.path.join(USD_ADDON_DIR, "plugins", "publish")
            ]
        }

    def _download_global_lakefs_binaries(self):
        settings = get_studio_settings()
        if not settings["usd"]["distribution"]["enabled"]:
            self.log.info("USD Binary distribution is disabled.")
            return

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        if not os.path.exists(ADDON_DATA_JSON_PATH):
            now = datetime.now().astimezone(timezone.utc)
            with open(ADDON_DATA_JSON_PATH, "w+") as json_file:
                init_data = {
                    "ayon_usd_addon_first_init_utc": str(now)
                }
                json.dump(init_data, json_file)

        if not utils.is_usd_lib_download_needed(settings):
            self.log.info("USD Libs already available. Skipping download.")
            return

        lake_fs_usd_lib_path = config.get_lakefs_usdlib_path(settings)

        # Get modified time on LakeFS
        lake_fs = config.get_global_lake_instance(settings)
        usd_lib_lake_fs_time_cest = (
            lake_fs
            .get_element_info(lake_fs_usd_lib_path)
            .get("Modified Time")
        )
        if not usd_lib_lake_fs_time_cest:
            raise ValueError(
                "Unable to find UsdLib date modified timestamp on "
                f"LakeFs server: {lake_fs_usd_lib_path}"
            )

        with open(ADDON_DATA_JSON_PATH, "r+") as json_file:
            addon_data_json = json.load(json_file)
            addon_data_json["usd_lib_lake_fs_time_cest"] = usd_lib_lake_fs_time_cest

            json_file.seek(0)
            json.dump(
                addon_data_json,
                json_file,
            )
            json_file.truncate()

        controller = worker.Controller()

        usd_download_work_item = controller.construct_work_item(
            func=lake_fs.clone_element,
            kwargs={
                "lake_fs_object_uir": lake_fs_usd_lib_path,
                "dist_path": DOWNLOAD_DIR,
            },
            progress_title="Download UsdLib",
        )

        usd_zip_path = os.path.join(
            DOWNLOAD_DIR,
            os.path.basename(config.get_lakefs_usdlib_path(settings))
        )
        usd_lib_path = os.path.splitext(usd_zip_path)[0]
        controller.construct_work_item(
            func=zip.extract_zip_file,
            kwargs={
                "zip_file_path": usd_zip_path,
                "dest_dir": usd_lib_path,
            },
            progress_title="Unzip UsdLib",
            dependency_id=[usd_download_work_item.get_uuid()],
        )

        from .ayon_bin_client.ayon_bin_distro.gui import progress_ui
        download_ui = progress_ui.ProgressDialog(
            controller,
            close_on_finish=True,
            auto_close_timeout=1,
            delete_progress_bar_on_finish=False,
            title="ayon_usd-Addon [UsdLib Download]",
        )
        download_ui.setStyleSheet(style.load_stylesheet())
        download_ui.start()
        self._download_window = download_ui