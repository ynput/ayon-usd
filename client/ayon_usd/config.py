import platform

from ayon_usd.ayon_bin_client.ayon_bin_distro.lakectlpy import wrapper
from ayon_core.settings import get_studio_settings


class _LocalCache:
    lake_instance = None

CACHED_ITEMS = []


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
    distribution = settings["usd"]["distribution"]["lake_fs"]
    return wrapper.LakeCtl(
        server_url=distribution["server_uri"],
        access_key_id=distribution["access_key_id"],
        secret_access_key=distribution["secret_access_key"],
    )


def _get_lakefs_repo_items(lakefs_repo: str) -> list:
    """Return all repo object names in the LakeFS repository"""
    if not lakefs_repo:
        return []

    if not lakefs_repo.endswith("/"):
        lakefs_repo += "/"
    return get_global_lake_instance().list_repo_objects(lakefs_repo)


def get_lakefs_usdlib_name(lakefs_repo: str) -> str:
    """Return AyonUsdBin/usd LakeFS repo object name for current platform."""
    global CACHED_ITEMS
    platform_name = platform.system().lower()
    if CACHED_ITEMS:
        lake_fs_repo_items = CACHED_ITEMS
    else:
        lake_fs_repo_items = _get_lakefs_repo_items(lakefs_repo)
        CACHED_ITEMS = lake_fs_repo_items
    for item in lake_fs_repo_items:
        if "AyonUsdBin/usd" in item and platform_name in item:
            return item

    raise RuntimeError(
        "No AyonUsdBin/usd item found for current platform "
        f"'{platform_name}' on LakeFS server: {lakefs_repo}. "
        f"All LakeFS repository items found: {lake_fs_repo_items}")


def get_lakefs_usdlib_path(lakefs_repo: str) -> str:
    """Return AyonUsdBin/usd LakeFS full url for current platform. """
    usd_lib_conf = get_lakefs_usdlib_name(lakefs_repo)
    return f"{lakefs_repo}/{usd_lib_conf}"
