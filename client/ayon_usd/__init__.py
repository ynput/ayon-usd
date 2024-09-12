"""USD Addon for AYON - client part."""
# flake8: noqa F401

# TODO ayon_api has a check for headless mode. we need to see if that system covers all fronts 
HEADLESS_MODE = True 
try:
    import qtpy # noqa: F401
    HEADLESS_MODE = False
except ImportError:
    print("qt.py or a Qt binding is not installed.")
except Exception as e: 
    raise RuntimeError(f"An error occurred while checking for Qt: {e}")

from .addon import USDAddon
from .utils import (
    get_download_dir
)
from .ayon_bin_client.ayon_bin_distro.util.zip import extract_zip_file

__all__ = (
    "USDAddon",
    "extract_zip_file",
    "get_download_dir",
)
