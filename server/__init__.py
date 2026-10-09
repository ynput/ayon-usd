"""USD Addon for AYON - server part."""

import os
from pathlib import Path
from typing import Any

from ayon_server.addons import BaseServerAddon
from fastapi import Depends  # ruff:ignore[unused-import]

from .settings import (
    DEFAULT_VALUES,
    USDSettings,
    convert_settings_overrides,
)

PRIVATE_DIR = (
    Path(os.path.dirname(os.path.abspath(__file__))).parent / "private"
)


class USDAddon(BaseServerAddon):
    """USD Addon for AYON."""

    settings_model = USDSettings

    def initialize(self) -> None:
        """Initialize USD Addon."""

    async def get_default_settings(self) -> USDSettings:
        """Return default settings.

        Returns:
            USDSettings: Settings model with default values.

        """
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)

    async def convert_settings_overrides(
        self,
        source_version: str,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert settings overrides from older addon versions.

        Returns:
            dict[str, Any]: Converted overrides.

        """
        convert_settings_overrides(source_version, overrides)
        return await super().convert_settings_overrides(
            source_version, overrides
        )
