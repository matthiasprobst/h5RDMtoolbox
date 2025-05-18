"""Attribute module"""
import ast
import json
import logging
import warnings
from datetime import datetime
from typing import Dict, Union, Tuple, Optional, Any

import numpy as np
import pint
import pydantic
import rdflib
from h5py._hl.attrs import AttributeManager
from h5py._hl.base import with_phil
from h5py._objects import ObjectID, phil
from pydantic import HttpUrl

from .. import errors
from .. import get_config, convention, utils
from .. import get_ureg
from .. import protected_attributes
from ..convention import consts

logger = logging.getLogger('h5rdmtoolbox')
H5_DIM_ATTRS = protected_attributes.h5rdmtoolbox


class AttrDescriptionError(Exception):
    """Generic attribute description error"""
    pass


class Attribute:
    """Helper class for quick assignment of RDF attributes to the HDF5 file.

    Examples
    --------
    >>> import h5rdmtoolbox as h5tbx
    >>> from ontolutils import M4I
    >>> rdf_attr = h5tbx.Attribute('0000-0001-8729-0482', rdf_predicate=M4I.orcidId,
    ...                            rdf_object='https://orcid.org/0000-0001-8729-0482')
    >>> with h5tbx.File('test.h5', 'w') as h5:
    ...     grp = h5.create_group('person')
    ...     grp.attrs['orcid'] = rdf_attr
    ...     # equal to:
    ...     # grp.attrs['orcid'] = '0000-0001-8729-0482'
    ...     # grp.rdf.predicate['orcid'] = str(M4I.orcidId)
    ...     # grp.rdf.object['orcid'] = 'https://orcid.org/0000-0001-8729-0482'
    """

    def __init__(self,
                 value, *,
                 definition: Optional[str] = None,
                 rdf_predicate=None,
                 frdf_predicate=None,
                 rdf_object=None,
                 frdf_object=None,
                 ):
        self.value = value
        self.definition = definition  # skos:definition
        if rdf_predicate is not None and frdf_predicate is not None:
            raise ValueError('You cannot set both rdf_predicate and frdf_predicate at the same time.')
        if rdf_object is not None and frdf_object is not None:
            raise ValueError('You cannot set both rdf_object and frdf_object at the same time.')
        self.rdf_predicate = self._validate_rdf(rdf_predicate)
        self.frdf_predicate = self._validate_rdf(frdf_predicate)
        self.rdf_object = self._validate_rdf(rdf_object)
        self.frdf_object = self._validate_rdf(frdf_object)

    @staticmethod
    def _validate_rdf(value):
        if value is None:
            return
        try:
            str(HttpUrl(value))
        except pydantic.ValidationError as e:
            raise AttrDescriptionError(
                f'Invalid URL: "{value}". This was validated with pydantic. Pydantic error: {e}'
            )
        return value

    def __repr__(self) -> str:
        out = f'{self.__class__.__name__}({self.value}'
        if self.rdf_predicate is not None:
            out += f', rdf_predicate={self.rdf_predicate}'
        if self.rdf_object is not None:
            out += f', rdf_object={self.rdf_object}'
        if self.definition is not None:
            out += f', definition={self.definition}'
        out += ')'
        return out

    def __str__(self) -> str:
        return self.__repr__()


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
    keep = [k for k in attrs.keys() if k not in H5_DIM_ATTRS]
    return {k: attrs[k] for k in keep}
    # return {k: v for k, v in attrs.items() if k not in H5_DIM_ATTRS}


def _check_iri(url):
    import requests
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f'URL {url} does not exist.')
    return True


class AttributeString(str):
    """String with special methods such as `to_pint()`"""

    def to_pint(self) -> "pint.util.Quantity":
        """Returns a pint.Quantity object"""
        assert get_ureg().default_format == get_config('ureg_format')
        return get_ureg()(self)


