"""HDF5-specific utilities for h5rdmtoolbox."""

import datetime
import json
import pathlib
import warnings
from typing import Dict, List, Tuple, Union, Optional

import h5py
import numpy as np
import pint
from h5py import File

from .. import get_config
from .._version import __version__
from ..ld import rdf

logger = __import__("h5rdmtoolbox", fromlist=["logger"]).logger


def _has_object_type(target: Union[h5py.Group, pathlib.Path], obj_type: type) -> bool:
    """Check if target contains any object of the given type.

    Parameters
    ----------
    target : h5py.Group or pathlib.Path
        HDF5 group or path to HDF5 file.
    obj_type : type
        The type to check for (h5py.Dataset or h5py.Group).

    Returns
    -------
    bool
        True if target contains at least one object of the given type.
    """
    if not isinstance(target, h5py.Group):
        with h5py.File(target) as h5:
            return _has_object_type(h5, obj_type)
    return any(isinstance(obj, obj_type) for obj in target.values())


def has_datasets(target: Union[h5py.Group, pathlib.Path]) -> bool:
    """Check if file has datasets.

    Parameters
    ----------
    target : h5py.Group or pathlib.Path
        HDF5 group or path to HDF5 file.

    Returns
    -------
    bool
        True if target contains at least one dataset.
    """
    return _has_object_type(target, h5py.Dataset)


def has_groups(target: Union[h5py.Group, pathlib.Path]) -> bool:
    """Check if file has groups.

    Parameters
    ----------
    target : h5py.Group or pathlib.Path
        HDF5 group or path to HDF5 file.

    Returns
    -------
    bool
        True if target contains at least one group.
    """
    return _has_object_type(target, h5py.Group)


def create_h5tbx_version_grp(root: h5py.Group) -> h5py.Group:
    """Creates a group in an HDF5 file with the h5rdmtoolbox version as an attribute.

    Parameters
    ----------
    root : h5py.Group
        Root group of the HDF5 file.

    Returns
    -------
    h5py.Group
        The created version group.
    """
    logger.debug(
        'Creating group "h5rdmtoolbox" with attribute "__h5rdmtoolbox_version__" in file'
    )
    version_group = root.create_group("h5rdmtoolbox")
    version_group.attrs["__h5rdmtoolbox_version__"] = __version__
    version_group.attrs["code_repository"] = (
        "https://github.com/matthiasprobst/h5RDMtoolbox"
    )
    version_group.attrs[rdf.RDF_PREDICATE_ATTR_NAME] = json.dumps(
        {
            "code_repository": "https://schema.org/codeRepository",
            "__h5rdmtoolbox_version__": "https://schema.org/softwareVersion",
        }
    )
    version_group.attrs[rdf.RDF_TYPE_ATTR_NAME] = (
        "https://schema.org/SoftwareSourceCode"
    )
    return version_group


def touch_tmp_hdf5_file(
    touch: bool = True, attrs: Optional[Dict] = None
) -> pathlib.Path:
    """Generates a file path in directory h5rdmtoolbox/.tmp with filename dsXXXX.hdf.

    Parameters
    ----------
    touch : bool, optional
        If True, creates the file, by default True.
    attrs : dict, optional
        Attributes to set on the root group, by default None.

    Returns
    -------
    pathlib.Path
        Path to the created HDF5 file.
    """
    from .file_io import generate_temporary_filename

    hdf_filepath = generate_temporary_filename(suffix=".hdf")
    if touch:
        with File(hdf_filepath, "w") as h5touch:
            if get_config("auto_create_h5tbx_version"):
                create_h5tbx_version_grp(h5touch)
            if attrs is not None:
                for ak, av in attrs.items():
                    create_special_attribute(h5touch.attrs, ak, av)
    return hdf_filepath


