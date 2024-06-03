"""Pre-launch hook to initialize asset resolver for the application."""
import concurrent.futures
import os
from platform import system
from pathlib import Path

import requests
from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_usd import get_download_dir, extract_zip_file


def download_zip(url, directory, filename=None):
    """
    Download a zip file from a URL.

    Args:
        url (str): The URL of the zip file.
        directory (str): The directory to save the zip file in.
        filename (str, optional): The name of the file
            to save the zip file as.

    Returns:
        str: The name of the file the zip file was saved as.
    """
    with requests.get(url) as response:
        # get filename from response headers
        if "Content-Disposition" in response.headers:
            filename = response.headers["Content-Disposition"].split(
                "filename=")[-1].strip('"')
        if not filename:
            # if not in headers, try to use last part of the URI without
            # query string
            filename = url.split("/")[-1].split("?")[0]
        with open(os.path.join(directory,filename), 'wb') as file:
            file.write(response.content)

    return filename


class InitializeAssetResolver(PreLaunchHook):
    """Initialize asset resolver for the application.

    Asset resolver is used to resolve assets in the application.
    """

    app_groups = {
        "maya",
        "nuke",
        "nukestudio",
        "houdini",
        "blender",
        "unreal"
    }
    launch_types = {LaunchTypes.local}

    def execute(self):
        """Pre-launch hook entry method."""
        resolver_settings = self.data["project_settings"]["ayon_usd"]["asset_resolvers"]  # noqa: E501
        self.log.debug(self.app_group)

        for resolver in resolver_settings:
            if resolver["app_name"] != self.app_name:
                continue

            if resolver["platform"].lower() != system().lower():
                continue

        if all(
            self.app_name not in resolver["app_name"]
            for resolver in resolver_settings
        ):
            self.log.info(
                f"No USD asset resolver settings for {self.app_name}.")
            return

        pxr_plugin_paths = []
        ld_path = []
        python_path =[]
        for resolver in resolver_settings:
            if resolver["app_name"] != self.app_name:
                continue

            if resolver["platform"].lower() != system().lower():
                continue

            self.log.info(
                f"Initializing USD asset resolver for [ {self.app_name} ] .")
            download_dir = get_download_dir()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_file = executor.submit(
                    download_zip,
                    resolver["uri"],
                    download_dir,
                    None
                )
                file = future_file.result()

            resolver_dir = download_dir / Path(Path(file).stem)
            if resolver_dir.is_dir():
                self.log.info(
                    "Existing resolver found in "
                    f"['{resolver_dir.as_posix()}'].")
            else:
                self.log.info(
                    f"Extracting resolver to ['{resolver_dir.as_posix()}'].")
                extract_zip_file(
                    (download_dir / Path(file)).as_posix(),
                    download_dir)

            pxr_plugin_paths.append(
                (
                    resolver_dir / "ayonUsdResolver" /
                    "resources" / "plugInfo.json"
                ).as_posix()
            )
            ld_path.append(
                (resolver_dir / "ayonUsdResolver" / "lib").as_posix())
            python_path.append(
                (resolver_dir / "ayonUsdResolver" /
                 "lib" / "python").as_posix())
            self.log.info(f"Asset resolver {self.app_name} initiated.")

        if self.launch_context.env.get("PXR_PLUGINPATH_NAME"):
            pxr_plugin_paths.append(
                self.launch_context.env["PXR_PLUGINPATH_NAME"].split(
                    os.pathsep)
            )

        self.launch_context.env["PXR_PLUGINPATH_NAME"] = os.pathsep.join(
            pxr_plugin_paths
        )

        self.launch_context.env["PYTHONPATH"] += os.pathsep.join(python_path)

        if ld_path:
            env_key = "LD_LIBRARY_PATH"
            if system().lower() == "windows":
                env_key = "PATH"
            existing_path = self.launch_context.env.get(env_key)
            if existing_path:
                ld_path.insert(0, existing_path)
                self.launch_context.env[env_key] = os.pathsep.join(ld_path)

        # TODO: move debug options to AYON settings
        self.launch_context.env["TF_DEBUG"] = "1"
        self.launch_context.env["AYONLOGGERLOGLVL"] = "INFO"
