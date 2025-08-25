import pyblish.api

from ayon_core.pipeline.publish import FARM_JOB_ENV_DATA_KEY
from ayon_usd import get_usd_pinning_envs



class CollectUSDPinningEnvVars(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.250
    label = "Collect USD Pinning Env vars (Deadline Job)"

    enabled = True
    families = [
        # Maya
        "renderlayer",
        # Houdini
        "publish.hou",  # cache submissions
        "remote_publish_on_farm",
        "redshift_rop",
        "arnold_rop",
        "mantra_rop",
        "karma_rop",
        "vray_rop"
    ]
    targets = ["local"]

    # USD Pinning file generation only supported for Maya and Houdini currently
    hosts = ["maya",
             "houdini"]

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.debug("Should not be processed on farm, skipping.")
            return

        job_env = instance.data.setdefault(FARM_JOB_ENV_DATA_KEY, {})
        usd_pinning_envs: dict = get_usd_pinning_envs(instance)

        # Log the job envs that are set
        for key, value in usd_pinning_envs.items():
            self.log.debug(f"Setting job env: {key}: {value}")

        job_env.update(usd_pinning_envs)