def try_making_serializable(d: Dict) -> Dict:
    """Tries to make a dictionary serializable by converting numpy arrays to lists.

    Parameters
    ----------
    d : dict
        Dictionary to make serializable.

    Returns
    -------
    dict
        Serializable dictionary.
    """
    result_dict = {}
    if not isinstance(d, dict):
        return d
    for key, value in d.items():
        if isinstance(value, dict):
            result_dict[key] = try_making_serializable(value)
        elif isinstance(value, np.ndarray):
            result_dict[key] = value.tolist()
        elif isinstance(value, (int, str, float, bool)):
            result_dict[key] = value
        elif isinstance(value, tuple):
            result_dict[key] = tuple([try_making_serializable(v) for v in value])
        elif isinstance(value, list):
            result_dict[key] = [try_making_serializable(v) for v in value]
        else:
            try:
                result_dict[key] = value.__to_h5attr__()
            except AttributeError:
                warnings.warn(
                    f"Type {type(value)} of value {value} not supported. Maybe json can handle it?"
                )
                result_dict[key] = value
    return result_dict


def create_special_attribute(h5obj: h5py.AttributeManager, name: str, value):
    """Allows writing more than the usual hdf5 attributes.

    Parameters
    ----------
    h5obj : h5py.AttributeManager
        HDF5 attribute manager.
    name : str
        Attribute name.
    value : any
        Attribute value.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (h5py.Dataset, h5py.Group)):
                value[k] = v.name
        _value = json.dumps(try_making_serializable(value))
    elif isinstance(value, (h5py.Dataset, h5py.Group)):
        _value = value.name
    elif isinstance(value, str):
        _value = value
    elif isinstance(value, pint.Quantity):
        _value = str(value)
    elif isinstance(value, pathlib.Path):
        _value = str(value)
    elif isinstance(value, datetime.datetime):
        _value = value.strftime(get_config("dtime_fmt"))
    else:
        _value = value

    if hasattr(name, "fragment"):
        fragment = name.fragment
        if not fragment:
            raise ValueError(f"Name {name} has no fragment")
        from ..ld.rdf import set_predicate

        set_predicate(h5obj, fragment, name)
        name = fragment

    try:
        h5obj.create(name, data=_value)
    except TypeError:
        try:
            h5obj.create(name, data=str(_value))
        except TypeError as e2:
            raise RuntimeError(
                f"Error setting attribute to HDF object {h5obj._parent}:"
                f"\n  name: {name}\n  value: {value} \n  type: {type(value)}\n"
                f"Original error: {e2}"
            ) from e2


def parse_object_for_attribute_setting(
    value,
) -> Union[str, int, float, bool, List[str], Tuple]:
    """Parses an object to a string for setting an attribute.

    Parameters
    ----------
    value : any
        Object to parse.

    Returns
    -------
    str, int, float, bool, list, or tuple
        Parsed value.
    """
    if isinstance(value, pint.Unit):
        return str(value)
    if isinstance(value, pint.Quantity):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [parse_object_for_attribute_setting(v) for v in value]
    if isinstance(value, tuple):
        return tuple([parse_object_for_attribute_setting(v) for v in value])
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, (h5py.Dataset, h5py.Group)):
        return value.name
    if hasattr(value, "__h5attr_repr__"):
        return value.__h5attr_repr__()
    try:
        return str(value)
    except TypeError:
        raise TypeError(f"Cannot parse type {type(value)} to string")


OBJ_FLT_DICT = {
    "group": h5py.Group,
    "groups": h5py.Group,
    "dataset": h5py.Dataset,
    "datasets": h5py.Dataset,
    "$group": h5py.Group,
    "$groups": h5py.Group,
    "$dataset": h5py.Dataset,
    "$datasets": h5py.Dataset,
}


def process_obj_filter_input(objfilter: str) -> Union[h5py.Dataset, h5py.Group, None]:
    """Return the object based on the input string.

    Parameters
    ----------
    objfilter : str or None
        Filter string ('dataset', 'group', etc.) or None.

    Returns
    -------
    h5py.Dataset, h5py.Group, or None
        The object type to filter for.

    Raises
    ------
    ValueError
        If the input string is not valid.
    TypeError
        If the input is not a string or h5py object.
    """
    if objfilter is None:
        return
    if isinstance(objfilter, str):
        try:
            return OBJ_FLT_DICT[objfilter.lower()]
        except KeyError:
            raise ValueError(
                f'Expected values for argument objfilter are "dataset" or "group", not "{objfilter}"'
            )
    if not isinstance(objfilter, (h5py.Dataset, h5py.Group)):
        raise TypeError(
            f'Expected values for argument objfilter are "dataset" or "group", not {type(objfilter)}'
        )
    return objfilter
