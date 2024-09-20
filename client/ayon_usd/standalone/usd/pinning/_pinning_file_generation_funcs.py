import logging
import json
import os
import sys
import re
from typing import Dict, List, Optional, Set
from pxr import UsdShade, Ar, Sdf
from urllib.parse import urlparse

log = logging.getLogger(__name__)


def _normalize_path(path):
    # On windows force drive letter to lowercase
    if sys.platform.startswith('win'):
        drive, tail = os.path.splitdrive(path)
        drive = drive.lower()
        path = f"{drive}{tail}"
    
    return os.path.normpath(path)


def is_uri(path: str) -> bool:
    parsed = urlparse(path)
    return bool(parsed.scheme)


def remove_root_from_dependency_info(
    dependency_info: Dict[str, str], root_info: Dict[str, str]
) -> Dict[str, str]:
    """Removes the Ayon Machine Root from a given Dependency info Dict

    Args:
        dependency_info: Dict generated by `get_asset_dependencies()`
        root_info: A flat dict containing root identifier mapping to the
        associated root path /path/to/root. This can be obtained from Ayon
        server `Get Project Roots Overrides`

    Returns:
         a dependency_info dict that holds key: Usd assetIdentifiers val:
         rootless paths as they would be returned from Ayon server `/resolve`
         endpoint ('Resolve Uris' in the server Docs).
    """

    if not root_info or not dependency_info:
        raise ValueError(
            f"both root_info and dependency_info need to be present "
            f"and an instance of Dict (root_info: {root_info}, "
            f"dependency_info: {dependency_info})"
        )

    replacements = {path: replacer for replacer, path in root_info.items()}

    pattern = "|".join(f"({pat})" for pat in replacements)
    regx = re.compile(pattern)

    # TODO test if there are cases where we have more than one match.group
    def _replace_match(match: re.Match):
        match_grp_zero = match.group(0)
        match_replacment = replacements.get(re.escape(match_grp_zero))
        if not match_replacment:
            return match_grp_zero

        replacment = "{root[" + match_replacment + "]}"
        return replacment

    rootless_dependency_info = {}
    for key, path in dependency_info.items():
        new_path = regx.sub(_replace_match, path)
        new_key = regx.sub(_replace_match, key)

        rootless_dependency_info[new_key] = new_path

    return rootless_dependency_info


def _get_prim_spec_asset_property_values(
        prim: Sdf.PrimSpec, layer: Sdf.Layer) -> List[str]:
    """Get all `Sdf.AttributeSpec` values for asset type properties.

    This includes time sample data from a given `Sdf.PrimSpec`.

    Args:
        prim (Sdf.PrimSpec): The prim spec to get asset property values from.
        layer (Sdf.Layer): Parent layer of the Sdf.PrimSpec instance

    Returns: flat list of AttributeSpec values

    """
    prop_data = []
    for prop in prim.properties:
        if not isinstance(prop, Sdf.AttributeSpec):
            continue

        if prop.typeName != Sdf.ValueTypeNames.Asset:
            continue

        default_val = prop.default
        if default_val:
            if hasattr(default_val, "__iter__"):
                prop_data.extend(default_val)
            else:
                prop_data.append(default_val.path)
        else:
            time_samples = layer.ListTimeSamplesForPath(prop.path)
            for time in time_samples:
                value = layer.QueryTimeSample(prop.path, time)
                if value:
                    if hasattr(value, "__iter__"):
                        prop_data.extend(value)
                    else:
                        prop_data.append(value.path)

    return prop_data


def _get_prim_spec_hierarchy_external_refs(
    prim: Sdf.PrimSpec, layer: Sdf.Layer
) -> List[str]:
    file_list: List[str] = _get_prim_spec_asset_property_values(prim, layer)

    for child_prim in prim.nameChildren:
        file_list.extend(_get_prim_spec_hierarchy_external_refs(child_prim, layer))
    return file_list


def _remove_sdf_args(ref: str) -> str:
    uri = re.sub(re.compile(r":SDF_FORMAT_ARGS.*$"), "", ref)
    return uri


