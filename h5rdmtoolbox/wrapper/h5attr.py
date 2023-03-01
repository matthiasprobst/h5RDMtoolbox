import ast
import h5py
import json
import pint
from h5py._hl.base import with_phil
from h5py._objects import ObjectID
from typing import Dict

from .h5utils import get_rootparent
from .. import config
from .. import utils
from .._config import ureg
from ..conventions.registration import REGISTRATED_ATTRIBUTE_NAMES

H5_DIM_ATTRS = ('CLASS', 'NAME', 'DIMENSION_LIST', 'REFERENCE_LIST', 'COORDINATES')


def pop_hdf_attributes(attrs: Dict) -> Dict:
    """Remove HDF attributes like NAME, CLASS, .... from the input dictionary

    Parameters
    ----------
    attrs: Dict
        Input dictionary

    Returns
    -------
    dict
        Dictionary without entries registered in `H5_DIM_ATTRS`
    """
    return {k: v for k, v in attrs.items() if k not in H5_DIM_ATTRS}


class AttributeString(str):
    """String with special methods such as `to_pint()`"""

    def to_pint(self) -> "pint.util.Quantity":
        """Returns a pint.Quantity object"""
        return ureg(self)


class WrapperAttributeManager(h5py.AttributeManager):
    """
    Subclass of h5py's Attribute Manager.
    Allows storing dictionaries as json strings and to store a dataset or a group as an
    attribute. The latter uses the name of the object. When __getitem__() is called and
    the name (string) is identified as a dataset or group, then this object is returned.
    """

    def __init__(self, parent):  # , identifier_convention: conventions.StandardNameTable):
        """ Private constructor."""
        super().__init__(parent)
        self._parent = parent
        # self.identifier_convention = identifier_convention  # standard_name_convention

    @with_phil
    def __getitem__(self, name):
        # if name in self.__dict__:
        #     return super(WrapperAttributeManager, self).__getitem__(name)
        ret = super(WrapperAttributeManager, self).__getitem__(name)
        if isinstance(ret, str):
            if ret == '':
                return ret
            if ret[0] == '{':
                dictionary = json.loads(ret)
                for k, v in dictionary.items():
                    if isinstance(v, str):
                        if not v:
                            dictionary[k] = ''
                        else:
                            if v[0] == '/':
                                if isinstance(self._id, h5py.h5g.GroupID):
                                    rootgrp = get_rootparent(h5py.Group(self._id))
                                    dictionary[k] = rootgrp.get(v)
                                elif isinstance(self._id, h5py.h5d.DatasetID):
                                    rootgrp = get_rootparent(h5py.Dataset(self._id).parent)
                                    dictionary[k] = rootgrp.get(v)
                return dictionary
            if ret[0] == '/':
                # it may be group or dataset path or actually just a filepath stored by the user
                if isinstance(self._id, h5py.h5g.GroupID):
                    # call like this, otherwise recursive call!
                    rootgrp = get_rootparent(h5py.Group(self._id))
                    if rootgrp.get(ret) is None:
                        # not a dataset or group, maybe just a filename that has been stored
                        return ret
                    return rootgrp.get(ret).name
                else:
                    rootgrp = get_rootparent(h5py.Dataset(self._id).parent)
                    return rootgrp.get(ret).name
            if ret[0] == '(':
                if ret[-1] == ')':
                    # might be a tuple object
                    return ast.literal_eval(ret)
                return ret
            if ret[0] == '[':
                if ret[-1] == ']':
                    # might be a list object
                    try:
                        return ast.literal_eval(ret)
                    except (NameError, AttributeError):
                        return ret
                return ret
            return AttributeString(ret)
        return ret

    @with_phil
    def __setitem__(self, name, value):
        """ Set a new attribute, overwriting any existing attribute.

        The type and shape of the attribute are determined from the data.  To
        use a specific type or shape, or to preserve the type of attribute,
        use the methods create() and modify().
        """
        if name == '_parent':
            return
        if not isinstance(name, str):
            raise TypeError(f'Attribute name must be a str but got {type(name)}')

        if name in REGISTRATED_ATTRIBUTE_NAMES:
            if hasattr(self._parent, name):
                setattr(self._parent, name, value)
                return
        utils.create_special_attribute(self, name, value)

    def __repr__(self):
        return super().__repr__()

    def __str__(self):
        outstr = ''
        adict = dict(self.items())
        key_lens = [len(k) for k in adict.keys()]
        if len(key_lens) == 0:
            return None
        keylen = max(key_lens)
        for k, v in adict.items():
            outstr += f'{k:{keylen}}  {v}\n'
        return outstr[:-1]

    def __getattr__(self, item):
        if config.natural_naming:
            if item in self.__dict__:
                return super().__getattribute__(item)
            if item in self.keys():
                return self[item]
            return super().__getattribute__(item)
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if key in ('_parent',):
            super().__setattr__(key, value)
            return
        if not isinstance(value, ObjectID):
            self.__setitem__(key, value)
            return
        super().__setattr__(key, value)

    def rename(self, key, new_name):
        """Rename an existing attribute"""
        tmp_val = self[key]
        self[new_name] = tmp_val
        assert tmp_val == self[new_name]
        del self[key]