class WrapperAttributeManager(AttributeManager):
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
                        # else:
                        #     if v[0] == '/':
                        #         if isinstance(_id, h5py.h5g.GroupID):
                        #             rootgrp = get_rootparent(h5py.Group(_id))
                        #             dictionary[k] = rootgrp.get(v)
                        #         elif isinstance(_id, h5py.h5d.DatasetID):
                        #             rootgrp = get_rootparent(h5py.Dataset(_id).parent)
                        #             dictionary[k] = rootgrp.get(v)
                return dictionary
            # if ret[0] == '/':
            #     # it may be group or dataset path or actually just a filepath stored by the user
            #     if isinstance(_id, h5py.h5g.GroupID):
            #         # call like this, otherwise recursive call!
            #         from .core import Group
            #         rootgrp = get_rootparent(Group(_id))
            #         if rootgrp.get(ret) is None:
            #             # not a dataset or group, maybe just a filename that has been stored
            #             return ret
            #         return rootgrp.get(ret)
            #     else:
            #         from .core import Dataset
            #         rootgrp = get_rootparent(Dataset(_id).parent)
            #         return rootgrp.get(ret)
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
                        # return ast.literal_eval(ret.replace(' ', ', '))
                    except (ValueError, NameError, AttributeError):
                        return ret
                return ret
            return AttributeString(ret)
        if isinstance(ret, np.ndarray) and ret.dtype.name == 'object':
            vstr = str(ret.tolist())
            if '<HDF5 object reference>' in vstr:
                return ret
            return WrapperAttributeManager._parse_return_value(_id, vstr)
        return ret

    @with_phil
    def __getitem__(self, name: str):

        ret = super(WrapperAttributeManager, self).__getitem__(name)
        parent = self._parent

        if get_config(
                'expose_user_prop_to_attrs') and parent.__class__ in convention.get_current_convention().properties:
            if name in convention.get_current_convention().properties[parent.__class__]:
                return convention.get_current_convention().properties[parent.__class__][name].get(parent)
        return WrapperAttributeManager._parse_return_value(self._id, ret)

    @with_phil
    def __delitem__(self, name):
        super().__delitem__(name)
        self._parent.rdf.delete(name)

    def create(self,
               name,
               data,
               shape=None, dtype=None,
               rdf_predicate: Union[str, rdflib.URIRef] = None,
               rdf_object: Optional[Union[str, rdflib.URIRef]] = None,
               frdf_predicate: Union[str, rdflib.URIRef] = None,
               frdf_object: Optional[Union[str, rdflib.URIRef]] = None,
               definition: Optional[str] = None,
               **kwargs) -> Any:
        """
        Create a new attribute.

        .. note:: Via the config setting "ignore_none" (`h5tbx.set_config(ignore_none=True)`) attribute values, that are None are not written.


        Parameters
        ----------
        name: str
            Name of the attribute.
        data: any
            Attribute value.
        shape: tuple, optional
            Shape of the attribute. If None, the shape is determined from the data.
        dtype:
            Data type of the attribute. If None, the data type is determined from the data.
        rdf_predicate: Union[str, rdflib.URIRef], optional
            IRI of the predicate
        rdf_object: Union[str, rdflib.URIRef], optional
            IRI of the object
        """
        if data is None and get_config('ignore_none'):
            logger.debug(f'Attribute "{name}" is None and "ignore_none" in config is True. Attribute is not created.')
            return
        r = super().create(name,
                           utils.parse_object_for_attribute_setting(data),
                           shape, dtype)
        _predicate = kwargs.get('predicate', None)
        if _predicate is not None:
            rdf_predicate = _predicate
            warnings.warn('The "predicate" argument is deprecated. Use "rdf_predicate" instead.', DeprecationWarning)
        _object = kwargs.get('predicate', None)
        if _object is not None:
            rdf_object = _object
            warnings.warn('The "object" argument is deprecated. Use "rdf_object" instead.', DeprecationWarning)

        if rdf_predicate is not None:
            self._parent.rdf.predicate[name] = rdf_predicate
        if rdf_object is not None:
            self._parent.rdf.object[name] = rdf_object
        if definition is not None:
            self._parent.rdf[name].definition = definition
        _frdf = None
        if frdf_predicate is not None or frdf_object is not None:
            try:
                _frdf = self._parent.frdf
            except AttributeError:
                raise AttributeError('You try to assign a rdf to the file level, however, "{self._parent.name}" is not the root level')
        if _frdf:
            if frdf_predicate is not None:
                _frdf.predicate[name] = frdf_predicate
            if frdf_object is not None:
                _frdf.object[name] = frdf_object
        return r

    @with_phil
    def __setitem__(self,
                    name: Union[str, Tuple[str, str]],
                    value, attrs: Optional[Dict] = None):
        """ Set a new attribute, overwriting any existing attribute.

        The type and shape of the attribute are determined from the data.  To
        use a specific type or shape, or to preserve the type of attribute,
        use the methods create() and modify().

        Parameters
        ----------
        name : Union[str, Tuple[str, str]]
            Name of the attribute. If it is a tuple, the second element is the IRI of the attribute.
        value : any
            Attribute value. Can also be type `AttributeValue` to set a value and its object IRI.
        """
        if name == '_parent':
            return

        if isinstance(value, Attribute):
            object_iri = value.rdf_object
            predicate_iri = value.rdf_predicate
            fpredicate_iri = value.frdf_predicate
            frdf_object_iri = value.frdf_object
            attr_def = value.definition
            value = value.value

            if not isinstance(name, tuple):
                self.create(name,
                            value,
                            rdf_predicate=predicate_iri,
                            frdf_predicate=fpredicate_iri,
                            rdf_object=object_iri,
                            frdf_object=frdf_object_iri,
                            definition=attr_def)

        else:
            object_iri = None
            predicate_iri = None
            attr_def = None

        if isinstance(name, tuple):
            # length must be 2, second element must be a IRI (not checked though)
            if not len(name) == 2:
                raise ValueError('Tuple must have length 2 in order to interpret it as an'
                                 'attribute name and its IRI')
            if predicate_iri is not None:
                raise ValueError('You cannot set the predicate iri at the same time by RDFAttribute and through '
                                 'the tuple syntax.')
            _name, predicate_iri = name
            self.create(_name, value,
                        rdf_predicate=predicate_iri,
                        rdf_object=object_iri,
                        definition=attr_def)
            return

        if not isinstance(name, str):
            raise TypeError(f'Attribute name must be a str but got {type(name)}')

        curr_cv = convention.get_current_convention()

        parent = self._parent
        # obj_type = parent.__class__
        if parent.__class__ in curr_cv.properties:
            sattr = curr_cv.properties[parent.__class__].get(name, None)
            if sattr is not None:
                logger.debug(f'validating {name} with {sattr}')
                # try:

                if value is consts.DefaultValue.NONE:
                    # no value given and not mandatory. just not set it and do nothing
                    return

                if value == 'None':
                    value = None

                if value is consts.DefaultValue.EMPTY:
                    # no value given, but is mandatory. check if there's an alternative
                    _alternative_sattr = sattr.alternative_standard_attribute
                    if _alternative_sattr is None:
                        raise errors.StandardAttributeError(
                            f'Convention "{curr_cv.name}" expects standard attribute "{name}" to be provided '
                            f'as an argument during {self._parent.__class__.__name__.lower()} creation.'
                        )
                    if attrs[_alternative_sattr] is None:
                        other_provided_attrs = {k: v for k, v in attrs.items() if
                                                v is not None and not isinstance(v, consts._SpecialDefaults)}
                        raise errors.StandardAttributeError(
                            f'Convention "{curr_cv.name}" expects standard attribute "{name}" to be provided '
                            f'as an argument during {self._parent.__class__.__name__.lower()} creation. Alternative '
                            f'standard attribute for it is "{_alternative_sattr}" but is not found in the other '
                            f'provided attributes: {other_provided_attrs}.'
                        )
                    return

                if isinstance(value, consts.DefaultValue):
                    value = value.value
                return sattr.set(
                    parent=parent,
                    value=value,
                    attrs=attrs
                )

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
    def raw(self) -> AttributeManager:
        """Return the original h5py attribute object manager"""
        with phil:
            return AttributeManager(self._parent)

    def write_uuid(self, uuid: Optional[str] = None,
                   name: Optional[str] = None,
                   overwrite: bool = False) -> str:
        """Write an uuid to the attribute of the object.

        Parameters
        ----------
        uuid : str=None
            The uuid to write. If None, a new uuid is generated.
        name: str=None
            Name of the attribute. If None, the default name is taken from the configuration.
        overwrite: bool=False
            If the attribute already exists, it is not overwritten if overwrite is False.

        Returns
        -------
        str
            The uuid as string.
        """
        if name is None:
            name = get_config('uuid_name')

        if name in self and not overwrite:
            raise ValueError(f'The attribute "{name}" cannot be written. It already exists and '
                             '"overwrite" is set to False')
        if uuid is None:
            from uuid import uuid4
            uuid = uuid4()
        suuid = str(uuid)
        self.create(name=name, data=suuid)
        return suuid

    def write_iso_timestamp(self,
                            name='timestamp',
                            dt: Optional[datetime] = None,
                            overwrite: bool = False, **kwargs):
        """Write the iso timestamp to the attribute of the object.

        Parameters
        --
        """
        if name in self and not overwrite:
            raise ValueError(f'The attribute "{name}" cannot be written. It already exists and '
                             '"overwrite" is set to False')
        if dt is None:
            dt = datetime.now()
        else:
            if not isinstance(dt, datetime):
                raise TypeError(f'Invalid type for parameter "dt". Expected type datetime but got "{type(dt)}"')
        self.create(name=name, data=dt.isoformat(**kwargs))
