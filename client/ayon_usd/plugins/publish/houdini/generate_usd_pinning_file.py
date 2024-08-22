"""
Empty Pyblish plugin that used for inspection.

Note: 
    PLugin's order is an int constant.
    Current Orders:
        pyblish.api.CollectorOrder == 0
        pyblish.api.ValidatorOrder == 1
        pyblish.api.ExtractorOrder == 2
        pyblish.api.IntegratorOrder == 3


    Sometimes, you can add some number to the order
      to adjust its order.
    You may want to adjust the order to make it run
      after a particular plugin.
"""

import os
import pyblish.api
import ayon_api
from ayon_core.pipeline.publish import KnownPublishError
from ayon_usd.standalone.usd import pinning


root_info = ayon_api.get_project_roots_for_site(os.environ.get("AYON_PROJECT_NAME"))


class Dumb(pyblish.api.InstancePlugin):
    """Dumb"""

    order = pyblish.api.IntegratorOrder + 0.3
    label = "Dumb"
    families = ["usdrop"]
    hosts = ["houdini"]

    enabled = True

    def process(self, instance):

        publish_dir = instance.data["publishDir"]
        publish_usd_file = instance.data["representations"][0]["published_path"]
        pinning_file_path = os.path.join(
            publish_dir, publish_usd_file.split(".")[0] + "_pinning_file.json"
        )
        if not os.path.exists(publish_usd_file):
            self.log.error(f"Usd file missing {publish_usd_file}")
            raise KnownPublishError(f"Usd File Missing {publish_usd_file}")

        pinning.generate_pinning_file(publish_usd_file, root_info, pinning_file_path)
        self.log.debug(
            f"Saving Pinning File for Usd Render Locatoin:{pinning_file_path}, for usd file {publish_usd_file}"
        )
