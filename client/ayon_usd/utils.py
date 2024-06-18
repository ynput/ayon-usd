"""USD Addon utility functions."""

import copy
import datetime
import hashlib
import json
import os
import platform
import subprocess
import zipfile
from pathlib import Path
from typing import Union

import ayon_api
from ayon_core.lib.local_settings import get_ayon_appdirs
from ayon_usd import version

CURRENT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR: Path = CURRENT_DIR / "downloads"
NOT_SET = type("NOT_SET", (), {"__bool__": lambda: False})()
ADDON_NAME: str = version.name
ADDON_VERSION: str = version.__version__


class _USDOptions:
    download_needed = None
    downloaded_root = NOT_SET


class _USDCache:
    addon_settings = NOT_SET


def get_addon_settings():
    """Get addon settings.

    Return:
        dict: Addon settings.

    """
    if _USDCache.addon_settings is NOT_SET:
        _USDCache.addon_settings = ayon_api.get_addon_settings(
            ADDON_NAME, ADDON_VERSION
        )
    return copy.deepcopy(_USDCache.addon_settings)


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


def _check_args_returncode(args):
    try:
        kwargs = {}
        if platform.system().lower() == "windows":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

        if hasattr(subprocess, "DEVNULL"):
            proc = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs
            )
            proc.wait()
        else:
            with open(os.devnull, "w") as devnull:
                proc = subprocess.Popen(args, stdout=devnull, stderr=devnull, **kwargs)
                proc.wait()

    except Exception:
        return False
    return proc.returncode == 0


def _get_addon_endpoint():
    return f"addons/{ADDON_NAME}/{ADDON_VERSION}"


def _get_info_path(name):
    return get_ayon_appdirs("addons", f"{ADDON_NAME}-{name}.json")


def _filter_file_info(name):
    filepath = _get_info_path(name)

    if os.path.exists(filepath):
        with open(filepath, "r") as stream:
            return json.load(stream)
    return []


def _store_file_info(name, info):
    """Store info to file."""
    filepath = _get_info_path(name)
    root, filename = os.path.split(filepath)
    if not os.path.exists(root):
        os.makedirs(root, exist_ok=True)
    with open(filepath, "w") as stream:
        json.dump(info, stream)


def get_downloaded_usd_info():
    """Get USD info from file."""
    return _filter_file_info("usd")


def store_downloaded_usd_info(usd_info):
    """Store USD info to file.

    Args:
        usd_info (list[dict[str, str]]): USD info to store.

    """
    _store_file_info("usd", usd_info)


def is_usd_download_needed(addon_settings=None):
    """Check if is download needed.

    Returns:
        bool: Should be config downloaded.

    """

    return True

    if _USDOptions.download_needed is not None:
        return _USDOptions.download_needed

    if addon_settings is None:
        addon_settings = get_addon_settings()

    download_needed = False
    if addon_settings["use_downloaded"]:
        # Check what is required by server
        usd_root = get_downloaded_usd_root()
        download_needed = not bool(usd_root)

    _USDOptions.download_needed = download_needed
    return _USDOptions.download_needed


def extract_zip_file(progress_item, zip_file_path: str, dest_dir: str):
    """Extract a zip file to a destination directory.

    Args:
        zip_file_path (str): The path to the zip file.
        dest_dir (str): The directory where the zip file should be extracted.

    """

    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)

    foulder_name = os.path.basename(zip_file_path).replace(".zip", "")
    return os.path.join(dest_dir, foulder_name)


def get_downloaded_usd_root() -> Union[str, None]:
    """Get downloaded USD binary root path."""
    if _USDOptions.downloaded_root is not NOT_SET:
        return _USDOptions.downloaded_root

    server_usd_info = _find_file_info("ayon_usd", get_server_files_info())
    if not server_usd_info:
        return None

    root = None
    for existing_info in get_downloaded_usd_info():
        if existing_info["checksum"] != server_usd_info["checksum"]:
            continue
        found_root = existing_info["root"]
        if os.path.exists(found_root):
            root = found_root
            break

    _USDOptions.downloaded_root = root
    return _USDOptions.downloaded_root
