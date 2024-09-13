"""USD Addon for AYON - client part."""

import importlib # noqa: F401

# Define custom exception
class QtBindingsNotFoundError(Exception):
    pass

from ayon_core.lib import is_headless_mode_enabled # noqa: F401 

IS_GUI_MODE = False
if not is_headless_mode_enabled():
    try:
        import qtpy  # noqa: F401
        IS_GUI_MODE = True
    except ImportError:
        pass
    except QtBindingsNotFoundError:
        print("testing")
        pass
    except Exception as e: 
        raise RuntimeError(f"An error occurred while checking for Qt: {e}")

from .addon import USDAddon  # noqa: F401
from .utils import (  # noqa: F401
    get_download_dir
)
from .ayon_bin_client.ayon_bin_distro.util.zip import extract_zip_file  # noqa: F401

__all__ = (
    "USDAddon",
    "extract_zip_file",
    "get_download_dir",
)
