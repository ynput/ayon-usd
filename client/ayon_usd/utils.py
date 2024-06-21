"""USD Addon utility functions."""

import os
import platform
import pathlib
import sys

import ayon_api
from ayon_usd.ayon_bin_client.ayon_bin_distro.work_handler import worker
from ayon_usd.ayon_bin_client.ayon_bin_distro.util import zip
from ayon_usd import config


@config.SingletonFuncCache.cache
def get_addon_settings() -> dict:
    """Get addon settings.

    Return:
        dict: Addon settings.

    """
    return ayon_api.get_addon_settings(config.ADDON_NAME, config.ADDON_VERSION)


def get_download_dir(create_if_missing=True):
    """Dir path where files are downloaded.

    Args:
        create_if_missing (bool): Create dir if missing.

    Returns:
        str: Path to download dir.

    """
    if create_if_missing and not os.path.exists(config.DOWNLOAD_DIR):
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    return config.DOWNLOAD_DIR


@config.SingletonFuncCache.cache
def get_downloaded_usd_root() -> str:
    """Get downloaded USDLib os local root path."""
    target_usd_lib = config.get_usd_lib_conf_from_lakefs()
    usd_lib_local_path = os.path.join(
        config.DOWNLOAD_DIR,
        os.path.basename(target_usd_lib).replace(
            f".{target_usd_lib.split('.')[-1]}", ""
        ),
    )
    return usd_lib_local_path


@config.SingletonFuncCache.cache
def is_usd_download_needed() -> bool:
    """
    checks if the correct UsdLib is allready present in downloads.
    Args:
        addon_settings ():

    Returns:

    """
    if os.path.exists(os.path.abspath(get_downloaded_usd_root())):
        return False

    return True


# TODO optionally allow to start a ui for the work items
def download_and_extract_resolver(resolver_lake_fs_path: str, download_dir: str) -> str:
    """downloads an individual object based on the lake_fs_path and extracts the zip into the specific download_dir

    Args:
        resolver_lake_fs_path ():
        download_dir ():

    Returns:

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


@config.SingletonFuncCache.cache
def get_resolver_to_download(settings, app_name: str) -> str:
    """
    gets lakeFs path that can be used with copy element to download specific resolver, this will priorities lake_fs_overwrites over asset_resolvers entry's

    Returns: str: lakeFs object path to be used with lake_fs_py wrapper

    """

    resolver_overwrite = next(
        (
            item
            for item in settings["lake_fs_overwrites"]
            if item["app_name"] == app_name and item["platform"] == sys.platform.lower()
        ),
        None,
    )
    if resolver_overwrite:
        return resolver_overwrite["lake_fs_path"]

    resolver = next(
        (
            item
            for item in settings["asset_resolvers"]
            if item["app_name"] == app_name and item["platform"] == sys.platform.lower()
        ),
        None,
    )

    if not resolver:
        return ""

    lake_base_path = settings["ayon_usd_lake_fs_server_repo"]
    resolver_lake_path = lake_base_path + resolver["lake_fs_path"]
    return resolver_lake_path


@config.SingletonFuncCache.cache
def get_resolver_setup_info(resolver_dir, settings, app_name: str, logger=None) -> dict:
    pxr_plugin_paths = []
    ld_path = []
    python_path = []

    if val := os.getenv("PXR_PLUGINPATH_NAME"):
        pxr_plugin_paths.extend(val.split(os.pathsep))
    if val := os.getenv("LD_LIBRARY_PATH"):
        ld_path.extend(val.split(os.pathsep))
    if val := os.getenv("PYTHONPATH"):
        python_path.extend(val.split(os.pathsep))

    resolver_plugin_info_path = os.path.join(
        resolver_dir, "ayonUsdResolver", "resources", "plugInfo.json"
    )
    resolver_ld_path = os.path.join(resolver_dir, "ayonUsdResolver", "lib")
    resolver_python_path = os.path.join(
        resolver_dir, "ayonUsdResolver", "lib", "python"
    )

    if (
        not os.path.exists(resolver_python_path)
        or not os.path.exists(resolver_ld_path)
        or not os.path.exists(resolver_python_path)
    ):
        raise RuntimeError(
            f"Cant start Resolver missing path resolver_python_path: {resolver_python_path}, resolver_ld_path: {resolver_ld_path}, resolver_python_path: {resolver_python_path}"
        )
    pxr_plugin_paths.append(pathlib.Path(resolver_plugin_info_path).as_posix())
    ld_path.append(pathlib.Path(resolver_ld_path).as_posix())
    python_path.append(pathlib.Path(resolver_python_path).as_posix())

    if logger:
        logger.info(f"Asset resolver {app_name} initiated.")
    resolver_setup_info_dict = {}
    resolver_setup_info_dict["PXR_PLUGINPATH_NAME"] = os.pathsep.join(pxr_plugin_paths)
    resolver_setup_info_dict["PYTHONPATH"] = os.pathsep.join(python_path)
    if platform.system().lower() == "windows":
        resolver_setup_info_dict["PATH"] = os.pathsep.join(ld_path)
    else:
        resolver_setup_info_dict["LD_LIBRARY_PATH"] = os.pathsep.join(ld_path)

    resolver_setup_info_dict["TF_DEBUG"] = settings["usd_tf_debug"]

    resolver_setup_info_dict["AYONLOGGERLOGLVL"] = settings["ayon_log_lvl"]
    resolver_setup_info_dict["AYONLOGGERSFILELOGGING"] = settings[
        "ayon_file_logger_enabled"
    ]
    resolver_setup_info_dict["AYONLOGGERSFILEPOS"] = settings["file_logger_file_path"]
    resolver_setup_info_dict["AYON_LOGGIN_LOGGIN_KEYS"] = settings[
        "file_logger_file_path"
    ]
    return resolver_setup_info_dict
