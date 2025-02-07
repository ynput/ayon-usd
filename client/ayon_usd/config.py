import platform

from ayon_usd.ayon_bin_client.ayon_bin_distro.lakectlpy import wrapper
from ayon_core.settings import get_studio_settings


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
    distribution = settings["usd"]["distribution"]
    return wrapper.LakeCtl(
        server_url=distribution["server_uri"],
        access_key_id=distribution["access_key_id"],
        secret_access_key=distribution["secret_access_key"],
    )


def _get_lakefs_repo_items(lake_fs_repo: str) -> list:
    """Return all repo object names in the LakeFS repository"""
    if not lake_fs_repo:
        return []
    return get_global_lake_instance().list_repo_objects(lake_fs_repo)


def get_lakefs_usdlib_name(lake_fs_repo: str) -> str:
    """Return AyonUsdBin/usd LakeFS repo object name for current platform."""
    platform_name = platform.system().lower()
    lake_fs_repo_items = _get_lakefs_repo_items(lake_fs_repo)
    for item in lake_fs_repo_items:
        if "AyonUsdBin/usd" in item and platform_name in item:
            return item

    raise RuntimeError(
        "No AyonUsdBin/usd item found for current platform "
        f"'{platform_name}' on LakeFS server: {lake_fs_repo}. "
        f"All LakeFS repository items found: {lake_fs_repo_items}")


def get_lakefs_usdlib_path(settings: dict) -> str:
    """Return AyonUsdBin/usd LakeFS full url for current platform. """
    lake_fs_repo = settings["usd"]["distribution"]["server_repo"]
    usd_lib_conf = get_lakefs_usdlib_name(lake_fs_repo)
    return f"{lake_fs_repo}{usd_lib_conf}"
