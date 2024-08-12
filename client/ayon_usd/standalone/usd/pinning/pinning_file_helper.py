import json
import os
import re
from typing import Dict, List
from pxr import UsdShade, Ar, Sdf
from urllib.parse import urlparse


def is_uri(path: str) -> bool:
    parsed = urlparse(path)
    return bool(parsed.scheme)


# Assume that the environment sets up the correct default AyonUsdResolver
resolver = Ar.GetResolver()


def remove_root_from_dependency_info(
    dependency_info: Dict[str, str], root_info: Dict[str, str]
) -> Dict[str, str]:
    """Re-roots a path dict so that a Ayon_Usd_Resolver can use its own system for root replace to resolve a given path

    Args:
        dependecy_info:
        root_info: a flat dict containing str: root identifier {root[work]}, str: associated root path /path/to/root

    Returns: the input dependecy_info dict with replaced root_info to obtain root-less paths,
    """

    if not root_info or not dependency_info:
        return {}

    replacements = {
        re.escape(path_portion): replacer
        for replacer, path_portion in root_info.items()
    }

    pattern = re.compile("|".join(f"({pat})" for pat in replacements))

    def _replace_match(match: re.Match):
        for _, group in enumerate(match.groups(), start=1):
            if group:
                replacment = "{root[" + replacements[re.escape(group)] + "]}"
                return replacment
        return match.group(0)

    root_less_dict = {}

    for key, path in dependency_info.items():
        new_path = pattern.sub(_replace_match, path)
        root_less_dict[key] = new_path

    return root_less_dict


def _get_prim_prop_data(prim: Sdf.PrimSpec, layer: Sdf.Layer) -> List[str]:
    prop_data = []
    for prop in prim.properties:
        if isinstance(prop, Sdf.AttributeSpec):
            if prop.typeName == Sdf.ValueTypeNames.Asset:

                default_val = prop.default
                if default_val:
                    if hasattr(default_val, "__iter__"):
                        prop_data.extend(default_val)
                    else:
                        prop_data.append(default_val.path)
                    continue  # No need to check for time samples if default val is populated

                time_samples = layer.ListTimeSamplesForPath(prop.path)
                for time in time_samples:
                    value = layer.QueryTimeSample(prop.path, time)
                    prop_data.append(value.path)

    return prop_data


def _traverse_prims(prim: Sdf.PrimSpec, layer: Sdf.Layer) -> List[Sdf.PrimSpec]:
    file_list = []

    file_list.extend(_get_prim_prop_data(prim, layer))

    for child_prim in prim.nameChildren:
        file_list.extend(_traverse_prims(child_prim, layer))
    return file_list


def _remove_sdf_args(ref: str) -> str:
    re.compile("")
    uri = re.sub(re.compile(r":SDF_FORMAT_ARGS.*$"), "", ref)
    return uri


def _Resolve(ref: str, layer_path: str) -> Ar.ResolvedPath:
    if os.path.isabs(ref) or is_uri(ref):
        resolved_path = resolver.Resolve(ref)
    else:
        parent_file_dir_name = os.path.dirname(layer_path)
        abs_path = os.path.normpath(os.path.join(parent_file_dir_name, ref))
        resolved_path = resolver.Resolve(abs_path)
    return resolved_path


def _resolve_udim(udim_identifier: str, layer: Sdf.Layer) -> Dict[str, str]:
    udim_data = {}
    udim_regx = re.compile(r"<UDIM>")
    resolved_udims = UsdShade.UdimUtils.ResolveUdimTilePaths(
        str(udim_identifier), layer
    )

    for resolved_udim_path in resolved_udims:
        udim_replaced_identifier = re.sub(
            udim_regx,
            resolved_udim_path[1],
            udim_identifier,
        )
        udim_data[udim_replaced_identifier] = resolved_udim_path[0]
    return udim_data


# TODO refactor so that this function has a gather block and a write block currently all individual blocks write to the identifier_to_path_dict and that makes sanitizing the data hard
def get_asset_dependencies(layer_path: str) -> Dict[str, str]:
    layer_path = _remove_sdf_args(layer_path)
    if not layer_path:
        return {}
    if isinstance(layer_path, Ar.ResolvedPath):
        layer_path = layer_path.GetPathString()

    identifier_to_path_dict = {}

    resolved_layer_path = resolver.Resolve(layer_path)
    layer = Sdf.Layer.FindOrOpen(resolved_layer_path)
    identifier_to_path_dict[layer_path] = resolved_layer_path.GetPathString()

    prim_spec_file_paths = _traverse_prims(layer.pseudoRoot, layer)
    for prim_spec in prim_spec_file_paths:
        prim_spec = str(prim_spec)
        if "<UDIM>" in prim_spec:

            prim_spec = _remove_sdf_args(prim_spec)
            unresolved_udim_path = _Resolve(prim_spec, layer.realPath)
            identifier_to_path_dict[prim_spec] = unresolved_udim_path.GetPathString()

            udim_data = _resolve_udim(prim_spec, layer)
            identifier_to_path_dict.update(udim_data)
            continue

        prim_spec = _remove_sdf_args(prim_spec)
        identifier_to_path_dict[prim_spec] = _Resolve(prim_spec, layer.realPath)
    asset_identifier_list = layer.GetCompositionAssetDependencies()

    for ref in asset_identifier_list:

        resolved_path = _Resolve(ref, resolved_layer_path.GetPathString())

        ref = _remove_sdf_args(ref)
        identifier_to_path_dict[ref] = resolved_path.GetPathString()

        recursive_result = get_asset_dependencies(resolved_path.GetPathString())
        identifier_to_path_dict.update(recursive_result)

    return identifier_to_path_dict


# this function would work but in some UsdLib versions it will output <UDIM> tag and in some versions it will resolve ot 1001-1100. This function also dose not handle UDIM resolution at the moment
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


def write_pinning_file(
    output_path: str,
    pinning_data: Dict[str, str],
    create_missing_dirs: bool = True,
    overwrite_ok: bool = True,
) -> bool:
    """writes out a pinning file to disk in the appropriate format

    Args:
        output_path: str path where the pinning file should be written to
        pinning_data: str the pinning dict that holds all the pinning data
        create_missing_dirs: bool
        overwrite_ok: bool

    Returns: bool Ture on successful write

    """
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
        json.dump(wirte_data, pinning_file, indent=2)
    return True


def generate_pinning_file(
    entry_usd: str, root_info: Dict[str, str], pinning_file_path: str
):

    if not pinning_file_path.endswith(".json"):
        raise RuntimeError(f"Pinning file path is not a json file {pinning_file_path}")

    pinning_data = get_asset_dependencies(entry_usd)

    root_less_pinning_file_data = remove_root_from_dependency_info(
        pinning_data, root_info
    )

    root_less_pinning_file_data["ayon_pinning_data_entry_sceene"] = _remove_sdf_args(
        entry_usd
    )
    write_pinning_file(
        os.path.join(pinning_file_path),
        root_less_pinning_file_data,
    )