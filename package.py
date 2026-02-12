"""AYON USD Addon package file."""

name = "usd"
title = "USD"
version = "0.1.4+dev"
client_dir = "ayon_usd"

services = {}

plugin_for = ["ayon_server"]
build_command = ""

ayon_required_addons = {
    "core": ">=1.5.3",
}
ayon_compatible_addons = {
    "deadline": ">=0.3.0",
}
