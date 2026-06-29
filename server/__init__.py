"""USD Addon for AYON - server part."""

import os
from pathlib import Path

from fastapi import Depends  # noqa: F401

from ayon_server.addons import BaseServerAddon


from .settings import USDSettings

PRIVATE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "private"


class USDAddon(BaseServerAddon):
    """USD Addon for AYON."""

    settings_model = USDSettings

    def initialize(self):
        """Initialize USD Addon."""
