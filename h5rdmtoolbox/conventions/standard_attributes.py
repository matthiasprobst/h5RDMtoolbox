"""standard attribute module"""
import abc
import enum
import json
import numpy as np
import pathlib
import warnings
from datetime import datetime
from typing import Dict, List, Union

from . import errors
from . import logger
from . import warnings as convention_warnings
from .consts import DefaultValue
from .validators import StandardAttributeValidator
from .validators import get_validator
from .. import get_ureg, get_config
from ..utils import DocStringParser
from ..wrapper.core import File, Group, Dataset

__doc_string_parser__ = {File: {'__init__': DocStringParser(File)},
                         Group: {'create_group': DocStringParser(Group.create_group),
                                 'create_dataset': DocStringParser(Group.create_dataset)}}

__all__ = ['StandardAttribute', ]


class TargetMethod(enum.Enum):
    """Available Target methods for Standard Attributes"""
    create_file = 1
    init = 1
    create_group = 2
    create_dataset = 3


def _pint_quantity(q, parent):
    return get_ureg()(q)


def _pint_unit(u, parent):
    return get_ureg().Unit(u)


def _standard_name_table(snt, parent):
    from .standard_names.table import StandardNameTable
    if isinstance(snt, dict):
        return StandardNameTable.from_yaml(snt)
    if not isinstance(snt, str):
        raise TypeError(f'Unexpected type for the standard name table: {type(snt)}')
    if snt.startswith('{'):
        return StandardNameTable.from_dict(json.loads(snt))
    if snt.startswith('https://zenodo.org/record/') or snt.startswith('10.5281/zenodo.'):
        return StandardNameTable.from_zenodo(doi=snt)
    if snt.startswith('https://'):
        return StandardNameTable.from_url(snt)
    if pathlib.Path(snt).exists():
        return StandardNameTable.from_yaml(snt)
    raise RuntimeError('Could not parse standard name table.')


def _standard_name(sn, parent):
    snt = parent.rootparent.standard_name_table
    return snt[sn]


def make_dict(ref, parent):
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


def _isodatetime(dt, parent):
    # expecting isoformat!
    return datetime.fromisoformat(dt)


