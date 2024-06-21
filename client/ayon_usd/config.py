"""USD Addon utility functions."""

import functools
import os
import platform
from pathlib import Path
from ayon_usd import version
from ayon_usd.ayon_bin_client.ayon_bin_distro.lakectlpy import wrapper
import ayon_api

CURRENT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR: Path = CURRENT_DIR / "downloads"
NOT_SET = type("NOT_SET", (), {"__bool__": lambda: False})()
ADDON_NAME: str = version.name
ADDON_VERSION: str = version.__version__

USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


class SingletonFuncCache:
    _instance = None
    _cache = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def cache(cls, func):
        @functools.wraps(func)
        def cache_func(*args, **kwargs):
            cache_key = (func.__name__, args, tuple(kwargs.items()))
            if cache_key in cls._cache:
                return cls._cache[cache_key]
            result = func(*args, **kwargs)
            cls._cache[cache_key] = result
            return result

        return cache_func

    def debug(self):
        return self._cache


def print_cache():
    print(SingletonFuncCache().debug())


@SingletonFuncCache.cache
def get_addon_settings():
    return ayon_api.get_addon_settings(ADDON_NAME, ADDON_VERSION)


# TODO should this be replaced with get_addon_settings ?
global_addon_settings = get_addon_settings()


@SingletonFuncCache.cache
def get_global_lake_instance():
    return wrapper.LakeCtl(
        server_url=global_addon_settings["ayon_usd_lake_fs_server_uri"],
        access_key_id=global_addon_settings["access_key_id"],
        secret_access_key=global_addon_settings["secret_access_key"],
    )


@SingletonFuncCache.cache
def _get_lake_fs_repo_items() -> list:
    return get_global_lake_instance().list_repo_objects(
        global_addon_settings["ayon_usd_lake_fs_server_repo"]
    )


@SingletonFuncCache.cache
def get_usd_lib_conf_from_lakefs() -> str:
    usd_zip_lake_path = ""
    for item in _get_lake_fs_repo_items():
        if "AyonUsdBin/usd" in item and platform.system().lower() in item:
            usd_zip_lake_path = item
    return usd_zip_lake_path


USD_ZIP_PATH = Path(
    os.path.join(
        DOWNLOAD_DIR,
        os.path.basename(
            f"{global_addon_settings['ayon_usd_lake_fs_server_repo']}{get_usd_lib_conf_from_lakefs()}"
        ),
    )
)

USD_LIB_PATH = Path(str(USD_ZIP_PATH).replace(USD_ZIP_PATH.suffix, ""))
