"""USD Addon utility functions."""

import json
import os
import platform
import pathlib
import sys

from ayon_core.lib import is_headless_mode_enabled 
if not is_headless_mode_enabled():
    from qtpy import QtWidgets

from ayon_usd.ayon_bin_client.ayon_bin_distro.work_handler import worker
from ayon_usd.ayon_bin_client.ayon_bin_distro.util import zip
from ayon_usd import config

USD_ADDON_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(USD_ADDON_ROOT_DIR, "downloads")
ADDON_DATA_JSON_PATH = os.path.join(DOWNLOAD_DIR, "ayon_usd_addon_info.json")

def info_popup(title: str, message: str):
    """ creates a pop up in a QApplication to display a message with an okay button. 
    it's a blocking function.
    when the okay button is pressed the QApplication will close and the function will release its block.

    Args:
        title (str): window title
        message (str): Popup Message
    """
    app = QtWidgets.QApplication()   
    msg = QtWidgets.QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QtWidgets.QMessageBox.Information)
    
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.setDefaultButton(QtWidgets.QMessageBox.Ok)
    
    if hasattr(msg, 'exec'):
        msg.exec() 
    else:
        msg.exec_() 
    
    app.exit() 

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


def is_usd_lib_download_needed(settings: dict) -> bool:
    """Return whether a USD libraries need (re-)download from the Lake FS
    repository.

    This will be the case if it's the first time syncing, the timestamp on the
    server is newer or the local files have been removed.

    Arguments:
        settings (dict): Studio or Project settings.

    Returns:
        bool: When true, a new download is required.

    """
    lake_fs_repo = settings["ayon_usd"]["lakefs"]["server_repo"]
    usd_lib_dir = os.path.abspath(get_downloaded_usd_root(lake_fs_repo))
    if not os.path.exists(usd_lib_dir):
        return True

    with open(ADDON_DATA_JSON_PATH, "r") as data_json:
        addon_data_json = json.load(data_json)
    try:
        usd_lib_lake_fs_time_stamp_local = addon_data_json[
            "usd_lib_lake_fs_time_cest"
        ]
    except KeyError:
        return True

    lake_fs_usd_lib_path = config.get_lakefs_usdlib_path(settings)
    lake_fs = config.get_global_lake_instance(settings)
    lake_fs_timestamp = lake_fs.get_element_info(
        lake_fs_usd_lib_path).get("Modified Time")
    if (
        not lake_fs_timestamp
        or usd_lib_lake_fs_time_stamp_local != lake_fs_timestamp
    ):
        return True
    return False


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


def get_resolver_to_download(settings, app_name: str) -> str:
    """
    Gets LakeFs path that can be used with copy element to download
    specific resolver, this will prioritize `lake_fs_overrides` over
    asset_resolvers entries.

    Returns: str: LakeFs object path to be used with lake_fs_py wrapper

    """
    lakefs = settings["ayon_usd"]["lakefs"]
    resolver_overwrite_list = lakefs["lake_fs_overrides"]
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

    resolver_list = lakefs["asset_resolvers"]
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

    lake_fs_repo_uri = lakefs["server_repo"]
    resolver_lake_path = lake_fs_repo_uri + resolver["lake_fs_path"]
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

    resolver_settings = settings["ayon_usd"]["ayon_usd_resolver"]
    return {
        "TF_DEBUG": settings["ayon_usd"]["usd"]["usd_tf_debug"],
        "AYONLOGGERLOGLVL": resolver_settings["ayon_log_lvl"],
        "AYONLOGGERSFILELOGGING": resolver_settings["ayon_file_logger_enabled"],  # noqa
        "AYONLOGGERSFILEPOS": resolver_settings["file_logger_file_path"],
        "AYON_LOGGIN_LOGGIN_KEYS": resolver_settings["ayon_logger_logging_keys"],  # noqa
        "PXR_PLUGINPATH_NAME": pxr_pluginpath_name,
        "PYTHONPATH": python_path,
        ld_path_key: ld_library_path
    }
