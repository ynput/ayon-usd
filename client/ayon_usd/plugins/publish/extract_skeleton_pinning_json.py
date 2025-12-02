"""Extract Skeleton Pinning JSON file.

This extractor creates a simple placeholder JSON file that is filled by
Integrator plugin (Integrate Pinning File). This way, publishing process
is much more simple and doesn't require any hacks.

Side effects:
    - Creates a JSON file with skeleton pinning data that doesn't contain
      any real data, it's just a placeholder. If, for whatever reason, the
      publishing process is interrupted, the placeholder file will be
      still there even if the real data is not present.

    - Adds a timestamp to the JSON file. This timestamp can be later used
      to check if the processed data is up-to-date.

"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.pipeline import OptionalPyblishPluginMixin, KnownPublishError
from ayon_core.pipeline.publish import FARM_JOB_ENV_DATA_KEY
from ayon_core.pipeline.farm.tools import iter_expected_files


class ExtractSkeletonPinningJSON(pyblish.api.InstancePlugin,
                                 OptionalPyblishPluginMixin):
    """Extract Skeleton Pinning JSON file.

    Extracted JSON file doesn't contain any data, it's just a placeholder
    that is filled by Integrator plugin (Integrate Pinning File).
    """

    label = "Extract Skeleton Pinning JSON"
    order = pyblish.api.ExtractorOrder + 0.49
    families: ClassVar = ["usd", "usdrender"]

    settings_category: ClassVar = "usd"

    # USD Pinning file generation only supported for Maya and Houdini currently
    hosts = ["maya", "houdini"]

    @staticmethod
    def _has_usd_representation(representations: list) -> bool:
        return any(
            representation.get("name") == "usd"
            for representation in representations
        )

    def process(self, instance: pyblish.api.Instance) -> None:
        """Process the plugin."""
        if not self.is_active(instance.data):
            return

        # we need to handle usdrender differently as usd for rendering will
        # be produced much later on the farm.
        if "usdrender" not in instance.data.get("families", []):
            if not self._has_usd_representation(instance.data["representations"]):
                self.log.info("No USD representation found, skipping.")
                return

        pin_file_dir= self.get_pin_file_dir(instance)
        pin_file = f"{instance.data['productName']}_pin.json"
        pin_file_path = pin_file_dir.joinpath(pin_file)

        pin_representation = {
            "name": "usd_pinning",
            "ext": "json",
            "files": pin_file_path.name,
            "stagingDir": pin_file_dir.as_posix(),
        }
        current_timestamp = datetime.now().timestamp()
        skeleton_pinning_data = {
            "timestamp": current_timestamp,
        }
        Path.mkdir(pin_file_dir, parents=True, exist_ok=True)
        with open(pin_file_path, "w") as f:
            json.dump(skeleton_pinning_data, f, indent=4)

        self.log.debug(f"Pinning File was created at: '{pin_file_path}'.")
        instance.data["representations"].append(pin_representation)

        # Set farm env keys
        if FARM_JOB_ENV_DATA_KEY not in instance.data:
            instance.data[FARM_JOB_ENV_DATA_KEY] = {}

        pin_file_path = self.get_rootless_path(instance, pin_file_path)
        instance.data[FARM_JOB_ENV_DATA_KEY].update({
            "PINNING_FILE_PATH": pin_file_path,
            "ENABLE_STATIC_GLOBAL_CACHE": "1",
        })

    def get_pin_file_dir(self, instance) -> Path:
        """Get pin file location

        Use the same logic used for obtaining the render metadata json file
        and default to stagingDir.

        For additional Info, see 
            ayon_core.pipeline.farm.pyblish_functions.create_metadata_path

        Returns:
            pin_file_dir(Path): directory for pin file.
        """
        pin_file_dir = instance.data.get(
            "publishRenderMetadataFolder",
            instance.data.get("outputDir")
        )
        if not pin_file_dir and instance.data.get("expectedFiles"):
            expected_files = instance.data["expectedFiles"]
            first_file = next(iter_expected_files(expected_files))
            pin_file_dir = os.path.dirname(first_file)

        if not pin_file_dir:
            pin_file_dir = instance.data["stagingDir"]

        if pin_file_dir:
            return Path(pin_file_dir)

        self.log.error("No staging directory found.")
        raise KnownPublishError("Cannot determine staging directory.")    

    def get_rootless_path(self, instance, path):
        anatomy = instance.context.data["anatomy"]
        # Convert output dir to `{root}/rest/of/path/...` with Anatomy
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