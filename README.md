# AYON USD Addon

This is AYON Addon for support of [USD](https://github.com/PixarAnimationStudios/OpenUSD).

It helps to distribute USD binaries and related tools to artist workstations and
to configure its environment.

## Introduction

USD is a modern, open-source, scene description and file format developed by
Pixar Animation Studios. It is used for interchanging 3D graphics data between
applications and for rendering.

Goal of this addon is to help distribute USD binaries:

- USD build for supported platforms.
- USD AR2 plugin for __some__ supported DCCs.
- USD Tools (usdcat, usdedit, usdinfo, usdview, usdzip) coming with USD build.
- Standalone tools for AYON - USD interoperation.

## Getting Started

### Installation

1. Clone the repository to your local machine.
2. Run `.\tools\manage.ps1 create-env` on Windows or `./tools/manage.sh create-env` on Linux.
3. Run `.\tools\manage.ps1 build` on Windows or `./tools/manage.sh build` on Linux.
4. In AYON, go to `Studio Settings` -> `Bundles` -> `Install Addons...` and select the `./package/ayon_usd-x.x.x.zip` file.
5. Upload the Addon and let the server restart after installation is done.
6. Use new addon in your bundles.

### Configuration

In addon settings, you can configure mapping between USD Resolver plugin and you DCCs.
`App Name` is the name of the DCC application, like `maya/2025` corresponding
to the Application addon settings. Then there is a platform settings, where you
can specify the platform for which the USD Asset Resolver plugin is used.
Lastly, there is a URL to the USD Asset Resolver plugin zip matching the platform and
the DCC application.

`ayon+settings://ayon_usd/asset_resolvers` is the key for the settings.
