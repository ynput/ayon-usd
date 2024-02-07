import os
import json
import platform
import datetime
import subprocess
import copy

import ayon_api

from ayon_common import (
    get_ayon_appdirs,
    validate_file_checksum,
    extract_archive_file,
)
from .version import __version__


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(CURRENT_DIR, "downloads")
NOT_SET = type("NOT_SET", (), {"__bool__": lambda: False})()
ADDON_NAME = "usd"


class _USDOptions:
    download_needed = None
    downloaded_root = NOT_SET


class _USDCache:
    addon_settings = NOT_SET


def get_addon_settings():
    if _USDCache.addon_settings is NOT_SET:
        _USDCache.addon_settings = ayon_api.get_addon_settings(
            ADDON_NAME, __version__
        )
    return copy.deepcopy(_USDCache.addon_settings)


def get_download_dir(create_if_missing=True):
    """Dir path where files are downloaded."""

    if create_if_missing and not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
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
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs
            )
            proc.wait()
        else:
            with open(os.devnull, "w") as devnull:
                proc = subprocess.Popen(
                    args, stdout=devnull, stderr=devnull, **kwargs
                )
                proc.wait()

    except Exception:
        return False
    return proc.returncode == 0


def _get_addon_endpoint():
    return "addons/{}/{}".format(ADDON_NAME, __version__)


def _get_info_path(name):
    return get_ayon_appdirs(
        "addons", "{}-{}.json".format(ADDON_NAME, name))


def filter_file_info(name):
    filepath = _get_info_path(name)
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as stream:
                return json.load(stream)
    except Exception:
        print("Failed to load {} info from {}".format(
            name, filepath
        ))
    return []


def store_file_info(name, info):
    filepath = _get_info_path(name)
    root, filename = os.path.split(filepath)
    if not os.path.exists(root):
        os.makedirs(root)
    with open(filepath, "w") as stream:
        json.dump(info, stream)


def get_downloaded_usd_info():
    return filter_file_info("usd")


def store_downloaded_usd_info(usd_info):
    store_file_info("usd", usd_info)


def get_server_files_info():
    """Receive zip file info from server.

    Information must contain at least 'filename' and 'hash' with md5 zip
    file hash.

    Returns:
        list[dict[str, str]]: Information about files on server.
    """

    response = ayon_api.get("{}/files_info".format(
        _get_addon_endpoint()
    ))
    response.raise_for_status()
    return response.data


def _find_file_info(name, files_info):
    """Find file info by name.

    Args:
        name (str): Name of file to find.
        files_info (list[dict[str, str]]): List of file info dicts.

    Returns:
        Union[dict[str, str], None]: File info data.
    """

    platform_name = platform.system().lower()
    return next(
        (
            file_info
            for file_info in files_info
            if (
                file_info["name"] == name
                and file_info["platform"] == platform_name
            )
        ),
        None
    )


def get_downloaded_usd_root():
    if _USDOptions.downloaded_root is not NOT_SET:
        return _USDOptions.downloaded_root

    server_usd_info = _find_file_info("usd", get_server_files_info())
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


def is_usd_download_needed(addon_settings=None):
    """Check if is download needed.

    Returns:
        bool: Should be config downloaded.
    """

    if _USDOptions.download_needed is not None:
        return _USDOptions.download_needed

    if addon_settings is None:
        addon_settings = get_addon_settings()
    download_needed = False
    if addon_settings["usd"]["use_downloaded"]:
        # Check what is required by server
        usd_root = get_downloaded_usd_root()
        download_needed = not bool(usd_root)

    _USDOptions.download_needed = download_needed
    return _USDOptions.download_needed


def _download_file(file_info, dirpath, progress=None):
    filename = file_info["filename"]
    checksum = file_info["checksum"]
    checksum_algorithm = file_info["checksum_algorithm"]

    zip_filepath = ayon_api.download_addon_private_file(
        ADDON_NAME,
        __version__,
        filename,
        dirpath,
        progress=progress
    )

    try:
        if not validate_file_checksum(
            zip_filepath, checksum, checksum_algorithm
        ):
            raise ValueError(
                "Downloaded file hash does not match expected hash"
            )
        extract_archive_file(zip_filepath, dirpath)

    finally:
        os.remove(zip_filepath)


def download_usd(progress=None):
    """Download usd from server.

    Todos:
        Add safeguard to avoid downloading of the file from multiple
            processes at once.

    Args:
        progress (ayon_api.TransferProgress): Keep track about download.
    """

    dirpath = os.path.join(get_download_dir(), "usd")

    files_info = get_server_files_info()
    file_info = _find_file_info("usd", files_info)
    if file_info is None:
        raise ValueError((
            "Couldn't find usd file for platform '{}'"
        ).format(platform.system()))

    _download_file(file_info, dirpath, progress=progress)

    usd_info = get_downloaded_usd_info()
    existing_item = next(
        (
            item
            for item in usd_info
            if item["root"] == dirpath
        ),
        None
    )
    if existing_item is None:
        existing_item = {}
        usd_info.append(existing_item)
    existing_item.update({
        "root": dirpath,
        "checksum": file_info["checksum"],
        "checksum_algorithm": file_info["checksum_algorithm"],
        "downloaded": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    store_downloaded_usd_info(usd_info)

    _USDOptions.download_needed = False
    _USDOptions.downloaded_root = NOT_SET
