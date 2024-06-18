"""USD Addon for AYON - server part."""

import os
import json
from pathlib import Path

from fastapi import Depends  # noqa: F401

from ayon_server.addons import BaseServerAddon
from ayon_server.api.dependencies import dep_current_user
from ayon_server.entities import UserEntity
from ayon_server.exceptions import NotFoundException

from .settings import USDSettings

PRIVATE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "private"


class USDAddon(BaseServerAddon):
    """USD Addon for AYON."""

    settings_model = USDSettings

    def initialize(self):
        """Initialize USD Addon."""
        self.add_endpoint(
            "files_info",
            self._get_files_info,
            method="GET",
            name="files_info",
            description="Get information about binary files on server.",
        )

    async def _get_files_info(
        self, user: UserEntity = Depends(dep_current_user)
    ) -> list[dict[str, str]]:
        info_filepath = (PRIVATE_DIR / "files_info.json").resolve().as_posix()
        try:
            with open(info_filepath, "r") as stream:
                data = json.load(stream)
        except FileNotFoundError as e:
            raise NotFoundException("Files info not found") from e
        return data

    async def _get_lakefs_repo(self, user: UserEntity = Depends(dep_current_user)):
        # TODO this endpoint will return everything that the lake ctl needs:
        # infos for generating a config file
        # LakeFs server uri
        # LakeFs repo + path on the server (for lakectl fs ls -r: to find all the resolvers and usd bins)
        pass