def _orcid(orcid_id, parent):
    from .. import orcid
    return orcid.ORCID(orcid_id)


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

    VALID_TARGET_METHODS = ('__init__', 'create_group', 'create_dataset')
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
                 description,
                 default_value=DefaultValue.EMPTY,
                 target_method: str = None,
                 target_methods=None,
                 alternative_standard_attribute: str = None,
                 position: Union[None, Dict[str, str]] = None,
                 return_type: str = None,
                 requirements: List[str] = None,
                 **kwargs):
        """

        Parameters
        ----------
        name: str
            The name of the attribute. The name is cut if it includes "-" and only the first part is taken,
            e.g. "comment-file" will be "comment". This is needed to define multiple attributes in a YAML file
            with the same "basename" ("basename" refers to the part before the "-", thus "comment" in the example).
        validator
        description
        default_value
        target_method: str
            The method to which the attribute belongs. Only one method can be specified.

            Note: In earlier versions multiple methods could be specified. This is not supported anymore because (a)
            it facilitates the code and makes it better to read and (b) the description of the attribute should be
            different depending on the method.
        target_methods: str
            Deprecated. Use target_method instead.
        alternative_standard_attribute
        position
        return_type
        requirements
        kwargs
        """
        if isinstance(requirements, str):
            requirements = [requirements]
        self.requirements = requirements
        self.alternative_standard_attribute = alternative_standard_attribute
        if isinstance(default_value, str):
            _default_value = default_value.lower()
            if _default_value == '$none':
                default_value = DefaultValue.NONE
            elif _default_value == '$empty':
                default_value = DefaultValue.EMPTY
            elif _default_value == 'none':
                default_value = None
            else:
                default_value = DefaultValue(default_value)

        if alternative_standard_attribute is not None and default_value is self.EMPTY:
            # an alternative standard name is given but no default value. Set default value to the alternative
            default_value = DefaultValue.EMPTY
        self.default_value = default_value

        self.input_type = 'str'
        self.name = name.split('-', 1)[0]  # the attrs key

        if isinstance(validator, str):
            validator = {validator: None}

        if len(validator) > 1:
            raise ValueError(f'Only one validator can be specified. Got {validator} instead.')

        self.validator = [get_validator(k)(v) for k, v in validator.items()][0]

        assert isinstance(self.validator, StandardAttributeValidator)

        if target_method is None and target_methods is not None:
            warnings.warn('target_method is deprecated. Use target_methods instead.', DeprecationWarning)
            target_method = target_methods

        if not isinstance(target_method, str):
            raise TypeError(f'target_method must be a string. Got {type(target_method)} instead.')
        if target_method not in self.VALID_TARGET_METHODS:
            raise ValueError(f'Invalid target method: "{target_methods}".from '
                             f'Valid target methods are: {self.VALID_TARGET_METHODS}.')

        self.target_method = target_method

        self.target_cls = self.PROPERTY_CLS_ASSIGNMENT[target_method]
        if description[-1] != '.':
            description += '.'
        self.description = description

        self.position = position
        if return_type is None:
            if self.validator.keyword in known_types:
                return_type = self.validator.keyword
            else:
                return_type = None
        else:
            if return_type not in known_types:
                raise ValueError(f'Unknown return type: {return_type}')
        self.return_type = return_type
        for _k in kwargs:
            logger.error(f'Unexpected entry "{_k}" for StandardAttribute, which is ignored.')

    def __repr__(self):
        if self.is_positional():
            return f'<PositionalStdAttr("{self.name}"): "{self.description}">'
        return f'<KeywordStdAttr("{self.name}"): default_value="{self.default_value}" | "{self.description}">'

    @property
    def target_methods(self):
        warnings.warn('target_methods is deprecated. Use target_method instead.', DeprecationWarning)
        return self.target_method

    def is_positional(self):
        """has no default value"""
        return self.default_value == DefaultValue.EMPTY

    def make_optional(self):
        """make this standard attribute optional by setting the default value to Default.NONE"""
        self.default_value = DefaultValue.NONE
        # disable and enable the convention to make the change effective:
        import h5rdmtoolbox as h5tbx
        _cache_cv = h5tbx.conventions.get_current_convention()
        h5tbx.use(None)
        h5tbx.use(_cache_cv)

    def set(self, parent, value, attrs=None):
        """Write `value` to attribute of `parent`

        Parameters
        ----------
        parent: h5py.File, h5py.Group, h5py.Dataset
            The parent object to which the attribute is written
        value: any
            The value to write to the attribute. The value is validated before it is written.
        attrs: dict, optional=None
            Other attributes to be set. This is used during dataset creation only.
        """
        # first call the validator on the value:
        try:
            if value is None:
                if self.validator.allow_None:
                    validated_value = self.validator(value, parent, attrs)
                else:
                    # None is passed. this is ignored
                    return
            else:
                validated_value = self.validator(value, parent, attrs)
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
        """Read the attribute from `parent`

        Parameters
        ----------
        parent: h5py.File, h5py.Group, h5py.Dataset
            The parent object from which the attribute is read

        Returns
        -------
        any
            The value of the attribute. The validator has a get method that is called on the return
            The type of the return value is thus dependent the validator. If the get method is not
            implemented, the return value is the same as the value stored in the attribute.

        Raises
        ------
        KeyError
            If the attribute name does not exist

        StandardAttributeValidationWarning
            If the attribute could not be validated during reading. The raw value is returned though.
        """
        try:
            ret_val = super(type(parent.attrs), parent.attrs).__getitem__(self.name)
        except KeyError:
            ret_val = self.default_value
        # is there a return value associated with the validator?
        try:
            return self.validator.get(ret_val, parent)
        except Exception as e:
            warnings.warn(f'The attribute "{self.name}" could not be validated due to: {e}',
                          convention_warnings.StandardAttributeValidationWarning)
            return ret_val


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
               'isodatetime': _isodatetime,
               'orcid': _orcid,
               'standard_name': _standard_name,
               }
_known_types = known_types.copy()
for k, v in known_types.items():
    _known_types[f'${k}'] = v
known_types = _known_types
