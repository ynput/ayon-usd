import json
import os
import shutil
from typing import Dict
from pxr import UsdUtils, Ar
from urllib.parse import urlparse


def is_uri(path):
    parsed = urlparse(path)
    return parsed.scheme


# we do the assumption that the environment sets up the correct Default resolver (in AYON case this should be the AyonUsdResolver)
resolver = Ar.GetResolver()


# TODO layer_path is not a good name for the resolved identifier
# TODO write doc string
def get_asset_dependencies(layer_path: str, asset_identifier: str) -> Dict[str, str]:
    """will return a Dict[str, str] that holds the asset_identifier and the resolved path for a given usd file
    the file needs to be an existing real path

    Args:
        layer_path: path to the resource
        asset_identifier: usd internal identifier for the resource

    Returns:

    """
    print(f"UsdFile: {layer_path} ")
    if not layer_path:
        return {}
    ref_list = {}

    if isinstance(layer_path, Ar.ResolvedPath):
        layer_path = layer_path.GetPathString()

    ref_list[asset_identifier] = layer_path
    if not layer_path.endswith((".usd", ".usda", ".usdc")):
        return ref_list

    asset_paths = UsdUtils.ExtractExternalReferences(layer_path)
    flattened_reference_list = [item for sublist in asset_paths for item in sublist]

    if flattened_reference_list:
        for ref in flattened_reference_list:

            if os.path.isabs(ref) or is_uri(ref):
                resolved_path = resolver.Resolve(ref)
            else:
                parent_file_dir_name = os.path.dirname(layer_path)
                abs_path = os.path.normpath(os.path.join(parent_file_dir_name, ref))
                resolved_path = resolver.Resolve(abs_path)

            if isinstance(resolved_path, Ar.ResolvedPath):
                resolved_path = resolved_path.GetPathString()

            ref_list.update(get_asset_dependencies(resolved_path, ref))
    return ref_list


def write_pinning_file(
    output_path: str,
    pinning_data: dict,
    create_missing_dirs: bool = True,
    overwrite_ok: bool = True,
) -> bool:

    # data validatoin
    if not isinstance(pinning_data, dict):
        print(f"pinning data is not a dict")
        return False

    if not output_path.endswith(".json"):
        print(f"output_path is not a json")
        return False

    # file creatoin
    if os.path.exists(output_path) and not overwrite_ok:
        print(f"Output path does Exist {output_path}")
        return False

    if create_missing_dirs:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as pinning_file:
        wirte_data = {"ayon_resolver_pinning_data": pinning_data}
        json.dump(wirte_data, pinning_file, indent=4, separators=(",", ": "))
    return True
