"""standard attribute module"""
import abc
import json
import numpy as np
import pathlib
import warnings
from typing import Dict, List

from . import errors
from .validators import StandardAttributeValidator
from .validators.core import TypeValidator, InValidator
from .validators.orcid import ORCIDValidator
from .validators.pint import PintQuantityValidator, PintUnitsValidator
from .validators.references import ReferencesValidator, BibTeXValidator, URLValidator
from .validators.standard_name import StandardNameValidator, StandardNameTableValidator, StandardName, StandardNameTable
from .validators.strings import RegexValidator, MinLengthValidator, MaxLengthValidator
from ... import get_ureg
from ...wrapper.h5attr import WrapperAttributeManager

__all__ = ['StandardName', 'StandardNameTable']


def _pint_quantity(q):
    return get_ureg()(q)


def _pint_unit(u):
    return get_ureg().Unit(u)


def _standard_name_table(snt):
    if isinstance(snt, dict):
        return StandardNameTable.from_yaml(snt)
    elif isinstance(snt, str):
        if snt.startswith('{'):
            return StandardNameTable(**json.loads(snt))
        if snt.startswith('https://zenodo.org/record/'):
            return StandardNameTable.from_zenodo(doir=snt)
        if snt.startswith('https://'):
            return StandardNameTable.from_url(snt)
        if pathlib.Path(snt).exists():
            return StandardNameTable.from_yaml(snt)
    raise TypeError(f'Unexpected type for the standard name table: {type(snt)}')


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


def get_validator(**validator: Dict) -> List[StandardNameValidator]:
    """return the respective StandardAttributeValidator

    validator_identifier: str:
        E.g. $regex, $orcid, $in, $standard_name, $standard_name_unit
    """
    for name, value in validator.items():
        if name not in av_validators:
            raise ValueError(f'No validator class found for "{name}"')
    return [av_validators[name](value) for name, value in validator.items()]


class StandardAttribute(abc.ABC):
    """StandardAttribute class for the standardized attributes"""

    def __init__(self, name, validator, method, description,
                 optional=False, default_value=None,
                 position=None,
                 return_type: str = None,
                 requirements: List[str] = None,
                 dependencies: List[str] = None,
                 **kwargs):
        if isinstance(requirements, str):
            requirements = [requirements]
        self.requirements = requirements
        self.name = name  # the attrs key
        if isinstance(validator, str):
            validator = {validator: None}
        self.validator = get_validator(**validator)
        assert isinstance(self.validator, list)
        assert isinstance(self.validator[0], StandardAttributeValidator)
        self.method = method
        self.description = description
        self.optional = optional
        self.default_value = default_value
        self.position = position
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies
        if return_type is None:
            return_type = None
        else:
            if return_type not in known_types:
                raise ValueError(f'Unknown return type: {return_type}')
        self.return_type = return_type
        for k in kwargs.keys():
            warnings.warn(f'Ignoring parameter "{k}"', UserWarning)

    def __repr__(self):
        return f'<StdAttr("{self.name}"): "{self.description}">'

    def set(self, parent, value):
        # first call the validator on the value:
        try:
            for validator in self.validator:
                validated_value = validator(value, parent)
        except Exception as e:
            raise errors.StandardAttributeError(f'The attribute "{self.name}" is standardized. '
                                                f'It seems, that the input "{value}" is not valid. '
                                                f'Here is the description of the standard attribute, '
                                                f'which may help to find the issue: "{self.description}" '
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


# class RegexStandardAttribute(StandardAttribute):
#
#     def select_validator(self, validator):
#         if isinstance(validator, dict):
#             validator = get_validator(**validator)
#         elif isinstance(validator, StandardAttributeValidator):
#             pass
#         else:
#             raise TypeError(f'Unexpected type for the validator: {type(validator)}')
#         assert validator is not None
#         return validator


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
               'standard_name_table': _standard_name_table}

av_validators = {'$type': TypeValidator,
                 '$in': InValidator,
                 '$regex': RegexValidator,
                 '$pintunit': PintUnitsValidator,
                 '$pintquantity': PintQuantityValidator,
                 '$orcid': ORCIDValidator,
                 '$url': URLValidator,
                 '$ref': ReferencesValidator,
                 '$bibtex': BibTeXValidator,
                 '$standard_name': StandardNameValidator,
                 '$standard_name_table': StandardNameTableValidator,
                 '$minlength': MinLengthValidator,
                 '$maxlength': MaxLengthValidator,
                 }
