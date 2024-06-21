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


def logger_logging_keys_enum():
    """Return enumerator for supported platforms."""
    return [
        {"label": "Off", "value": ""},
        {"label": "Api Debug", "value": "AyonApi/"},
        {"label": "Env Debug", "value": "AyonApiDebugEnvVars/"},
        {"label": "All", "value": "AyonApi/AyonApiDebugEnvVars/"},
    ]


def log_lvl_enum():
    """Return enumerator for supported log lvls."""
    return [
        {"label": "Info", "value": "INFO"},
        {"label": "Error", "value": "ERROR"},
        {"label": "Warn", "value": "WARN"},
        {"label": "Critical", "value": "CRITICAL"},
        {"label": "Off", "value": "OFF"},
    ]


def file_logger_enum():
    """Return enumerator for supported log lvls."""
    return [
        {"label": "Off", "value": "OFF"},
        {"label": "On", "value": "ON"},
    ]


class AppPlatformPathModel(BaseSettingsModel):
    """Application platform URI model."""

    _layout = "compact"
    app_name: str = Field(
        title="App Name", description="Application name, e.g. maya/2025"
    )
    # TODO: we need to take into account different linux flavors
    platform: str = Field(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    lake_fs_path: str = Field(
        title="LakeFs Object Path",
        description="The LakeFs internal path to the resolver zip, e.g: `AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip`\n"
                    "This information can be found on LakeFs server Object Information.",
    )


class AppPlatformURIModel(BaseSettingsModel):
    """Application platform URI model."""

    _layout = "compact"
    app_name: str = Field(
        title="App Name", description="Application name, e.g. maya/2025"
    )
    # TODO: we need to take into account different linux flavors
    platform: str = Field(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    uri: str = Field(
        title="LakeFs Object Uri",
        description="Path to USD Asset Resolver plugin zip file on the LakeFs server, e.g: `lakefs://ayon-usd/V001/AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip`",
    )


class USDSettings(BaseSettingsModel):
    """USD settings."""

    ayon_usd_lake_fs_server_uri: str = Field(
        "http://192.168.178.42:58000",
        title="LakeFs Server Uri",
        description="The url to your LakeFs server.",
    )
    ayon_usd_lake_fs_server_repo: str = Field(
        "lakefs://ayon-usd/main/",
        title="LakeFs Repository Uri",
        description="The url to your LakeFs Repository Path",
    )
    access_key_id: str = Field(
        "AKIAIOSFOLKFSSAMPLES",
        title="Access Key Id",
        description="LakeFs Access Key Id",
    )
    secret_access_key: str = Field(
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        title="Access Key",
        description="LakeFs Access Key",
    )
    ayon_log_lvl: str = Field(
        "WARN",
        title="AyonResolver Log Lvl",
        enum_resolver=log_lvl_enum,
        description="Allows you to set the Verbosity of the AyonUsdResolver logger",
    )
    ayon_file_logger_enabled: str = Field(
        "OFF",
        title="AyonResolver File Logger Enabled",
        enum_resolver=file_logger_enum,
        description="Allows you to enable or disable the AyonUsdResolver file logger",
    )
    ayon_logger_logging_keys: str = Field(
        "",
        title="AyonCppApi Logging Keys",
        enum_resolver=logger_logging_keys_enum,
        description="List of extra logging options for the AyonCppApi",
    )
    file_logger_file_path: str = Field(
        "",
        title="AyonResolver File logger file path",
        description="Allows you to set a custom location where the file logger will export to. This can be a relative or absolute path. This is only used if `ayon_file_logger_enabled` is enabled.",
    )
    usd_tf_debug: str = Field(
        "",
        title="Tf Debug Variable for Debugging Usd",
        description="",
    )
    asset_resolvers: list[AppPlatformPathModel] = Field(
        title="Resolver Application LakeFs Paths",
        description="Allows an admin to define a specific Resolver Zip for a specific Application",
        default=[
            AppPlatformPathModel(
                app_name="maya/2024",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Maya/ayon-usd-resolver_maya2024.2_linux_py310.zip",
            ),
            AppPlatformPathModel(
                app_name="maya/2024",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Maya/ayon-usd-resolver_maya2024.2_win64_py310.zip",
            ),
            AppPlatformPathModel(
                app_name="maya/2025",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Maya/ayon-usd-resolver_maya2025_linux_py311.zip",
            ),
            AppPlatformPathModel(
                app_name="maya/2025",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Maya/ayon-usd-resolver_maya2025_win64_py310.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/19-5Py37",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/19-5",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py39.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/19-5Py37",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_win64_py37.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/19-5",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_win64_py39.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/20-0",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou20_linux_py310.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/20-0Py39",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou20_linux_py39.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/20-0",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou20_win64_py310.zip",
            ),
            AppPlatformPathModel(
                app_name="houdini/20-0Py39",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Hou/ayon-usd-resolver_hou20_win64_py39.zip",
            ),
            AppPlatformPathModel(
                app_name="unreal/5-4",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/Unreal/ayon-usd-resolver_unreal5.4_linux_py311.zip",
            ),
            AppPlatformPathModel(
                app_name="unreal/5-4",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/Unreal/ayon-usd-resolver_unreal5.4_win64_py311.zip",
            ),
            AppPlatformPathModel(
                app_name="ayon_usd/23-5",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/AyonUsd/ayon-usd-resolver_usd23.5_linux_py39.zip",
            ),
            AppPlatformPathModel(
                app_name="ayon_usd/23-5",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/AyonUsd/ayon-usd-resolver_usd23.5_win64_py39.zip",
            ),
        ],
    )
    lake_fs_overrides: list[AppPlatformURIModel] = Field(
        title="Resolver Application overrides",
        description="Allows an admin to define a specific Resolver Zip override for a specific Application",
        default=[],
    )
