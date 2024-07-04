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


# FIX this is an option for a selector enum
# def platform_enum():
#     """Return enumerator for supported platforms."""
#     return [
#         {"label": "Windows 7", "value": "windows7/windows"},
#         {"label": "Windows 8", "value": "windows8/windows"},
#         {"label": "Windows 10", "value": "windows10/windows"},
#         {"label": "Windows 11", "value": "windows11/windows"},
#         {"label": "Windows Server 2019", "value": "win_server_2019/windows_server"},
#         {"label": "Windows Server 2022", "value": "win_server_2022/windows_server"},
#         {"label": "Ubuntu 20.04 LTS", "value": "ubuntu2004/linux"},
#         {"label": "Ubuntu 22.04 LTS", "value": "ubuntu2204/linux"},
#         {"label": "CentOS 7", "value": "centos7/linux"},
#         {"label": "CentOS 8", "value": "centos8/linux"},
#         {"label": "CentOS Stream 8", "value": "centos_stream8/linux"},
#         {"label": "Red Hat Enterprise Linux 8", "value": "rhel8/linux"},
#         {"label": "Red Hat Enterprise Linux 9", "value": "rhel9/linux"},
#         {"label": "Debian 10", "value": "debian10/linux"},
#         {"label": "Debian 11", "value": "debian11/linux"},
#         {"label": "Fedora 33", "value": "fedora33/linux"},
#         {"label": "Fedora 34", "value": "fedora34/linux"},
#         {"label": "openSUSE Leap 15.2", "value": "opensuse_leap_152/linux"},
#         {"label": "openSUSE Leap 15.3", "value": "opensuse_leap_153/linux"},
#         {"label": "Arch Linux", "value": "arch_linux/linux"},
#         {"label": "Linux Mint 20", "value": "linux_mint20/linux"},
#         {"label": "Slackware 14.2", "value": "slackware142/linux"},
#         {"label": "Elementary OS 6", "value": "elementary_os6/linux"},
#         {"label": "Kali Linux 2021.4", "value": "kali_linux_20214/linux"},
#         {"label": "Gentoo", "value": "gentoo/linux"},
#         {"label": "Manjaro 21.2", "value": "manjaro212/linux"},
#         {"label": "FreeBSD 12.2", "value": "freebsd122/freebsd"},
#         {"label": "OpenBSD 6.9", "value": "openbsd69/openbsd"},
#         {"label": "NetBSD 9.2", "value": "netbsd92/netbsd"},
#         {"label": "Solaris 11.4", "value": "solaris114/solaris"},
#         {
#             "label": "OpenIndiana Hipster 2021.10",
#             "value": "openindiana_hipster_202110/solaris",
#         },
#         {"label": "AIX 7.2", "value": "aix72/aix"},
#         {"label": "macOS Monterey", "value": "macos_monterey/darwin"},
#         {"label": "macOS Big Sur", "value": "macos_big_sur/darwin"},
#         {"label": "macOS Catalina", "value": "macos_catalina/darwin"},
#         {"label": "macOS Mojave", "value": "macos_mojave/darwin"},
#         {"label": "VMware ESXi 7.0", "value": "vmware_esxi70/hypervisor"},
#         {
#             "label": "Microsoft Hyper-V Server 2019",
#             "value": "hyperv_server_2019/hypervisor",
#         },
#         {"label": "Citrix XenServer 8.2", "value": "xenserver82/hypervisor"},
#         {"label": "Proxmox VE 7.1", "value": "proxmox_ve71/hypervisor"},
#         {"label": "Oracle VM Server 3.4", "value": "oracle_vm_server34/hypervisor"},
#         {"label": "CoreOS", "value": "coreos/linux"},
#         {"label": "Ubuntu Server 20.04 LTS", "value": "ubuntu_server_2004/linux"},
#         {"label": "Ubuntu Server 22.04 LTS", "value": "ubuntu_server_2204/linux"},
#         {"label": "CentOS Stream 8", "value": "centos_stream8/linux"},
#         {"label": "Red Hat Enterprise Linux Server 8", "value": "rhel_server8/linux"},
#         {"label": "SUSE Linux Enterprise Server 15", "value": "sles15/linux"},
#         {"label": "Rocky Linux 8", "value": "rocky_linux8/linux"},
#         {"label": "AlmaLinux 8", "value": "almalinux8/linux"},
#     ]


