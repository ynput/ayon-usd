"""USD Addon utility functions."""
from __future__ import annotations

import json
import os
import platform
import pathlib
import sys
from datetime import datetime, timezone

from ayon_core.lib.path_templates import StringTemplate

from ayon_usd.ayon_bin_client.ayon_bin_distro.work_handler import worker
from ayon_usd.ayon_bin_client.ayon_bin_distro.util import zip
from ayon_usd import config

USD_ADDON_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(USD_ADDON_ROOT_DIR, "downloads")
ADDON_DATA_JSON_PATH = os.path.join(DOWNLOAD_DIR, "ayon_usd_addon_info.json")
ADDON_FIRST_INIT_KEY = "ayon_usd_addon_first_init_utc"


def get_addon_data_json() -> dict:
    """Get addon data JSON content as dict."""
    if os.path.exists(ADDON_DATA_JSON_PATH):
        try:
            with open(ADDON_DATA_JSON_PATH, "r") as json_file:
                data = json.load(json_file)
        except (json.JSONDecodeError, OSError, ValueError):
            return {}
        if isinstance(data, dict):
            return data
    return {}


def create_addon_data_json_file():
    """Ensure addon data JSON file exists and contains init metadata."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    addon_data = get_addon_data_json()
    if ADDON_FIRST_INIT_KEY in addon_data:
        return

    addon_data[ADDON_FIRST_INIT_KEY] = str(datetime.now().astimezone(
        timezone.utc
    ))

    with open(ADDON_DATA_JSON_PATH, "w") as json_file:
        json.dump(addon_data, json_file)


def get_download_dir(create_if_missing=True):
    """Dir path where files are downloaded.

    Args:
        create_if_missing (bool): Create dir if missing.

    Returns:
        str: Path to download dir.

    """
    if create_if_missing and not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR


def get_downloaded_usd_root(lake_fs_repo_uri) -> str:
    """Get downloaded USDLib os local root path."""
    target_usd_lib = config.get_lakefs_usdlib_name(lake_fs_repo_uri)
    filename_no_ext = os.path.splitext(os.path.basename(target_usd_lib))[0]
    return os.path.join(DOWNLOAD_DIR, filename_no_ext)


def lakefs_download_and_extract(resolver_lake_fs_path: str,
                                download_dir: str) -> str:
    """Download individual object based on the lake_fs_path and extracts
    the zip into the specific download_dir.

    Args
        resolver_lake_fs_path (str): Lake FS Path for the resolver
        download_dir (str): Directory to download and unzip to.

    Returns:
        str: Result from the ZIP file extraction.

    """
    controller = worker.Controller()
    download_item = controller.construct_work_item(
        func=config.get_global_lake_instance().clone_element,
        args=[resolver_lake_fs_path, download_dir],
    )

    extract_zip_item = controller.construct_work_item(
        func=zip.extract_zip_file,
        args=[
            download_item.connect_func_return,
            download_dir,
        ],
        dependency_id=[download_item.get_uuid()],
    )

    controller.start()

    return str(extract_zip_item.func_return)


def get_local_resolver_path(settings, app_name: str):
    """Check local_resolver_paths for a matching app + platform entry.

    Args:
        settings (dict): Project settings.
        app_name (str): Application name, e.g. "houdini/20-5".

    Returns:
        str | None: Local filesystem path to the resolver directory,
            or None if no match found.

    """
    roots = settings["usd"]["distribution"]["local"]["roots"]
    local_paths = (
        settings["usd"]["distribution"]["local"]["asset_resolvers"]
    )
    current_platform = platform.system().lower()
    for entry in local_paths:
        if entry["platform"] != current_platform:
            continue
        if entry["name"] == app_name or app_name in entry.get(
            "app_alias_list", []
        ):
            template = StringTemplate(entry["path"])
            result = template.format(
                {root["name"]: root.get(current_platform) for root in roots}
            )
            return str(result)
    
    return None


def get_resolver_to_download(settings, app_name: str) -> str:
    """
    Gets LakeFs path that can be used with copy element to download
    specific resolver, this will prioritize `lake_fs_overrides` over
    asset_resolvers entries.

    Returns: str: LakeFs object path to be used with lake_fs_py wrapper

    """
    distribution = settings["usd"]["distribution"]["lake_fs"]
    resolver_overwrite_list = distribution["lake_fs_overrides"]
    if resolver_overwrite_list:
        resolver_overwrite = next(
            (
                item
                for item in resolver_overwrite_list
                if item["app_name"] == app_name
                and item["platform"] == sys.platform.lower()
            ),
            None,
        )
        if resolver_overwrite:
            return resolver_overwrite["uri"]

    resolver_list = distribution["asset_resolvers"]
    if not resolver_list:
        return ""

    resolver = next(
        (
            item
            for item in resolver_list
            if (item["name"] == app_name or app_name in item["app_alias_list"])
            and item["platform"] == platform.system().lower()
        ),
        None,
    )
    if not resolver:
        return ""

    lake_fs_repo_uri = distribution["server_repo"]
    lake_fs_repo_uri = lake_fs_repo_uri.strip().rstrip("/")
    resolver_lake_path = f"{lake_fs_repo_uri}/{resolver['lake_fs_path']}"
    return resolver_lake_path


def get_resolver_setup_info(
        resolver_dir,
        settings,
        env=None) -> dict:
    """Get the environment variables to load AYON USD setup.

    Arguments:
        resolver_dir (str): Directory of the resolver.
        settings (dict[str, Any]): Studio settings.
        env (dict[str, str]): Source environment to build on.

    Returns:
        dict[str, str]: The environment needed to load AYON USD correctly.
    """

    resolver_root = pathlib.Path(resolver_dir) / "ayonUsdResolver"
    resolver_plugin_info_path = resolver_root / "resources" / "plugInfo.json"
    resolver_ld_path = resolver_root / "lib"
    resolver_python_path = resolver_root / "lib" / "python"

    if (
        not os.path.exists(resolver_python_path)
        or not os.path.exists(resolver_ld_path)
    ):
        raise RuntimeError(
            f"Cant start Resolver missing path "
            f"resolver_python_path: {resolver_python_path}, "
            f"resolver_ld_path: {resolver_ld_path}"
        )

    def _append(_env: dict, key: str, path: str):
        """Add path to key in env"""
        current: str = _env.get(key)
        if current:
            return os.pathsep.join([current, path])
        return path

    ld_path_key = "LD_LIBRARY_PATH"
    if platform.system().lower() == "windows":
        ld_path_key = "PATH"

    pxr_pluginpath_name = _append(
        env, "PXR_PLUGINPATH_NAME", resolver_plugin_info_path.as_posix()
    )
    ld_library_path = _append(
        env, ld_path_key, resolver_ld_path.as_posix()
    )
    python_path = _append(
        env, "PYTHONPATH", resolver_python_path.as_posix()
    )

    resolver_settings = settings["usd"]["ayon_usd_resolver"]
    return {
        "TF_DEBUG": settings["usd"]["usd"]["usd_tf_debug"],
        "AYON_USD_RESOLVER_LOG_LVL": resolver_settings["ayon_log_lvl"],
        "AYON_USD_RESOLVER_LOG_FILE_ENABLED": resolver_settings["ayon_file_logger_enabled"],  # noqa
        "AYON_USD_RESOLVER_LOG_FILE": resolver_settings["file_logger_file_path"],
        "AYON_USD_RESOLVER_LOGGING_KEYS": resolver_settings["ayon_logger_logging_keys"],  # noqa
        "PXR_PLUGINPATH_NAME": pxr_pluginpath_name,
        "PYTHONPATH": python_path,
        ld_path_key: ld_library_path,
        # Backwards compatibility (deprecated)
        "AYONLOGGERLOGLVL": resolver_settings["ayon_log_lvl"],
        "AYONLOGGERFILELOGGING": resolver_settings["ayon_file_logger_enabled"],
        "AYONLOGGERFILEPOS": resolver_settings["file_logger_file_path"],
        "AYON_LOGGIN_LOGGIN_KEYS": resolver_settings["ayon_logger_logging_keys"],
    }
