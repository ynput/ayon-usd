"""Main settings for USD on AYON server."""

from ayon_server.settings import BaseSettingsModel, SettingsField

from .publish_plugins import PublishPluginsModel, DEFAULT_PUBLISH_VALUES

def platform_enum():
    """Return enumerator for supported platforms."""
    return [
        {"label": "Windows", "value": "windows"},
        {"label": "Linux", "value": "linux"},
        {"label": "MacOS", "value": "darwin"},
    ]


def logger_logging_keys_enum():
    """Return enumerator for AyonCpp Logging Keys."""
    return [
        {"label": "Off", "value": ""},
        {"label": "Api Debug", "value": "AyonApi/"},
        {"label": "Env Debug", "value": "AyonApiDebugEnvVars/"},
        {"label": "All", "value": "AyonApi/AyonApiDebugEnvVars/"},
    ]


# TODO: find a way to pull this from AyonCppApi (later AyonLogger)
def log_lvl_enum():
    """Return enumerator for supported log levels."""
    return [
        {"label": "Info", "value": "INFO"},
        {"label": "Error", "value": "ERROR"},
        {"label": "Warn", "value": "WARN"},
        {"label": "Critical", "value": "CRITICAL"},
        {"label": "Off", "value": "OFF"},
    ]


# TODO: find a way to pull this from AyonCppApi (later AyonLogger)
def file_logger_enum():
    """Return enumerator to enable or disable the file logger."""
    return [
        {"label": "Off", "value": "OFF"},
        {"label": "On", "value": "ON"},
    ]


class AppPlatformPathModel(BaseSettingsModel):

    _layout = "collapsed"
    name: str = SettingsField(
        title="App Name", description="Application name, e.g. maya/2025"
    )

    app_alias_list: list[str] = SettingsField(
        title="Application Alias",
        description="Define a list of App Names that use the same "
        "resolver as the parent application",
        default_factory=list,
    )

    # TODO: we need to take into account here different linux flavors
    platform: str = SettingsField(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    lake_fs_path: str = SettingsField(
        title="Repository Object Path",
        description=(
            "The LakeFs internal path to the resolver zip, e.g: "
            "`AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip`"
            "\n"
            "This information can be found on LakeFs server Object "
            "Information."
        ),
    )


class AppPlatformURIModel(BaseSettingsModel):
    """Application platform URI model."""

    _layout = "expanded"
    app_name: str = SettingsField(
        title="App Name", description="Application name, e.g. maya/2025"
    )
    # TODO: we need to take into account here different linux flavors
    platform: str = SettingsField(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    uri: str = SettingsField(
        title="Repository Object URI",
        description=(
            "Path to USD Asset Resolver plugin zip file on the LakeFs server, "
            "e.g: `lakefs://ayon-usd/V001/AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip`"  # noqa
        ),
    )


class BinaryDistributionSettings(BaseSettingsModel):
    """Binary distribution of USD and AYON USD Resolver"""

    _layout = "collapsed"

    enabled: bool = SettingsField(False)

    server_uri: str = SettingsField(
        "https://lake.ayon.cloud",
        title="Server Uri",
        description="The url to your LakeFs server.",
    )
    server_repo: str = SettingsField(
        "lakefs://ayon-usd/v0.2.0/",
        title="Repository Uri",
        description="The url to your LakeFs Repository Path",
    )
    access_key_id: str = SettingsField(
        "{AYON_Distribution_Key_Id}",
        title="Access Key Id",
        description="LakeFs Access Key Id",
    )
    secret_access_key: str = SettingsField(
        "{AYON_Distribution_Access_Key}",
        title="Access Key",
        description="LakeFs Access Key",
    )
    asset_resolvers: list[AppPlatformPathModel] = SettingsField(
        title="Resolver Application Paths",
        description="Allows an admin to define a specific Resolver Zip for a specific Application",
        default=[
            AppPlatformPathModel(
                name="maya/2024",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/MayaLinux/Maya2024_2_Py310_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="maya/2024",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/MayaWin/Maya2024_2_Py310_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="maya/2025",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/MayaLinux/Maya2025_Py311_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="maya/2025",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/MayaWin/Maya2025_Py311_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/19-5Py37",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini195_Py37_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/19-5",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini195_Py39_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/19-5Py37",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini195_Py37_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/19-5",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini195_Py39_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-0",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini20_Py310_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-0Py39",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini20_Py39_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-0",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini20_Py310_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-0Py39",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini20_Py39_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-5",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini205_Py311_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-5Py310",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/HouLinux/Houdini205_Py310_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-5",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini205_Py311_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="houdini/20-5Py310",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/HouWin/Houdini205_Py310_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="unreal/5-4",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/UnrealLinux/Unreal5_4_Py39_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="unreal/5-4",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/UnrealWin/Unreal5_4_Py39_Win_Windows_AMD64.zip",
            ),
            AppPlatformPathModel(
                name="ayon_usd/23-5",
                platform="linux",
                lake_fs_path="AyonUsdResolverBin/AyonUsdLinux/AyonUsd23_5_Py39_Linux_Linux_x86_64.zip",
            ),
            AppPlatformPathModel(
                name="ayon_usd/23-5",
                platform="windows",
                lake_fs_path="AyonUsdResolverBin/AyonUsdWin/AyonUsd23_5_Py39_Win_Windows_AMD64.zip",
            ),
        ],
    )
    lake_fs_overrides: list[AppPlatformURIModel] = SettingsField(
        title="Resolver Application Overrides",
        description=(
            "Allows to define a specific Resolver Zip for a specific Application"
        ),
        default_factory=list,
    )


class AyonResolverSettings(BaseSettingsModel):
    """AYON USD resolver Settings"""

    _layout = "collapsed"

    ayon_log_lvl: str = SettingsField(
        "WARN",
        title="Resolver Log Level",
        enum_resolver=log_lvl_enum,
        description="Set verbosity of the AyonUsdResolver logger",
    )
    ayon_file_logger_enabled: str = SettingsField(
        "OFF",
        title="Resolver File Logger Enabled ",
        enum_resolver=file_logger_enum,
        description="Enable or disable AyonUsdResolver file logger",
    )
    file_logger_file_path: str = SettingsField(
        "",
        title="Resolver File logger file path",
        description=(
            "Allows you to set a custom location where the file logger will "
            "export to. This can be a relative or absolute path. This is only "
            "used if `ayon_file_logger_enabled` is enabled."
        ),
    )
    ayon_logger_logging_keys: str = SettingsField(
        "",
        title="AyonCppApi Logging Keys",
        enum_resolver=logger_logging_keys_enum,
        description="List of extra logging options for the AyonCppApi",
    )


class UsdLibConfigSettings(BaseSettingsModel):
    """Settings for USD"""

    _layout = "collapsed"
    usd_tf_debug: str = SettingsField(
        "",
        title="Tf Debug Variable for Debugging USD",
        description="",
    )


class USDSettings(BaseSettingsModel):

    distribution: BinaryDistributionSettings = SettingsField(
        default_factory=BinaryDistributionSettings, title="Binary Distribution"
    )

    ayon_usd_resolver: AyonResolverSettings = SettingsField(
        default_factory=AyonResolverSettings, title="AYON USD Resolver Config"
    )

    usd: UsdLibConfigSettings = SettingsField(
        default_factory=UsdLibConfigSettings, title="USD Library Config")

    publish: PublishPluginsModel = SettingsField(
        title="Publish plugins",
        default=DEFAULT_PUBLISH_VALUES
    )