"""Utilities (mostly helper functions) for interaction with HDF5"""


def get_rootparent(obj):
    """Return the root group instance."""

    def get_root(parent):
        global found
        found = parent.parent

        def search(parent):
            global found
            parent = parent.parent
            if parent.name == '/':
                found = parent
            else:
                search(parent)

        search(parent)
        return found

    if obj.name == '/':
        return obj
    return get_root(obj.parent)


def _is_not_valid_natural_name(instance, name: str, is_natural_naming_enabled: bool) -> bool:
    """Check if name is already a function call or a property"""
    if is_natural_naming_enabled:
        if isinstance(name, str):
            return hasattr(instance, name)
        return hasattr(instance, name.decode("utf-8"))