# FIX find a way to pull this info from AyonCppApi (Later AyonLogger)
def logger_logging_keys_enum():
    """Return enumerator for supported platforms."""
    return [
        {"label": "Off", "value": ""},
        {"label": "Api Debug", "value": "AyonApi/"},
        {"label": "Env Debug", "value": "AyonApiDebugEnvVars/"},
        {"label": "All", "value": "AyonApi/AyonApiDebugEnvVars/"},
    ]


# FIX find a way to pull this from AyonCppApi (later AyonLogger)
def log_lvl_enum():
    """Return enumerator for supported log lvls."""
    return [
        {"label": "Info", "value": "INFO"},
        {"label": "Error", "value": "ERROR"},
        {"label": "Warn", "value": "WARN"},
        {"label": "Critical", "value": "CRITICAL"},
        {"label": "Off", "value": "OFF"},
    ]


# FIX find a way to pull this from AyonCppApi (later AyonLogger)
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
    # TODO: we need to take into account here different linux flavors
    platform: str = Field(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    lake_fs_path: str = Field(
        title="LakeFs object Path",
        description="the LakeFs internal path to the resolver zip (can be found in Object Information's) e.g: 	AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip",
    )


class AppPlatformURIModel(BaseSettingsModel):
    """Application platform URI model."""

    _layout = "compact"
    app_name: str = Field(
        title="App Name", description="Application name, e.g. maya/2025"
    )
    # TODO: we need to take into account here different linux flavors
    platform: str = Field(
        title="Platform",
        enum_resolver=platform_enum,
        description="windows / linux / darwin",
    )
    uri: str = Field(
        title="LakeFs object Uri",
        description="Path to USD Asset Resolver plugin zip file on the lakeFs server e.g: lakefs://ayon-usd/V001/AyonUsdResolverBin/Hou/ayon-usd-resolver_hou19.5_linux_py37.zip",
    )


class LakeFsSettings(BaseSettingsModel):
    """LakeFs Settings / Download Settings ?"""

    _layout = "collapsed"

    ayon_usd_lake_fs_server_uri: str = Field(
        "http://192.168.178.42:58000",
        title="LakeFs Server Uri",
        description="The url to your LakeFs server.",
    )
    ayon_usd_lake_fs_server_repo: str = Field(
        "lakefs://ayon-usd/main/",
        title="LakeFs repo Uri",
        description="LakeFs Rpo Path",
    )
    access_key_id: str = Field(
        "AKIAIOSFOLKFSSAMPLES",
        title="Acess Key Id",
        description="LakeFs Acsess Key Id",
    )
    secret_access_key: str = Field(
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        title="Aycess Key",
        description="LakeFs Access Key",
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
    lake_fs_overwrites: list[AppPlatformURIModel] = Field(
        title="Resolver Application overwrites",
        description="Allows an admin to define a specific Resolver Zip for a specific Application",
        default=[],
    )


class AyonResolverSettings(BaseSettingsModel):
    """LakeFs Settings / Download Settings ?"""

    _layout = "collapsed"

    ayon_log_lvl: str = Field(
        "WARN",
        title="AyonResolver Log Lvl",
        enum_resolver=log_lvl_enum,
        description="Allows you to set the Verbosity off the Logger in the AyonUsdResolver default is Warn",
    )
    ayon_file_logger_enabled: str = Field(
        "OFF",
        title="AyonResolver File Logger Enabled ",
        enum_resolver=file_logger_enum,
        description="Allows you to enable or disalbe the AyonUsdResolver file logger, default is Off",
    )
    ayon_loggin_loggin_keys: str = Field(
        "",
        title="AyonCppApi Logging Keys",
        enum_resolver=logger_logging_keys_enum,
        description="a list off extra logging options for the AyonCppApi",
    )
    file_logger_file_path: str = Field(
        "",
        title="AyonResolver File logger file path",
        description="Allows you to set a custom location where the file logger will export to. can be relative and abselute path, default empty",
    )


class UsdSettings(BaseSettingsModel):
    """LakeFs Settings / Download Settings ?"""

    _layout = "collapsed"
    usd_tf_debug: str = Field(
        "",
        title="Tf Debug Varialbe for Debbuging Usd",
        description="",
    )


class USDSettings(BaseSettingsModel):
    """USD settings."""

    LakeFs_Settings: LakeFsSettings = Field(default_factory=LakeFsSettings)

    Ayon_UsdResolver_Settings: AyonResolverSettings = Field(
        default_factory=AyonResolverSettings
    )

    Usd_Settings: UsdSettings = Field(default_factory=UsdSettings)
