from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
)

class EnabledOnlyModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)


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
    ExtractSkeletonPinningJSON: EnabledOnlyModel = SettingsField(
        default_factory=EnabledOnlyModel,
        title="Generate USD Resolver Pinning file on publish",
        description=(
            "When enabled, on publishing USD files a pinning file will be "
            "written along with the published file that pins all dynamic "
            "entity URIs to the paths in the pinning file. This should be "
            "disabled when not using the USD resolver."
        )
    )


DEFAULT_PUBLISH_VALUES = {
    "USDOutputProcessorRemapToRelativePaths": {
        "enabled": False,
        "optional": False,
        "active": True,
    },
    "ExtractSkeletonPinningJSON": {
        "enabled": True
    }
}
