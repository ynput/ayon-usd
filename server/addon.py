"""USD Addon for AYON."""
import os
from pathlib import Path
from typing import Any

from ayon_server.addons import BaseServerAddon
from fastapi import Depends  # noqa: F401

from .api import router
from .settings import USDSettings, convert_settings_overrides

PRIVATE_DIR = Path(
    os.path.dirname(os.path.abspath(__file__))).parent / "private"


class USDAddon(BaseServerAddon):
    """USD Addon for AYON."""

    settings_model = USDSettings

    def initialize(self) -> None:
        """Initialize USD Addon."""
        self.add_router(router)

    async def convert_settings_overrides(
        self,
        source_version: str,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert settings overrides for USD Addon.

        Args:
            source_version (str): The version of the source settings.
            overrides (dict[str, Any]): The settings overrides to convert.

        Returns:
            dict[str, Any]: The converted settings overrides.

        """
        convert_settings_overrides(source_version, overrides)
        return await super().convert_settings_overrides(
            source_version, overrides
        )
