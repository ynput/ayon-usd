"""USD Addon for AYON."""

import json
import os

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

        Skip downloading base USD, not needed now.
        """
        pass

    def tray_exit(self):
        """Exit tray module."""
        pass

    def tray_menu(self, tray_menu):
        """Add menu items to tray menu."""
        pass

    def get_launch_hook_paths(self):
        """Get paths to launch hooks."""
        return [os.path.join(USD_ADDON_DIR, "hooks")]

    def get_publish_plugin_paths(self, host_name):
        return [
            os.path.join(USD_ADDON_DIR, "plugins", "publish")
        ]
