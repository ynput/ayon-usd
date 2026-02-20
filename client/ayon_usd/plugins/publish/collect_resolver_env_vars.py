"""Collect USD resolver environment variables for farm job submission.

Emits platform-independent config vars (TF_DEBUG, logger settings) into
the farm job environment.  Path-based vars (PXR_PLUGINPATH_NAME, PYTHONPATH,
LD_LIBRARY_PATH) are NOT set here — they are injected by the
``pre_resolver_init`` hook which runs during ``extractenvironments`` on each
worker, producing paths correct for that worker's OS.
"""

import os

import pyblish.api

from ayon_core.pipeline.publish import FARM_JOB_ENV_DATA_KEY


class CollectResolverEnvVars(pyblish.api.InstancePlugin):
    """Collect USD resolver env vars for farm jobs.

    Non-path settings (``TF_DEBUG``, logger config) are read directly
    from the USD addon settings and added to the farm job environment.
    """

    order = pyblish.api.CollectorOrder + 0.251
    label = "Collect USD Resolver Env Vars (Farm Job)"

    families = [
        # Maya
        "renderlayer",
        # Houdini
        "usdrender",
        "publish.hou",
        "remote_publish_on_farm",
        "redshift_rop",
        "arnold_rop",
        "mantra_rop",
        "karma_rop",
        "vray_rop",
    ]
    targets = ["local"]
    hosts = ["maya", "houdini"]

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.debug("Not a farm instance, skipping.")
            return

        settings = instance.context.data["project_settings"]
        job_env = instance.data.setdefault(FARM_JOB_ENV_DATA_KEY, {})

        # --- Non-path config (from USD addon settings) -------------------
        usd_settings = settings.get("usd", {})
        resolver_cfg = usd_settings.get("ayon_usd_resolver", {})
        config_vars = {
            "TF_DEBUG": usd_settings.get("usd", {}).get("usd_tf_debug", ""),
            "AYONLOGGERLOGLVL": resolver_cfg.get("ayon_log_lvl", ""),
            "AYONLOGGERSFILELOGGING": resolver_cfg.get(
                "ayon_file_logger_enabled", ""
            ),
            "AYONLOGGERSFILEPOS": resolver_cfg.get(
                "file_logger_file_path", ""
            ),
            "AYON_LOGGIN_LOGGIN_KEYS": resolver_cfg.get(
                "ayon_logger_logging_keys", ""
            ),
        }
        for key, value in config_vars.items():
            if value:
                self.log.debug(f"Setting job env (config): {key}: {value}")
                job_env[key] = str(value)
