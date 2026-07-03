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
    distribution = settings["usd"]["distribution"]

    _LocalCache.lake_instance = wrapper.LakeCtl(
        server_url=distribution["server_uri"],
        access_key_id=distribution["access_key_id"],
        secret_access_key=distribution["secret_access_key"],
    )
    return _LocalCache.lake_instance


def _normalize_lakefs_repo_root(lake_fs_repo: str) -> str:
    """Return a repo URI normalized for repo-root operations."""
    lake_fs_repo = lake_fs_repo.strip()
    if not lake_fs_repo.endswith("/"):
        lake_fs_repo = f"{lake_fs_repo}/"
    return lake_fs_repo


def _normalize_lakefs_repo_base(lake_fs_repo: str) -> str:
    """Return a repo URI normalized for object-path construction."""
    return lake_fs_repo.strip().rstrip("/")


def _get_lakefs_repo_items(lakefs_repo: str) -> list:
    """Return all repo object names in the LakeFS repository"""
    if not lakefs_repo:
        return []

    lakefs_repo = _normalize_lakefs_repo_root(lakefs_repo)
    return get_global_lake_instance().list_repo_objects(lakefs_repo)


def get_lakefs_usdlib_name(lakefs_repo: str, settings=None) -> str:
    """Return AyonUsdBin/usd LakeFS repo object name for current platform."""
    lakefs_repo = _normalize_lakefs_repo_base(lakefs_repo)

    global CACHED_ITEMS
    if CACHED_ITEMS:
        lakefs_repo_items = CACHED_ITEMS
    else:
        lakefs_repo_items = _get_lakefs_repo_items(lakefs_repo, settings)
        CACHED_ITEMS = lakefs_repo_items

    platform_name = platform.system().lower()
    for item in lakefs_repo_items:
        if "AyonUsdBin/usd" in item and platform_name in item:
            return item

    raise RuntimeError(
        "No AyonUsdBin/usd item found for current platform "
        f"'{platform_name}' on LakeFS server: {lakefs_repo}. "
        f"All LakeFS repository items found: {lakefs_repo_items}")


def get_lakefs_usdlib_path(lakefs_repo: str) -> str:
    """Return AyonUsdBin/usd LakeFS full url for current platform. """
    usd_lib_conf = get_lakefs_usdlib_name(lakefs_repo)
    return f"{lakefs_repo}/{usd_lib_conf}"
