import ast
import h5py
import json
import pint
from h5py._hl.base import with_phil
from h5py._objects import ObjectID
from typing import Dict

from .h5utils import get_rootparent
from .. import get_config, conventions, utils
from .. import get_ureg
from ..conventions import consts

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
        assert get_ureg().default_format == get_config('ureg_format')
        return get_ureg()(self)


class WrapperAttributeManager(h5py.AttributeManager):
    """
    Subclass of h5py's Attribute Manager.
    Allows storing dictionaries as json strings and to store a dataset or a group as an
    attribute. The latter uses the name of the object. When __getitem__() is called and
    the name (string) is identified as a dataset or group, then this object is returned.
    """

    def __init__(self, parent):
        """ Private constructor."""
        super().__init__(parent)
        self._parent = parent

    @staticmethod
    def _parse_return_value(_id, ret):
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
                                if isinstance(_id, h5py.h5g.GroupID):
                                    rootgrp = get_rootparent(h5py.Group(_id))
                                    dictionary[k] = rootgrp.get(v)
                                elif isinstance(_id, h5py.h5d.DatasetID):
                                    rootgrp = get_rootparent(h5py.Dataset(_id).parent)
                                    dictionary[k] = rootgrp.get(v)
                return dictionary
            if ret[0] == '/':
                # it may be group or dataset path or actually just a filepath stored by the user
                if isinstance(_id, h5py.h5g.GroupID):
                    # call like this, otherwise recursive call!
                    rootgrp = get_rootparent(h5py.Group(_id))
                    if rootgrp.get(ret) is None:
                        # not a dataset or group, maybe just a filename that has been stored
                        return ret
                    return rootgrp.get(ret).name
                else:
                    rootgrp = get_rootparent(h5py.Dataset(_id).parent)
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
                    except (ValueError, NameError, AttributeError):
                        return ret
                return ret
            return AttributeString(ret)
        return ret

    @with_phil
    def __getitem__(self, name):

        ret = super(WrapperAttributeManager, self).__getitem__(name)
        parent = self._parent

        if get_config(
                'expose_user_prop_to_attrs') and parent.__class__ in conventions.get_current_convention().properties:
            if name in conventions.get_current_convention().properties[parent.__class__]:
                return conventions.get_current_convention().properties[parent.__class__][name].get(parent)
        return WrapperAttributeManager._parse_return_value(self._id, ret)
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

        curr_cv = conventions.get_current_convention()

        parent = self._parent
        # obj_type = parent.__class__
        if parent.__class__ in curr_cv.properties:

            sattr = curr_cv.properties[parent.__class__].get(name, None)
            if sattr is not None:
                try:
                    if value == 'None':
                        value = None
                    if value is consts.DefaultValue.EMPTY:
                        # no value given, but is mandatory. check if there's an alternative
                        if sattr.alternative_standard_attribute is None:
                            raise ValueError(f'Parameter (standard attribute) "{name}" must be provided and '
                                             f'cannot be None!')
                        return
                    if value is consts.DefaultValue.NONE:
                        # no value given and not mandatory. just not set it and do nothing
                        return
                    if isinstance(value, consts.DefaultValue):
                        value = value.value
                    return curr_cv.properties[parent.__class__][name].set(parent, value)
                except TypeError as e:
                    raise TypeError(f'Could not set "{name}" (value="{value}") to "{parent.name}". Orig error: {e}')
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
        if get_config('natural_naming'):
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
            if get_config('natural_naming'):
                self.__setitem__(key, value)
                return
            else:
                raise RuntimeError('Natural naming is disabled. Use the setitem method to set attributes.')
        super().__setattr__(key, value)

    def rename(self, key, new_name):
        """Rename an existing attribute"""
        tmp_val = self[key]
        self[new_name] = tmp_val
        assert tmp_val == self[new_name]
        del self[key]

    def sdump(self, show_private=True) -> None:
        """Print all attributes. Hides all attributes that start with __ and end with __ if show_private is False.

        Parameters
        ----------
        show_private : bool, optional
            If True, all attributes are shown, by default True. If False, all attributes that start with
            "__" and end with "__" are hidden.
        """
        first_line = f'Attributes of "{self._parent.name}":'
        print(first_line)
        print('-' * len(first_line))

        adict = dict(self.items())
        if not show_private:
            key_lens = [len(k) for k in adict.keys() if not k.startswith('__') and not k.endswith('__')]
        else:
            key_lens = [len(k) for k in adict.keys()]
        if len(key_lens) == 0:
            return None
        keylen = max(key_lens)
        for k, v in adict.items():
            if not show_private:
                if k.startswith('__') and k.endswith('__'):
                    continue
            print(f'{k:{keylen}}:  {v}')

    @property
    def raw(self) -> "h5py._hl.attrs.AttributeManager":
        """Return the original h5py attribute object manager"""
        from h5py._hl import attrs
        from h5py._objects import phil
        with phil:
            return attrs.AttributeManager(self._parent)
