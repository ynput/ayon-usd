# AYON USD Addon

This AYON Addon acts as an extension for the **AYON Contribution workflow**
utilizing the
[Open-USD Framework](https://github.com/PixarAnimationStudios/OpenUSD) to allow
for a more automated workflow across Applications, Systems and Teams.

You can find Admin and Developer docs under Docs/Ayon_Docs/

## Getting Started

### Clone the Repo

> **_IMPORTANT_**\
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
