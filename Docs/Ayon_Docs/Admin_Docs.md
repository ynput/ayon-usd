## Introduction

> **_NOTE_**\
> this addon is currently in its Alpha stage and you will need to set some
> LakeFs keys (LakeFs is the data server we use to distribute Bin data) you can
> get those Keys on our Discord server just ask one of the Ynput staff for them.
> the settings are the following:
> `ayon+settings://ayon_usd/lakefs/access_key_id` and
> `ayon+settings://ayon_usd/lakefs/secret_access_key`

USD is a modern, open-source, scene description and file format developed by
Pixar Animation Studios. Its an Extensive and extendable C++Lib that is used in
3D, 2D and Games Graphics in order to allow for eficient work with Sceene data.

Many might know it from SideFs Houdini Solaris or Nvidia Omniverse but it is by
now included in most other Vfx software packages.

In AYON we use it in our New **Contribution workflow** as the data backend to
allow cross Platform and Application workflows. This allows for better
integrated Teams and a more artist centric Workflow as artists can open the same
scene in different applications and work with the tools that serve them the
best.

Goal of this addon is to extend the Contirbution workflow by automaticly
distributing Usd and Ayon Libs:

- USD-Lib build for supported platforms.
- USD AR2 [Asset Resolver](https://github.com/ynput/ayon-usd-resolver) plugin
  for
  [**some**](https://github.com/ynput/ayon-usd-resolver?tab=readme-ov-file#tested-platforms)
  supported DCCs.
- USD Tools (usdcat, usdedit, usdinfo, usdview, usdzip) coming with USD build.
- Standalone tools for AYON - Extending the capability and usability of the
  OpenUsdLib for artists and studios.

## Configuration

there is a list of things that you can configure in the server settings to
achieve the optimal setup for your studio. In most cases you will probably not
need to touch them tho.

#### LakeFs Config

**LakeFs Settings:** `ayon+settings://ayon_usd/lakefs`\
LakeFs is the backend of our bin distribution system the addon will use the
specified server to download the resolvers and AyonUsdLibs from LakeFs.

**LakeFs Server Uri:**
`ayon+settings://ayon_usd/lakefs/server_repo`\
this is the Uri used to host the LakeFs server. the Ynput server can be found at
`https://lake.ayon.cloud`

**LakeFs Repository Uri:**
`ayon+settings://ayon_usd/lakefs/server_repo`\
this is a LakeFs internal link that also specifies the branch your downloading
from.\
this can be great if you want to pin your pipeline to a specific release.

**Asset Resolvers:** `ayon+settings://ayon_usd/lakefs/asset_resolvers`\
allows you to associate a specific Application name with a specific resolver.\
we always setup all the resolvers we compile but if you have special App_Names
in your Applications then you might want to add an App Alias.\
e.g if you have hou19.5.xxx setup as an variant for Houdini you can then set it
as an alias for the Hou19.5 entry because they share the same resolver.

#### Usd Resolver Config

`ayon+settings://ayon_usd/ayon_usd_resolver`

**Log Lvl** `ayon+settings://ayon_usd/ayon_usd_resolver/ayon_log_lvl`
control the log lvl of the AyonUsdResolver. It is advised to have this at Warn
or Critical as Logging will impact the performance.

**File Logger Enabled**
`ayon+settings://ayon_usd/ayon_usd_resolver/ayon_file_logger_enabled`
AyonUsdResolver includes a file logger if needed.

**Logging Keys**
`ayon+settings://ayon_usd/ayon_usd_resolver/ayon_logger_logging_keys`
AyonUsdResolver Logger has a few predefined logging keys that can be enabled for
Debugging. it is advised to only do this with Developer bundles as it can expose
AYON Server data. it will also generate quite a big output.

**File Logger Path**
`ayon+settings://ayon_usd/ayon_usd_resolver/file_logger_file_path` The
Ayon File Logger needs an output path this needs to be a relative or absolute
path to a folder.

#### UsdLib Config:

`ayon+settings://ayon_usd/usd`

**Tf_Debug** `ayon+settings://ayon_usd/usd/usd_tf_debug`\
this allows you to set the UsdTfDebug env variable to get extra debug info from
the UsdLib.\
[Usd Survival Guide (Luca Sheller)](https://lucascheller.github.io/VFX-UsdSurvivalGuide/core/profiling/debug.html)\
[OpenUsd Debug Wiki](https://openusd.org/release/api/group__group__tf___debugging_output.html)
