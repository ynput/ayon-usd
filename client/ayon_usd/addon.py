import os

from openpype.modules import AYONAddon, ITrayModule

from .utils import is_usd_download_needed
from .version import __version__


USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


class USDAddon(AYONAddon, ITrayModule):
    """Addon to add USD Support to AYON.

    Addon can also skip distribution of binaries from server and can
    use path/arguments defined by server.

    Cares about supplying USD Framework.
    """

    name = "usd"
    version = __version__

    def initialize(self, module_settings):
        self.enabled = True
        self._download_window = None

    def tray_exit(self):
        pass

    def tray_menu(self, tray_menu):
        pass

    def tray_init(self):
        pass

    def tray_start(self):
        download_usd = is_usd_download_needed()
        if not download_usd:
            return

        from .download_ui import show_download_window

        download_window = show_download_window(
            download_usd
        )
        download_window.finished.connect(self._on_download_finish)
        download_window.start()
        self._download_window = download_window

    def _on_download_finish(self):
        self._download_window.close()
        self._download_window = None
