from typing import Any

_LEGACY_LAKEFS_KEYS = (
    "server_uri",
    "server_repo",
    "access_key_id",
    "secret_access_key",
    "asset_resolvers",
    "lake_fs_overrides",
)


def _convert_distribution_overrides(
    overrides: dict[str, Any],
) -> None:
    """Convert flat legacy `distribution` overrides to the nested schema."""
    distribution_overrides = overrides.get("distribution")
    if not isinstance(distribution_overrides, dict):
        return

    # If overrides are already in the new format -> skip conversion
    if any(key in distribution_overrides for key in ("type", "lake_fs", "local")):
        return

    lake_fs_overrides = {}
    for key in _LEGACY_LAKEFS_KEYS:
        value = distribution_overrides.pop(key, None)
        if value is not None:
            lake_fs_overrides[key] = value

    if not lake_fs_overrides:
        return

    distribution_overrides["type"] = "lake_fs"
    distribution_overrides["lake_fs"] = lake_fs_overrides


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_distribution_overrides(overrides)
    return overrides
