"""USD Addon utility functions."""

import functools
import os
import platform
import json
import hashlib
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

            cache_key = tuple((func.__name__, cls._hash_args_kwargs(args, kwargs)))

            if cache_key in cls._cache.keys():
                return cls._cache[cache_key]
            result = func(*args, **kwargs)
            cls._cache[cache_key] = result

            return result

        return cache_func

    @staticmethod
    def _hash_args_kwargs(args, kwargs):
        """Generate a hashable key from *args and **kwargs."""
        args_hash = SingletonFuncCache._make_hashable(args)
        kwargs_hash = SingletonFuncCache._make_hashable(kwargs)
        return args_hash + kwargs_hash

    @staticmethod
    def _make_hashable(obj):
        """Converts an object to a hashable representation."""

        if isinstance(obj, (int, float, str, bool, type(None))):
            return hashlib.sha256(str(obj).encode()).hexdigest()

        if isinstance(obj, dict) or hasattr(obj, "__dict__"):
            return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

        try:
            return hashlib.sha256(json.dumps(obj).encode()).hexdigest()
        except TypeError:
            return hashlib.sha256(str(id(obj)).encode()).hexdigest()

    def debug(self):
        return self._cache


def print_cache():
    print(SingletonFuncCache().debug())


@SingletonFuncCache.cache
def get_addon_settings():
    return ayon_api.get_addon_settings(ADDON_NAME, ADDON_VERSION)


@SingletonFuncCache.cache
def get_global_lake_instance():
    addon_settings = (
        get_addon_settings()
    )  # the function is cached, but this reduces the call stack
    return wrapper.LakeCtl(
        server_url=addon_settings["ayon_usd_lake_fs_server_uri"],
        access_key_id=addon_settings["access_key_id"],
        secret_access_key=addon_settings["secret_access_key"],
    )


@SingletonFuncCache.cache
def _get_lake_fs_repo_items() -> list:
    return get_global_lake_instance().list_repo_objects(
        get_addon_settings()["ayon_usd_lake_fs_server_repo"]
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
            f"{get_addon_settings()['ayon_usd_lake_fs_server_repo']}{get_usd_lib_conf_from_lakefs()}"
        ),
    )
)

USD_LIB_PATH = Path(str(USD_ZIP_PATH).replace(USD_ZIP_PATH.suffix, ""))
