"""Main settings for USD on AYON server."""
from ayon_server.settings import BaseSettingsModel, MultiplatformPathListModel
from pydantic import Field


def platform_enum():
    """Return enumerator for supported platforms."""
    return [
        {"label": "Windows", "value": "windows"},
        {"label": "Linux", "value": "linux"},
        {"label": "MacOS", "value": "darwin"},
    ]


class AppPlatformURIModel(BaseSettingsModel):
    """Application platform URI model."""

    _layout = "compact"
    app_name: str = Field(
        title="App Name",
        description="Application name, e.g. maya/2025")
    # TODO: we need to take into account here different linux flavors
    platform: str = Field(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin")
    uri: str = Field(
        title="URI",
        description="Path to USD Asset Resolver plugin zip file")


class USDSettings(BaseSettingsModel):
    """USD settings."""

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
    asset_resolvers: list[AppPlatformURIModel] = Field(
        title="Asset Resolvers",
        description="USD Asset Resolver settings",
        default=[
            AppPlatformURIModel(
                app_name="maya/2025",
                platform="windows",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_maya2025_win64_py310.zip"),
            AppPlatformURIModel(
                app_name="maya/2025",
                platform="linux",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_maya2025_linux_py311.zip"),
            AppPlatformURIModel(
                app_name="maya/2024",
                platform="windows",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_maya2024.2_win64_py310.zip"),
            AppPlatformURIModel(
                app_name="maya/2024",
                platform="linux",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_maya2024.2_linux_py310.zip"),
            AppPlatformURIModel(
                app_name="unreal/5-4",
                platform="windows",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_unreal5.4_win64_py311.zip"),
            AppPlatformURIModel(
                app_name="unreal/5-4",
                platform="linux",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_unreal5.4_linux_py311.zip"),
            AppPlatformURIModel(
                app_name="houdini/19-5",
                platform="windows",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_hou19.5_win64_py39.zip"),
            AppPlatformURIModel(
                app_name="houdini/19-5",
                platform="linux",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_hou19.5_linux_py39.zip"),
            AppPlatformURIModel(
                app_name="houdini/20",
                platform="windows",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_hou20_win64_py310.zip"),
            AppPlatformURIModel(
                app_name="houdini/20",
                platform="linux",
                uri="https://distribute.openpype.io/resolvers/ayon-usd-resolver_hou20_linux_py310.zip"),

        ],
    )
