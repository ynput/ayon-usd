from ayon_server.settings import BaseSettingsModel, MultiplatformPathListModel
from pydantic import Field, validator


class USDSettings(BaseSettingsModel):
    use_downloaded: bool = Field(
        default=True,
        title="Download USD from server",
        description="If disabled, one of custom options must be used",
    )
    custom_roots: MultiplatformPathListModel = Field(
        default_factory=MultiplatformPathListModel,
        title="Custom USD root",
        description="Root to directory where USD binaries can be found",
    )
