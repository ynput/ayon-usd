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
        resolver_settings = self.data["project_settings"]["usd"]["asset_resolvers"]  # noqa: E501
        # project_name = self.data["project_name"]
        host_name = self.application.host_name
        variant = self.application.variant

        host_variant = f"{host_name}/{variant}"
        for resolver in resolver_settings:
            if resolver["app_name"] != host_variant:
                continue

            if resolver["platform"].lower() != system().lower():
                continue

        if all(
            host_variant not in resolver["app_name"]
            for resolver in resolver_settings
        ):
            self.log.info(f"No asset resolver settings for {host_variant}.")
            return

        pxr_plugin_paths = []
        for resolver in resolver_settings:
            if resolver["app_name"] != host_variant:
                continue

            if resolver["platform"].lower() != system().lower():
                continue

            self.log.info(f"Initializing asset resolver for {host_variant}.")
            download_dir = get_download_dir()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_file = executor.submit(
                    download_zip,
                    resolver["uri"],
                    download_dir,
                    None
                )
                file = future_file.result()

            resolver_dir = Path(Path(file).stem)
            if resolver_dir.is_dir():
                self.log.info(
                    f"Existing resolver found in {resolver_dir.as_posix()}.")
            else:
                self.log.info(
                    f"Extracting resolver to {resolver_dir.as_posix()}.")
                extract_zip_file(file, download_dir)

            pxr_plugin_paths.append(
                (
                    resolver_dir / "ayonUsdResolver" /
                    "resources" / "plugInfo.json"
                ).as_posix()
            )
            self.log.info(f"Asset resolver {host_variant} initiated.")

        self.launch_context.env["PXR_PLUGINPATH_NAME"] = os.pathsep.join(
            pxr_plugin_paths
        )
