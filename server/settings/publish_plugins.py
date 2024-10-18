from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
)


class EnabledBaseModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = SettingsField(True)
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


class PublishPluginsModel(BaseSettingsModel):
    USDOutputProcessorRemapToRelativePaths: EnabledBaseModel = SettingsField(
        default_factory=EnabledBaseModel,
        title="Process USD files to use relative paths",
        description=(
            "When enabled, published USD layers will anchor the asset paths to"
            " the published filepath. "
        )
    )


DEFAULT_PUBLISH_VALUES = {
    "USDOutputProcessorRemapToRelativePaths": {
        "enabled": False,
        "optional": False,
        "active": True,
    },
}
