"""
Contains all property accessors

the python filename and accessor class name must not be identical!
"""

from typing import Union

from ._logger import logger

REGISTRATED_ATTRIBUTE_NAMES = []


def _register_hdf_attribute(cls, name: str = None, overwrite: bool = False):
    def decorator(accessor):
        """decorator"""
        return register_hdf_attribute(accessor, cls, name, overwrite)

    return decorator


def register_hdf_attr(cls: Union["Dataset", "Group"], overwrite=False, name: str = None):
    """registers a property to a group or dataset. getting method must be specified, setting and deleting are optional,
    also docstring is optional but strongly recommended!

    Parameters
    ----------
    cls: Dataset or Group
        HDF5 object to attach standard attribute to.
    overwrite: bool, default=False
        Whether to overwrite an existing attributes
    name: str, default=None
        Name to be used for the attribute. If None, cls.__name__ is used
    """
    return _register_hdf_attribute(cls, name=name, overwrite=overwrite)


def register_hdf_attribute(attribute_class, cls, name, overwrite):
    """register an attribute defined in `attribute_class` to `cls`"""
    if name is None:
        attrname = attribute_class.__name__
    else:
        attrname = name
    REGISTRATED_ATTRIBUTE_NAMES.append(attrname)
    if hasattr(cls, attrname):
        if overwrite:
            logger.debug(f'Overwriting existing property "{attrname}" of {cls}.')
            delattr(cls, attrname)
        else:
            raise AttributeError(f'Cannot register property {attrname} to {cls} because it has already a property '
                                 f'with this name.')
    fget, fset, fdel, doc = None, None, None, None
    if hasattr(attribute_class, 'get'):
        fget = attribute_class.get
    if hasattr(attribute_class, 'set'):
        fset = attribute_class.set
    if hasattr(attribute_class, 'delete'):
        fdel = attribute_class.delete
    if hasattr(attribute_class, 'doc'):
        doc = attribute_class.doc
    logger.debug(f'Register special hdf attribute {name} to {cls}')
    setattr(cls, attrname, property(fget, fset, fdel, doc))
    return attribute_class
