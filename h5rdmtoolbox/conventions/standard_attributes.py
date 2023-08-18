"""standard attribute module"""
import abc
import json
import numpy as np
import pathlib
from datetime import datetime
from typing import Dict, List, Union, Tuple

from . import errors
from . import logger
from .consts import DefaultValue
from .validator import StandardAttributeValidator
from .validator import get_validator
from .. import get_ureg, get_config
from ..utils import DocStringParser
from ..wrapper.core import File, Group, Dataset
from ..wrapper.h5attr import WrapperAttributeManager

av_validators = get_validator()

__doc_string_parser__ = {File: {'__init__': DocStringParser(File)},
                         Group: {'create_group': DocStringParser(Group.create_group),
                                 'create_dataset': DocStringParser(Group.create_dataset)}}

__all__ = ['StandardAttribute', ]


def _pint_quantity(q):
    return get_ureg()(q)


def _pint_unit(u):
    return get_ureg().Unit(u)


def _standard_name_table(snt):
    from .standard_names.table import StandardNameTable
    if isinstance(snt, dict):
        return StandardNameTable.from_yaml(snt)
    if not isinstance(snt, str):
        raise TypeError(f'Unexpected type for the standard name table: {type(snt)}')
    if snt.startswith('{'):
        return StandardNameTable(**json.loads(snt))
    if snt.startswith('https://zenodo.org/record/') or snt.startswith('10.5281/zenodo.'):
        return StandardNameTable.from_zenodo(doi=snt)
    if snt.startswith('https://'):
        return StandardNameTable.from_url(snt)
    if pathlib.Path(snt).exists():
        return StandardNameTable.from_yaml(snt)
    raise RuntimeError('Could not parse standard name table.')


def make_dict(ref):
    """If input is string repr of dict, return dict"""
    if isinstance(ref, np.ndarray):
        ref = ref.tolist()
    elif isinstance(ref, str):
        if ref[0] == '{':
            return json.loads(ref)
        return ref
    _out = []
    for r in ref:
        if isinstance(r, str) and r[0] == '{':
            _out.append(json.loads(r))
        else:
            _out.append(r)
    return _out


def _isodatetime(dt):
    # expecting isoformat!
    return datetime.fromisoformat(dt)


def get_validator(**validator: Dict) -> List[StandardAttributeValidator]:
    """return the respective StandardAttributeValidator

    validator_identifier: str:
        E.g. $regex, $orcid, $in, $standard_name, $standard_name_unit
    """
    for name, value in validator.items():
        if name not in av_validators:
            raise ValueError(f'No validator class found for "{name}"')
    return [av_validators[name](value) for name, value in validator.items()]


