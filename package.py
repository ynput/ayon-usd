"""AYON USD Addon package file."""

name = "ayon_usd"
title = "Usd Addon"
version = "0.1.0-alpha-dev.1"
client_dir = "ayon_usd"

services = {}

plugin_for = ["ayon_server"]
build_command = ""

ayon_compatible_addons = {
    "deadline": ">=0.3.0",
}
