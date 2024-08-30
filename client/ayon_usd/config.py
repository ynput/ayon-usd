"""USD Addon utility functions."""

import os
import platform

from pathlib import Path

from ayon_usd.ayon_bin_client.ayon_bin_distro.lakectlpy import wrapper
from ayon_core.settings import get_studio_settings


CURRENT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR: Path = CURRENT_DIR / "downloads"
USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
ADDON_DATA_JSON_PATH = os.path.join(DOWNLOAD_DIR, "ayon_usd_addon_info.json")


class _LocalCache:
    lake_instance = None


def get_global_lake_instance(settings=None):
    """Create lakefs connection.

    Warning:
        This returns singleton object which uses connection information
            available on first call.

    Args:
        settings (Optional[Dict[str, Any]]): Prepared studio or
            project settings.

    Returns:
        wrapper.LakeCtl: Connection object.

    """
    if _LocalCache.lake_instance is not None:
        return _LocalCache.lake_instance

    if not settings:
        settings = get_studio_settings()
    lakefs = settings["ayon_usd"]["lakefs"]
    return wrapper.LakeCtl(
        server_url=lakefs["server_uri"],
        access_key_id=lakefs["access_key_id"],
        secret_access_key=lakefs["secret_access_key"],
    )


def _get_lake_fs_repo_items(lake_fs_repo_uri: str) -> list:
    if not lake_fs_repo_uri:
        return []
    return get_global_lake_instance().list_repo_objects(lake_fs_repo_uri)


def get_usd_lib_conf_from_lakefs(lake_fs_repo_uri: str) -> str:
    usd_zip_lake_path = ""
    for item in _get_lake_fs_repo_items(lake_fs_repo_uri):
        if "AyonUsdBin/usd" in item and platform.system().lower() in item:
            usd_zip_lake_path = item
    return usd_zip_lake_path


def get_lakefs_usdlib_path(settings: dict) -> str:
    lake_fs_repo_uri = settings["ayon_usd"]["lakefs"]["server_uri"]
    usd_lib_conf = get_usd_lib_conf_from_lakefs(lake_fs_repo_uri)
    return f"{lake_fs_repo_uri}{usd_lib_conf}"
