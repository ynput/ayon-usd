import os
from typing import ClassVar
import pyblish.api
import ayon_api
from ayon_core.pipeline import OptionalPyblishPluginMixin
from ayon_core.pipeline.publish import FARM_JOB_ENV_DATA_KEY
from ayon_usd.standalone.usd.pinning import generate_pinning_file


class ExtractSkeletonPinningJSON(pyblish.api.InstancePlugin,
                                 OptionalPyblishPluginMixin):
    """Extract Skeleton Pinning JSON file.
    
    This plugin generates a Pinning JSON file, which is useful
    for farm submission to decrease the overhead of resolving Entity URIs.

    This extractor does the following:
        - Generates the pinning file as `__render__pin.json` 
            and places it next to `__render__.usd`.
        - Updates farm environment variables with the pinning file
            location and a flag to enable pinning mode on the farm.

    Notes:
        To generate the pinning file, the USD file path must be accessible
        beforehand. Therefore, **`__render__.usd`** must already exist so
        it can be parsed to create the pinning file accordingly.

        Pinning preferably works with these render targets 
            - `Farm rendering`and
            - `Local Export, Farm Render`

        With the `Farm Export, Farm Render` target, the plugin will still
        function, but this workflow results in the USD file being exported
        twice: once by this plugin and then again (overwritten) by the
        dedicated export job on the farm.
    """

    label = "Extract Skeleton Pinning JSON"
    # Run After Extract ROP.
    order = pyblish.api.ExtractorOrder + 0.49
    hosts = ["houdini"]
    families: ClassVar = ["usdrender"]

    settings_category: ClassVar = "usd"

    def process(self, instance: pyblish.api.Instance) -> None:
        """Process the plugin."""
        if not self.is_active(instance.data):
            return

        if not instance.data["farm"]:
            return

        usd_file_path = self.get_usd_file_path(instance)
        usd_file_name = os.path.basename(usd_file_path)
        usd_file_name = os.path.splitext(usd_file_name)[0]

        pin_file_name = f"{usd_file_name}_pin.json"
        pin_file_path = os.path.join(
            os.path.dirname(usd_file_path), pin_file_name
        )

        AYON_USD_RESOLVER_PINNING_ROOTS = ayon_api.get_AYON_USD_RESOLVER_PINNING_ROOTS_by_site_id(
            instance.context.data["projectName"]
        )
        generate_pinning_file(
            usd_file_path,
            AYON_USD_RESOLVER_PINNING_ROOTS,
            pin_file_path
        )

        self.log.debug(f"Pinning file was created at: '{pin_file_path}'.")
        pin_file_path = self.get_rootless_path(instance, pin_file_path)

        # Set farm env keys
        farm_job_data: dict[str, str] = instance.data.setdefault(
		    FARM_JOB_ENV_DATA_KEY, {}
		)
        farm_job_data.update({
            "AYON_USD_RESOLVER_PINNING_FILE": pin_file_path,
            "AYON_USD_RESOLVER_ENABLE_PINNING": "1",
        })

    def get_usd_file_path(self, instance):
        usd_file_path = instance.data.get(
            "ifdFile", None
        )

        # Return "ifdFile" if exists. With some render targets, the file is
        # set but not saved to disk.
        if usd_file_path and os.path.isfile(usd_file_path):
            return usd_file_path

        # Export __render__.usd if file doesn't exist already.
        return self.export_usd_file(instance)

    def export_usd_file(self, instance) -> str:
        """Save USD file from Houdini.

        This is called only from running host so we can safely assume
        that Houdini Addon is available.

        Args:
            instance (pyblish.api.Instance): Instance object.

        Returns:
            str: The rootless path to the saved USD file.
        """
        import hou
        from ayon_houdini.api import maintained_selection

        ropnode = hou.node(instance.data.get("instance_node"))
        filename = ropnode.parm("lopoutput").eval()
        directory = ropnode.parm("savetodirectory_directory").eval()
        filepath = os.path.join(directory, filename)

        # create temp usdrop node
        with maintained_selection():
            temp_usd_node = hou.node("/out").createNode("usd")
            temp_usd_node.parm("lopoutput").set(filepath)
            temp_usd_node.parm("loppath").set(ropnode.parm("loppath").eval())
            temp_usd_node.render()
            temp_usd_node.destroy()

        return filepath

    def get_rootless_path(self, instance, path):
        anatomy = instance.context.data["anatomy"]
        # Convert path dir to `{root}/rest/of/path/...` with Anatomy
        success, rootless_path = anatomy.find_root_template_from_path(
            path)
        if not success:
            # `rootless_path` is not set to `output_dir` if none of roots match
            self.log.warning(
                f"Could not find root path for remapping '{path}'."
                " This may cause issues on farm."
            )
            rootless_path = path
        return rootless_path
