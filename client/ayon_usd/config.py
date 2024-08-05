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
AYON_BUNDLE_NAME = os.environ["AYON_BUNDLE_NAME"]
USD_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))

ADDON_DATA_JSON_PATH = os.path.join(DOWNLOAD_DIR, "ayon_usd_addon_info.json")


# Addon Settings
# LakeFs
ADDON_SETTINGS_LAKE_FS_URI = ("LakeFs_Settings", "ayon_usd_lake_fs_server_uri")
ADDON_SETTINGS_LAKE_FS_REPO_URI = ("LakeFs_Settings", "ayon_usd_lake_fs_server_repo")
ADDON_SETTINGS_LAKE_FS_KEY_ID = ("LakeFs_Settings", "access_key_id")
ADDON_SETTINGS_LAKE_FS_KEY = ("LakeFs_Settings", "secret_access_key")
# Resolver def
ADDON_SETTINGS_ASSET_RESOLVERS = ("LakeFs_Settings", "asset_resolvers")
ADDON_SETTINGS_ASSET_RESOLVERS_OVERWRITES = ("LakeFs_Settings", "lake_fs_overrides")
# Usd settings
ADDON_SETTINGS_USD_TF_DEBUG = ("Usd_Settings", "usd_tf_debug")
# Resolver Settings
ADDON_SETTINGS_USD_RESOLVER_LOG_LVL = ("Ayon_UsdResolver_Settings", "ayon_log_lvl")

ADDON_SETTINGS_USD_RESOLVER_LOG_FILLE_LOOGER_ENABLED = (
    "Ayon_UsdResolver_Settings",
    "ayon_file_logger_enabled",
)

ADDON_SETTINGS_USD_RESOLVER_LOG_FILLE_LOOGER_FILE_PATH = (
    "Ayon_UsdResolver_Settings",
    "file_logger_file_path",
)

ADDON_SETTINGS_USD_RESOLVER_LOG_LOGGIN_KEYS = (
    "Ayon_UsdResolver_Settings",
    "ayon_logger_logging_keys",
)


def get_addon_settings_value(settings: dict, key_path: tuple):
    try:
        selected_element = settings
        for key in key_path:
            selected_element = selected_element[key]

        return selected_element
    except (KeyError, TypeError) as e:
        raise KeyError(f"Error accessing settings with key path {key_path}: {e}")


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


def get_addon_settings():

    return ayon_api.get_addon_settings(
        addon_name=ADDON_NAME,
        addon_version=ADDON_VERSION,
        variant=AYON_BUNDLE_NAME,
    )


@SingletonFuncCache.cache
def get_global_lake_instance():
    addon_settings = (
        get_addon_settings()
    )  # the function is cached, but this reduces the call stack
    return wrapper.LakeCtl(
        server_url=str(
            get_addon_settings_value(addon_settings, ADDON_SETTINGS_LAKE_FS_URI)
        ),
        access_key_id=str(
            get_addon_settings_value(addon_settings, ADDON_SETTINGS_LAKE_FS_KEY_ID)
        ),
        secret_access_key=str(
            get_addon_settings_value(addon_settings, ADDON_SETTINGS_LAKE_FS_KEY)
        ),
    )


@SingletonFuncCache.cache
def _get_lake_fs_repo_items() -> list:
    lake_repo_uri = str(
        get_addon_settings_value(get_addon_settings(), ADDON_SETTINGS_LAKE_FS_REPO_URI)
    )
    if not lake_repo_uri:
        return []
    return get_global_lake_instance().list_repo_objects(lake_repo_uri)


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
            f"{get_addon_settings_value(get_addon_settings(), ADDON_SETTINGS_LAKE_FS_REPO_URI)}{get_usd_lib_conf_from_lakefs()}"
        ),
    )
)

USD_LIB_PATH = Path(str(USD_ZIP_PATH).replace(USD_ZIP_PATH.suffix, ""))