class StandardAttribute(abc.ABC):
    """StandardAttribute class for the standardized attributes

    Parameters
    ----------
    name: str
        The name of the attribute
    validator: str | dict
        The validator for the attribute. If the validator takes a parameter, pass it as dict.
        Examples for no-parameter validator: "$pintunits", "$standard_name", "$orcid", "$url"
        Examples for validator with parameter: {"$regex": "^[a-z0-9_]*$"}, {"$in": ["a", "b", "c"]}
    target_methods: str | List[str]
        The method to which the attribute belongs. If the standard attribute is positional for all methods to
        which it applies, pass a list of strings, e.g. target_methods=["create_group", "create_dataset"].
        If it is positional and is only valid for one method, pass a string, e.g. target_methods="create_group".
    description: str
        The description of the attribute
    default_value: any, optional=DefaultValue.EMPTY
        If the attribute is positional, it has no default value, then pass DefaultValue.EMPTY (the default).
        Otherwise, pass the default value. The default value applies to all methods to which the attribute applies.
    alternative_standard_attribute; str, optional=None
        The name of the alternative standard attribute. If the attribute is not present, the alternative standard
        attribute is used. If None (default), no alternative standard attribute is defined.
    position: int, optional=None
        The position of the attribute. None puts it at the end.
    return_type: str, optional=None
        The return type of the method. If None (default), the return type is the one naturally return by the
        toolbox
    requirements: List[str] = None,
        The requirements for the attribute. Values are other standard names used in the convention.
        If None (default), no requirements are defined.

    Attributes
    ----------
    name: str
        The name of the attribute
    validator: StandardAttributeValidator
        The validator for the attribute
    target_methods: str | List[str]
        The method to which the attribute belongs. If the standard attribute is positional for all methods to
        which it applies, pass a list of strings, e.g. target_methods=["create_group", "create_dataset"].
        If it is positional and is only valid for one method, pass a string, e.g. target_methods="create_group".
    description: str
        The description of the attribute
    default_value: any, optional=DefaultValue.EMPTY
        If the attribute is positional, it has no default value, then pass DefaultValue.EMPTY (the default).
        Otherwise, pass the default value. The default value applies to all methods to which the attribute applies.
    alternative_standard_attribute; str, optional=None
        The name of the alternative standard attribute. If the attribute is not present, the alternative standard
        attribute is used. If None (default), no alternative standard attribute is defined.
    position: int, optional=None
        The position of the attribute. None puts it at the end.
    return_type: str, optional=None
        The return type of the method. If None (default), the return type is the one naturally return by the
        toolbox
    requirements: List[str] = None,
        The requirements for the attribute. Values are other standard names used in the convention.
        If None (default), no requirements are defined.
    target_cls: h5py.File | h5py.Group | h5py.Dataset
        The class to which the attribute belongs. This is set automatically.



    """
    EMPTY = DefaultValue.EMPTY  # quasi positional
    NONE = DefaultValue.NONE  # keyword argument is None. None will not be written to the file

    METHOD_CLS_ASSIGNMENT = {'__init__': File,
                             'create_group': Group,
                             'create_dataset': Group,
                             'create_string_dataset': Group}
    PROPERTY_CLS_ASSIGNMENT = {'__init__': File,
                               'create_group': Group,
                               'create_dataset': Dataset,
                               'create_string_dataset': Dataset}

    def __init__(self,
                 name,
                 validator,
                 target_methods: Union[str, Tuple[str], Tuple[str, str], Tuple[str, str, str]],
                 description,
                 default_value=DefaultValue.EMPTY,
                 alternative_standard_attribute: str = None,
                 position: Union[None, Dict[str, str]] = None,
                 return_type: str = None,
                 requirements: List[str] = None,
                 **kwargs):
        if isinstance(requirements, str):
            requirements = [requirements]
        self.requirements = requirements
        self.alternative_standard_attribute = alternative_standard_attribute
        if isinstance(default_value, str):
            _default_value = default_value.lower()
            if _default_value == '$none':
                default_value = self.NONE
            elif _default_value == '$empty':
                default_value = self.EMPTY
            elif _default_value == 'none':
                default_value = None

        if alternative_standard_attribute is not None and default_value is self.EMPTY:
            # an alternative standard name is given but no default value. Set default value to the alternative
            default_value = self.EMPTY
        self.default_value = default_value

        self.input_type = 'str'
        self.name = name  # the attrs key
        if isinstance(validator, str):
            validator = {validator: None}

        self.validator = get_validator(**validator)
        assert isinstance(self.validator, list)
        assert isinstance(self.validator[0], StandardAttributeValidator)

        if not isinstance(target_methods, (str, Tuple, List)):
            raise TypeError(f'The parameter "target_methods" for standard attribute "{name}" '
                            'must be a string or a tuple of strings, not '
                            f'{type(target_methods)}')

        if isinstance(target_methods, str):
            target_methods = (target_methods,)
        else:
            target_methods = tuple(target_methods)

        for tm in target_methods:
            if tm not in ('create_dataset', 'create_group', '__init__'):
                raise ValueError("Expected on of these methods: 'create_dataset', 'create_group', '__init__' but "
                                 f"found {tm}")

        self.target_methods = target_methods
        self.target_cls = tuple([self.PROPERTY_CLS_ASSIGNMENT[tm] for tm in target_methods])
        self.description = description
        self.position = position
        if return_type is None:
            return_type = None
        else:
            if return_type not in known_types:
                raise ValueError(f'Unknown return type: {return_type}')
        self.return_type = return_type
        for k in kwargs:
            logger.error(f'Unexpected entry "{k}" for StandardAttribute, which is ignored.')

    def __repr__(self):
        if self.is_positional():
            return f'<PositionalStdAttr("{self.name}"): "{self.description}">'
        return f'<KeywordStdAttr("{self.name}"): default_value="{self.default_value}" | "{self.description}">'

    def is_positional(self):
        """has no default value"""
        return self.default_value == DefaultValue.EMPTY

    def set(self, parent, value):
        # first call the validator on the value:
        try:
            for validator in self.validator:
                if value is None:
                    if validator.allow_None:
                        validated_value = validator(value, parent)
                    else:
                        # None is passed. this is ignored
                        return
                else:
                    validated_value = validator(value, parent)

        except Exception as e:
            if get_config('ignore_standard_attribute_errors'):
                logger.warning(f'Setting "{value}" for standard attribute "{self.name}" failed. '
                               f'Original error: {e}')
                validated_value = value
            else:
                raise errors.StandardAttributeError(f'Setting "{value}" for standard attribute "{self.name}" failed. '
                                                    f'Original error: {e}') from e
        super(type(parent.attrs), parent.attrs).__setitem__(self.name, validated_value)

    def get(self, parent):
        try:
            ret_val = super(type(parent.attrs), parent.attrs).__getitem__(self.name)
        except KeyError:
            ret_val = self.default_value
        if self.return_type is None:
            return WrapperAttributeManager._parse_return_value(parent._id, ret_val)
        return known_types[self.return_type](ret_val)


known_types = {'int': int,
               'float': float,
               'str': str,
               'bool': bool,
               'list': list,
               'tuple': tuple,
               'dict': dict,
               'pint.Quantity': _pint_quantity,
               'pint.Unit': _pint_unit,
               'sdict': make_dict,
               'standard_name_table': _standard_name_table,
               'isodatetime': _isodatetime}
