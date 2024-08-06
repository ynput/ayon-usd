"""USD Addon utility functions."""

import json
import os
import platform
import pathlib
import sys

import ayon_api
from ayon_usd.ayon_bin_client.ayon_bin_distro.work_handler import worker
from ayon_usd.ayon_bin_client.ayon_bin_distro.util import zip
from ayon_usd import config


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


def is_usd_lib_download_needed() -> bool:
    # TODO redocument

    usd_lib_dir = os.path.abspath(get_downloaded_usd_root())
    if os.path.exists(usd_lib_dir):

        ctl = config.get_global_lake_instance()
        lake_fs_usd_lib_path = f"{config.get_addon_settings_value(config.get_addon_settings(),config.ADDON_SETTINGS_LAKE_FS_REPO_URI)}{config.get_usd_lib_conf_from_lakefs()}"

        with open(config.ADDON_DATA_JSON_PATH, "r") as data_json:
            addon_data_json = json.load(data_json)
        try:
            usd_lib_lake_fs_time_stamp_local = addon_data_json[
                "usd_lib_lake_fs_time_cest"
            ]
        except KeyError:
            return True

        if (
            usd_lib_lake_fs_time_stamp_local
            == ctl.get_element_info(lake_fs_usd_lib_path)["Modified Time"]
        ):
            return False

    return True


def download_and_extract_resolver(resolver_lake_fs_path: str, download_dir: str) -> str:
    """downloads an individual object based on the lake_fs_path and extracts the zip into the specific download_dir

    Args
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
    Gets LakeFs path that can be used with copy element to download
    specific resolver, this will prioritize `lake_fs_overrides` over
    asset_resolvers entries.

    Returns: str: LakeFs object path to be used with lake_fs_py wrapper

    """
    resolver_overwrite_list = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_ASSET_RESOLVERS_OVERWRITES
    )

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
            return resolver_overwrite["lake_fs_path"]

    resolver_list = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_ASSET_RESOLVERS
    )
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

    lake_base_path = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_LAKE_FS_REPO_URI
    )
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

    resolver_setup_info_dict["TF_DEBUG"] = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_USD_TF_DEBUG
    )

    resolver_setup_info_dict["AYONLOGGERLOGLVL"] = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_USD_RESOLVER_LOG_LVL
    )

    resolver_setup_info_dict["AYONLOGGERSFILELOGGING"] = (
        config.get_addon_settings_value(
            settings, config.ADDON_SETTINGS_USD_RESOLVER_LOG_FILLE_LOOGER_ENABLED
        )
    )

    resolver_setup_info_dict["AYONLOGGERSFILEPOS"] = config.get_addon_settings_value(
        settings, config.ADDON_SETTINGS_USD_RESOLVER_LOG_FILLE_LOOGER_FILE_PATH
    )

    resolver_setup_info_dict["AYON_LOGGIN_LOGGIN_KEYS"] = (
        config.get_addon_settings_value(
            settings, config.ADDON_SETTINGS_USD_RESOLVER_LOG_LOGGIN_KEYS
        )
    )

    return resolver_setup_info_dict
