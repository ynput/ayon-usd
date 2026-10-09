"""USD Addon for AYON."""

from __future__ import annotations

import os
from typing import Any

from ayon_core.addon import AYONAddon, IPluginPaths, ITrayAddon

from .version import __version__

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

    def tray_init(self) -> None:
        """Initialize tray module."""
        super().tray_init()

    def initialize(self, studio_settings: dict[str, Any]) -> None:
        """Initialize USD Addon."""
        self._download_window = None

    def tray_start(self) -> None:
        """Start tray module.

        Skip downloading base USD, not needed now.
        """

    def tray_exit(self) -> None:
        """Exit tray module."""

    def tray_menu(self, tray_menu: Any) -> None:  # ruff:ignore[any-type]
        """Add menu items to tray menu."""

    def get_launch_hook_paths(self) -> list[str]:  # ruff:ignore[no-self-use]
        """Get paths to launch hooks.

        Returns:
            list[str]: Paths to launch hook directories.

        """
        return [os.path.join(USD_ADDON_DIR, "hooks")]

    def get_publish_plugin_paths(  # ruff:ignore[no-self-use]
        self, host_name: str
    ) -> list[str]:
        """Get paths to publish plugins.

        Args:
            host_name (str): Name of the host requesting the paths.

        Returns:
            list[str]: Paths to publish plugin directories.

        """
        return [
            os.path.join(USD_ADDON_DIR, "plugins", "publish")
        ]
