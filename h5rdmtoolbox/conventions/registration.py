"""
Contains all property accessors

the python filename and accessor class name must not be identical!
"""

from typing import Union

STANDARD_ATTRIBUTE_NAMES = []


def _register_standard_attribute(cls, name: str = None, overwrite: bool = False):
    def decorator(accessor):
        """decorator"""
        if name is None:
            attrname = accessor.__name__
        else:
            attrname = name
        STANDARD_ATTRIBUTE_NAMES.append(attrname)
        if hasattr(cls, attrname):
            if overwrite:
                print(f'Overwriting existing property {attrname}.')
                delattr(cls, attrname)
            else:
                raise AttributeError(f'Cannot register property {attrname} to {cls} because it has already a property '
                                     f'with this name.')
        fget, fset, fdel, doc = None, None, None, None
        if hasattr(accessor, 'get'):
            fget = accessor.get
        if hasattr(accessor, 'set'):
            fset = accessor.set
        if hasattr(accessor, 'delete'):
            fdel = accessor.delete
        if hasattr(accessor, 'doc'):
            doc = accessor.doc
        setattr(cls, attrname, property(fget, fset, fdel, doc))
        return accessor

    return decorator


def register_standard_attribute(cls: Union["H5Dataset", "H5Group"], overwrite=False, name: str = None):
    """registers a property to a group or dataset. getting method must be specified, setting and deleting are optional,
    also docstring is optional but strongly recommended!

    Parameters
    ----------
    cls: H5Dataset or H5Group
        HDF5 object to attach standard attribute to.
    overwrite: bool, default=False
        Whether to overwrite an existing attributes
    attrname: str, default=None
        Name to be used for the attribute. If None, cls.__name__ is used
    """
    # if not isinstance(cls, (H5Dataset, H5Group)):
    #     raise TypeError(f'Registration is only possible to H5dataset or H5Group but not {type(cls)}')
    return _register_standard_attribute(cls, name=name, overwrite=overwrite)
