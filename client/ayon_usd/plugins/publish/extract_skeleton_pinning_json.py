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
import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.pipeline import OptionalPyblishPluginMixin, KnownPublishError


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

        try:
            staging_dir = Path(instance.data["stagingDir"])
        except KeyError:
            self.log.debug("No staging directory on instance found.")
            try:
                staging_dir = Path(instance.data["ifdFile"]).parent
            except KeyError as e:
                self.log.error("No staging directory found.")
                raise KnownPublishError("Cannot determine staging directory.") from e

        pin_file = f"{staging_dir.stem}_pin.json"
        pin_file_path = staging_dir.joinpath(pin_file)
        pin_representation = {
            "name": "usd_pinning",
            "ext": "json",
            "files": pin_file_path.name,
            "stagingDir": staging_dir.as_posix(),
        }
        current_timestamp = datetime.now().timestamp()
        skeleton_pinning_data = {
            "timestamp": current_timestamp,
        }
        Path.mkdir(staging_dir, parents=True, exist_ok=True)
        with open(pin_file_path, "w") as f:
            json.dump(skeleton_pinning_data, f, indent=4)

        instance.data["representations"].append(pin_representation)