def _resolve_udim(udim_identifier: str, layer: Sdf.Layer) -> Dict[str, str]:
    udim_data = {}
    resolved_udims = UsdShade.UdimUtils.ResolveUdimTilePaths(
        str(udim_identifier), layer
    )
    for path, tile in resolved_udims:
        udim_replaced_identifier = udim_identifier.replace(
            "<UDIM>",
            tile,
        )
        udim_data[layer.ComputeAbsolutePath(udim_replaced_identifier)] = path
    
    return udim_data


# TODO refactor so that this function has a gather block and a write block
#  currently all individual blocks write to the identifier_to_path_dict and
#  that makes sanitizing the data hard
def get_asset_dependencies(
    layer_path: str,
    resolver: Ar.Resolver,
    processed_layers: Optional[Set[str]] = None
) -> Dict[str, str]:
    """Return mapping from all used asset identifiers to the resolved filepaths.

    Recursively traverse `Sdf.Layer` and get all their asset dependencies.
    For each asset identifier map it to its resolved filepath.

    Args:
        layer_path: Usd layer path to be taken as the root layer

    Returns: Mapping from asset identifier to their resolved paths

    """
    layer_path = _remove_sdf_args(layer_path)
    if not layer_path:
        return {}
    if isinstance(layer_path, Ar.ResolvedPath):
        layer_path = layer_path.GetPathString()

    identifier_to_path: Dict[str, str] = {}

    resolved_layer_path: Ar.ResolvedPath = resolver.Resolve(layer_path)

    if not processed_layers:
        processed_layers = {resolved_layer_path.GetPathString()}

    elif resolved_layer_path.GetPathString() in processed_layers:
        return {}

    else:
        processed_layers.add(resolved_layer_path.GetPathString())

    layer: Sdf.Layer = Sdf.Layer.FindOrOpen(resolved_layer_path)
    if not layer:
        log.warning(f"Unable to open layer: {resolved_layer_path}")
        return {}

    identifier_to_path[layer_path] = resolved_layer_path.GetPathString()
    prim_spec_file_paths: List[str] = _get_prim_spec_hierarchy_external_refs(
        layer.pseudoRoot, layer
    )
    for identifier in prim_spec_file_paths:
        identifier = _remove_sdf_args(identifier)
        resolved_path = resolver.Resolve(layer.ComputeAbsolutePath(identifier))
        resolved_path_str = resolved_path.GetPathString()
        identifier_to_path[layer.ComputeAbsolutePath(identifier)] = resolved_path_str

        if "<UDIM>" in resolved_path_str:
            # Include all tiles/paths of the UDIM
            udim_data = _resolve_udim(identifier, layer)
            identifier_to_path.update(udim_data)

    asset_identifier_list: List[str] = layer.GetCompositionAssetDependencies()

    for ref in asset_identifier_list:
        resolved_path = resolver.Resolve(layer.ComputeAbsolutePath(ref))
        ref = _remove_sdf_args(ref)
        resolved_path_str = resolved_path.GetPathString()
        if is_uri(ref):
            search_path_string = ref
        else:
            search_path_string = resolved_path_str

        identifier_to_path[search_path_string] = resolved_path_str

        recursive_result = get_asset_dependencies(
            search_path_string,
            resolver,
            processed_layers,
        )
        identifier_to_path.update(recursive_result)
   
    return identifier_to_path


