"""USD Addon utility functions."""

import os
import platform
from pathlib import Path
from ayon_usd import version
from ayon_usd.utils import get_addon_settings
from ayon_usd.ayon_bin_client.ayon_bin_distro.lakectlpy import wrapper

CURRENT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR: Path = CURRENT_DIR / "downloads"
NOT_SET = type("NOT_SET", (), {"__bool__": lambda: False})()
ADDON_NAME: str = version.name
ADDON_VERSION: str = version.__version__


settings = get_addon_settings()
lake_ctl_instance_glob = wrapper.LakeCtl(
    server_url=settings["ayon_usd_lake_fs_server_uri"],
    access_key_id=settings["access_key_id"],
    secret_access_key=settings["secret_access_key"],
)


# TODO i believe this should be in in utils but that would be an circular import. so i assume one off the scripts dose something it should not doo
# TODO list_repo_objects needs the uri to look like this lakefs://ayon-usd/V001/ the "/" is important at the end this needs to be ensured
def get_usd_lib_conf_from_lakefs():
    item_list = lake_ctl_instance_glob.list_repo_objects(
        settings["ayon_usd_lake_fs_server_repo"]
    )

    lake_fs_usd_zip_path = ""
    for item in item_list:
        if "AyonUsdBin/usd" in item and platform.system().lower() in item:
            lake_fs_usd_zip_path = item
    return lake_fs_usd_zip_path


USD_ZIP_PATH = Path(
    os.path.join(
        DOWNLOAD_DIR,
        os.path.basename(
            f"{settings['ayon_usd_lake_fs_server_repo']}{get_usd_lib_conf_from_lakefs()}"
        ),
    )
)
USD_LIB_PATH = Path(str(USD_ZIP_PATH).replace(USD_ZIP_PATH.suffix, ""))
