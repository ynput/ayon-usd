"""Extract pinning file from USD file as a json file.

This is WIP and will be refactored in the future.
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import ayon_api
import pyblish.api
from ayon_core.pipeline import get_current_host_name, get_current_project_name
from ayon_core.pipeline.publish import KnownPublishError
from ayon_usd.standalone.usd.pinning import generate_pinning_file


class IntegrateUsdPinningFile(pyblish.api.InstancePlugin):
    """Extract pinning file from USD file as a json file."""

    order = pyblish.api.IntegratorOrder + 0.01
    label = "Integrate data into USD pinning file"
    optional = True
    families: ClassVar = ["usd", "usdrender"]

    def process(self, instance: pyblish.api.Instance) -> None:
        """Process the plugin."""

        anatomy = instance.context.data["anatomy"]
        usd_pinning_path = None

        # get pinning json file
        if "usdrender" in instance.data.get("families", []):
            self.log.debug(
                "Extracting USD pinning file for usdrender family.")
            usd_file_path = self.save_usd(instance)
            for rep in instance.data["representations"]:
                if rep["name"] == "usd_pinning":
                    usd_pinning_path = Path(rep["stagingDir"]) / rep["files"]
                    break
        else:
            if instance.data.get("versionEntity") is None:
                err_msg = "Instance was not integrated to AYON yet."
                raise KnownPublishError(err_msg)

            ayon_api.get_representation_by_name(
                get_current_project_name(),
                representation_name="usd_pinning",
                version_id=instance.data["versionEntity"]["id"])

            published_repres = instance.data.get("published_representations")
            usd_file_rootless_path = None
            usd_pinning_rootless_file_path = None

            for repre_info in published_repres.values():
                rep = repre_info["representation"]

                if rep["name"] == "usd":
                    usd_file_rootless_path = rep["attrib"]["path"]
                    continue
                if rep["name"] == "usd_pinning":
                    usd_pinning_rootless_file_path = rep["attrib"]["path"]
                    continue

                if usd_file_rootless_path and usd_pinning_rootless_file_path:
                    break

            if not usd_file_rootless_path or not usd_pinning_rootless_file_path:
                self.log.info("No USD or USD pinning file found, skipping.")
                return

            # get the full path of the usd file
            usd_file_path = Path(
                anatomy.fill_root(usd_file_rootless_path))
            usd_pinning_path = Path(
                anatomy.fill_root(usd_pinning_rootless_file_path))

        if not usd_pinning_path:
            self.log.error("No USD pinning file found.")
            return

        generate_pinning_file(
            usd_file_path.as_posix(),
            ayon_api.get_project_roots_by_site_id(get_current_project_name()),
            usd_pinning_path.as_posix())

        # clean temporary usd file
        if "usdrender" in instance.data.get("families", []):
            self.log.debug(f"Removing temporary USD file: {usd_file_path}")
            usd_file_path.unlink()

    def save_usd(self, instance: pyblish.api.Instance) -> Path:
        """Save USD file to disk.

        Args:
            instance (pyblish.api.Instance): Instance object.

        Returns:
            str: The rootless path to the saved USD file.

        """
        if get_current_host_name() == "houdini":
            return self._save_usd_from_houdini(instance)
        raise NotImplementedError(
            f"Unsupported host {get_current_host_name()}")

    def _save_usd_from_houdini(self, instance: pyblish.api.Instance) -> Path:
        """Save USD file from Houdini.

        This is called only from running host so we can safely assume
        that Houdini Addon is available.

        Args:
            instance (pyblish.api.Instance): Instance object.

        Returns:
            str: The rootless path to the saved USD file.

        """
        import hou  # noqa: F401
        from ayon_houdini.api import maintained_selection  # noqa: F401

        ropnode = hou.node(instance.data.get("instance_node"))
        filename = ropnode.parm("lopoutput").eval()
        directory = ropnode.parm("savetodirectory_directory").eval()
        filepath = Path(directory) / filename

        # create temp usdrop node
        with maintained_selection():
            temp_usd_node = hou.node("/out").createNode("usd")
            temp_usd_node.parm("lopoutput").set(
                filepath.as_posix())
            temp_usd_node.parm("loppath").set(ropnode.parm("loppath").eval())
            temp_usd_node.render()
            temp_usd_node.destroy()

        return filepath
