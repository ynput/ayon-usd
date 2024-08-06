# AYON USD Addon

This AYON Addon acts as an extension for the Contribution workflow utilizing the
[Open-USD](https://github.com/PixarAnimationStudios/OpenUSD) to allow for a more
automated workflow across Applications, Systems and Teams.

## Introduction

USD is a modern, open-source, scene description and file format developed by
Pixar Animation Studios. Its an Extensive and extendable C++Lib that is used in
3D, 2D and Games Graphics in order to allow for eficient work with Sceene data.

Manny might now it from SideFs Houdini Solaris or Nvidia Omniverse but it is by
now also included in most other typical Vfx software packages.

In AYON we use it in our New Contribution workflow as the data backed to allow
cross Platform and Application workflows. This allows for better integrated
Teams and a more artist centric Workflow as artists can open the same scene in
different applications and work with the tools that serve them the best.

Goal of this addon is to help distribute USD binaries:

- USD build for supported platforms.
- USD AR2 plugin for **some** supported DCCs.
- USD Tools (usdcat, usdedit, usdinfo, usdview, usdzip) coming with USD build.
- Standalone tools for AYON - USD interoperation.

## Getting Started

### Clone the Repo

> [!IMPORTANT]\
> This repository uses Git Submodules. Make sure to use the correct `git clone`\
> commands accordingly.\
> `git clone --recurse-submodules https://github.com/ynput/ayon-usd.git`\
> `git submodule update --init --recursive`

### Installation

1. Clone the repository to your local machine.
2. Run `.\tools\manage.ps1 create-env` on Windows or
   `./tools/manage.sh create-env` on Linux.
3. Run `.\tools\manage.ps1 build` on Windows or `./tools/manage.sh build` on
   Linux.
4. In AYON, go to `Studio Settings` -> `Bundles` -> `Install Addons...` and
   select the `./package/ayon_usd-x.x.x.zip` file.
5. Upload the Addon and let the server restart after installation is done.
6. Use new addon in your bundles.

## Admin Docs

### Configuration

there is a list of things that you can configure in the server settings to
achieve the optimal setup for your studio. In most cases you will probably not
need to touch them tho.

`ayon+settings://ayon_usd/asset_resolvers` is the key for the settings.

> [NOTE]\
> this addon is currently in its Alpha stage and you will need to set some
> LakeFs keys (LakeFs is the data server we use to distribute Bin data) you can
> get those Keys on our Discord server just ask one of the Ynput staff for them.
> the settings are the following:
> `ayon+settings://ayon_usd/LakeFs_Settings/access_key_id` and
> `ayon+settings://ayon_usd/LakeFs_Settings/secret_access_key`
