"""Utilities (mostly helper functions) for interaction with HDF5"""


def get_rootparent(obj):
    """Return the root group instance.

    Parameters
    ----------
    obj : h5py.Group or h5py.Dataset
        HDF5 object to find root for.

    Returns
    -------
    h5py.Group
        Root group of the HDF5 file.
    """
    if obj.name == "/":
        return obj

    def search(parent):
        if parent.parent.name == "/":
            return parent.parent
        return search(parent.parent)

    return search(obj.parent)


def _is_not_valid_natural_name(
    instance, name: str, is_natural_naming_enabled: bool
) -> bool:
    """Check if name is already a function call or a property"""
    if is_natural_naming_enabled:
        if isinstance(name, str):
            return hasattr(instance, name)
        return hasattr(instance, name.decode("utf-8"))
