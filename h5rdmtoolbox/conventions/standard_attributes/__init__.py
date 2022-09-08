"""
Contains all property accessors

the python filename and accessor class name must not be identical!
"""

from typing import Union

STANDARD_ATTRIBUTE_NAMES = []


def _register_standard_attribute(cls, overwrite=False):
    def decorator(accessor):
        """decorator"""
        if hasattr(accessor, '__propname__'):
            name = accessor.__propname__
        else:
            name = accessor.__name__
        STANDARD_ATTRIBUTE_NAMES.append(name)
        if hasattr(cls, name):
            if overwrite:
                print(f'Overwriting existing property {name}.')
                delattr(cls, name)
            else:
                raise AttributeError(f'Cannot register property {name} to {cls} because it has already a property with '
                                     'this name.')
        fget, fset, fdel, doc = None, None, None, None
        if hasattr(accessor, 'get'):
            fget = accessor.get
        if hasattr(accessor, 'set'):
            fset = accessor.set
        if hasattr(accessor, 'delete'):
            fdel = accessor.delete
        if hasattr(accessor, 'doc'):
            doc = accessor.doc
        setattr(cls, name, property(fget, fset, fdel, doc))
        return accessor

    return decorator


def register_standard_attribute(cls: Union["H5Dataset", "H5Group"], overwrite=False):
    """registers a property to a group or dataset. getting method must be specified, setting and deleting are optional,
    also docstring is optional but strongly recommended!"""
    # if not isinstance(cls, (H5Dataset, H5Group)):
    #     raise TypeError(f'Registration is only possible to H5dataset or H5Group but not {type(cls)}')
    return _register_standard_attribute(cls, overwrite)
