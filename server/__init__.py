"""USD Addon for AYON - server part."""

import os
from pathlib import Path
from typing import Any

from fastapi import Depends  # noqa: F401

from ayon_server.addons import BaseServerAddon
from .api import router


from .settings import USDSettings, convert_settings_overrides

PRIVATE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "private"


class USDAddon(BaseServerAddon):
    """USD Addon for AYON."""

    settings_model = USDSettings

    def initialize(self):
        """Initialize USD Addon."""
        self.add_router(router)
        pass

    async def convert_settings_overrides(
        self,
        source_version: str,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        convert_settings_overrides(source_version, overrides)
        return await super().convert_settings_overrides(
            source_version, overrides
        )
