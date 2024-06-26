"""USD Addon for AYON."""

import os
import shutil

from . import config, utils
from ayon_core.modules import AYONAddon, ITrayModule
from ayon_core import style
from .ayon_bin_client.ayon_bin_distro.gui import progress_ui
from .ayon_bin_client.ayon_bin_distro.work_handler import worker
from .ayon_bin_client.ayon_bin_distro.util import zip


class USDAddon(AYONAddon, ITrayModule):
    """Addon to add USD Support to AYON.

    Addon can also skip distribution of binaries from server and can
    use path/arguments defined by server.

    Cares about supplying USD Framework.
    """

    name = "ayon_usd"
    _download_window = None

    def tray_init(self):
        """Initialize tray module."""
        super(USDAddon, self).tray_init()

    def initialize(self, module_settings):
        """Initialize USD Addon."""
        self.enabled = True
        self._download_window = None

    def tray_start(self):
        """Start tray module.

        Download USD if needed.
        """
        super(USDAddon, self).tray_start()

        if not utils.is_usd_download_needed():
            print(f"usd is allready downloaded")
            return

        # TODO remove this ( this exists because for some reason there is a downloades.zip where the downloades folder should be and i dont know why it is there it dose not create a re download off the usd lib)
        if not os.path.exists(config.DOWNLOAD_DIR):
            os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        if os.path.exists(str(config.DOWNLOAD_DIR) + ".zip"):
            os.remove(str(config.DOWNLOAD_DIR) + ".zip")

        settings = config.get_addon_settings()
        controller = worker.Controller()
        usd_download_work_item = controller.construct_work_item(
            func=config.get_global_lake_instance().clone_element,
            kwargs={
                "lake_fs_object_uir": f"{settings['ayon_usd_lake_fs_server_repo']}{config.get_usd_lib_conf_from_lakefs()}",
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