# This function would work but in some UsdLib versions it will output <UDIM>
# tag and in some versions it will resolve to 1001-1100. This function also
# does not handle UDIM resolution at the moment
# def get_asset_dependencies(
#     layer_path: str, asset_identifier: str, print_debug: bool = False
# ) -> Dict[str, str]:
#     """will return a Dict[str, str] that holds the asset_identifier and the resolved path for a given usd file
#     the file needs to be an existing real path
#
#     Args:
#         layer_path: path to the resource
#         asset_identifier: usd internal identifier for the resource
#
#     Returns: a flat dict containing all the asset_identifiers and resolved paths that are needed to construct the Usd-Stage
#
#     """
#     if print_debug:
#         print(f"UsdFile: {layer_path} ")
#     if not layer_path:
#         return {}
#     ref_list = {}
#
#     if isinstance(layer_path, Ar.ResolvedPath):
#         layer_path = layer_path.GetPathString()
#
#     ref_list[asset_identifier] = layer_path
#     if not layer_path.endswith((".usd", ".usda", ".usdc")):
#         return ref_list
#     asset_paths = UsdUtils.ExtractExternalReferences(layer_path)
#     flattened_reference_list = [item for sublist in asset_paths for item in sublist]
#     if not flattened_reference_list:
#         return ref_list
#
#     for ref in flattened_reference_list:
#
#         if os.path.isabs(ref) or is_uri(ref):
#             resolved_path = resolver.Resolve(ref)
#         else:
#             parent_file_dir_name = os.path.dirname(layer_path)
#             abs_path = os.path.normpath(os.path.join(parent_file_dir_name, ref))
#             resolved_path = resolver.Resolve(abs_path)
#
#         if isinstance(resolved_path, Ar.ResolvedPath):
#             resolved_path = resolved_path.GetPathString()
#
#         ref_list.update(get_asset_dependencies(resolved_path, ref))
#     return ref_list


def _write_pinning_file(
    output_path: str,
    pinning_data: Dict[str, str],
    create_missing_dirs: bool = True,
    overwrite_ok: bool = True,
):
    """writes out a pinning file to disk in the appropriate format

    Args:
        output_path (str): Path where the pinning file should be written to
        pinning_data (str): The pinning dict that holds all the pinning data
        create_missing_dirs (bool): Whether to ensure folders to output path
            exist before writing the file.
        overwrite_ok (bool): Whether to overwrite the pinning file if it
            already exists.

    Raises:
        TypeError: raised if pinning_data is not a dict
            or output_path is not a JSON
        FileExistsError: raised if output_path exists and overwrite_ok is False
    """

    # data validation
    if not isinstance(pinning_data, dict):
        raise TypeError("pinning data is not a dict")

    if not output_path.endswith(".json"):
        raise TypeError("output_path is not a json")

    # file creation
    if os.path.exists(output_path) and not overwrite_ok:
        raise FileExistsError(
            f"Destination filepath already exists: {output_path}")

    if create_missing_dirs:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as pinning_file:

        write_data = {"ayon_resolver_pinning_data": pinning_data}
        json.dump(write_data, pinning_file, indent=2)


def generate_pinning_file(
    entry_usd: str, root_info: Dict[str, str], pinning_file_path: str
):
    """Generate a AYON USD Resolver pinning file.

    The pinning file can be used to pin paths in USD to specific filepaths,
    avoiding the need for dynamic resolving and runtime and allowing to pin
    dynamic URIs (like 'get me latest version') to be pinned to the version
    at the time of the generation.

    Arguments:
        entry_usd: The USD filepath to generate the pinning file for.
        root_info: The project roots for the site the pinning should resolve
          to. These can be obtained via e.g. the AYON REST API get
          `/api/projects/{project_name}/siteRoots".
        pinning_file_path: The destination path to write the pinning file to.

    """

    if not pinning_file_path.endswith(".json"):
        raise RuntimeError(
            f"Pinning file path is not a json file {pinning_file_path}")

    # Assume that the environment sets up the correct default AyonUsdResolver
    resolver = Ar.GetResolver()
    pinning_data = get_asset_dependencies(entry_usd, resolver)

    # on Windows, we need to make the drive letter lower case.
    if sys.platform.startswith('win'):
        pinning_data = {
            _normalize_path(key): _normalize_path(val)
            for key, val in pinning_data.items()
        }

    rootless_pinning_data = remove_root_from_dependency_info(
        pinning_data, root_info
    )

    rootless_pinning_data["ayon_pinning_data_entry_scene"] = _remove_sdf_args(
        entry_usd
    )

    _write_pinning_file(
        pinning_file_path,
        rootless_pinning_data,
    )
