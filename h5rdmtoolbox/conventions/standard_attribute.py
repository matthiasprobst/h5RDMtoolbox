"""standard attribute module"""
import abc
import warnings
from typing import Dict, List

from .validators import (RegexValidator,
                         ORCIDValidator,
                         PintUnitsValidator,
                         PintQuantityValidator,
                         ReferencesValidator,
                         BibTeXValidator,
                         URLValidator,
                         MinLengthValidator,
                         MaxLengthValidator)
from .validators.base import StandardAttributeValidator
from .. import get_ureg
from ..wrapper.h5attr import WrapperAttributeManager


def _pint_quantity(q):
    return get_ureg()(q)


def _pint_unit(u):
    return get_ureg().Unit(u)


class StandardNameValidator(StandardAttributeValidator):
    def __call__(self, standard_name, parent, **kwargs):
        snt = parent.rootparent.attrs.get('standard_name_table', None)
        if snt.startswith('https://zenodo.org/record/'):
            from .tbx.table import StandardNameTable
            snt = StandardNameTable.from_zenodo(doi=snt.split('https://zenodo.org/record/')[1].strip('/'))
        else:
            raise NotImplementedError('Only Zenodo is supported at the moment')

        if snt is None:
            raise KeyError('No standard name table defined for this file!')

        units = parent.attrs.get('units', None)
        if units is None:
            raise KeyError('No units defined for this variable!')

        if not snt.check(standard_name, units):
            raise ValueError(f'Standard name {standard_name} with units {units} is invalid')
        return standard_name


class StandardNameTableValidator(StandardAttributeValidator):
    def __call__(self, standard_name_table, *args, **kwargs):
        # from .tbx.table import StandardNameTable
        # if standard_name_table.startswith('https://zenodo.org/record/'):
        #     standard_name_table = StandardNameTable.from_zenodo(standard_name_table)
        # else:
        #     raise NotImplementedError('Only Zenodo is supported at the moment')
        return standard_name_table


known_types = {'int': int,
               'float': float,
               'str': str,
               'bool': bool,
               'list': list,
               'tuple': tuple,
               'dict': dict,
               'pint.Quantity': _pint_quantity,
               'pint.Unit': _pint_unit}

av_validators = {'$regex': RegexValidator,
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


def get_validator(**validator: Dict) -> List[StandardNameValidator]:
    """return the respective StandardAttributeValidator

    validator_identifier: str:
        E.g. $regex, $orcid, $in, $standard_name, $standard_name_unit
    """
    for name, value in validator.items():
        if name not in av_validators:
            raise ValueError(f'No validator class found for "{name}"')
    return [av_validators[name](value) for name, value in validator.items()]


class StandardAttributeError(Exception):
    pass


class StandardAttribute(abc.ABC):

    def __init__(self, name, validator, method, description,
                 optional=False, default_value=None,
                 position=None,
                 return_type: str = None,
                 **kwargs):
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
        if return_type is None:
            return_type = None
        else:
            if return_type not in known_types:
                raise ValueError(f'Unknown return type: {return_type}')
        self.return_type = return_type
        for k in kwargs.keys():
            warnings.warn(f'Ignoring parameter {k}', UserWarning)

    def __repr__(self):
        return f'<StdAttr("{self.name}"): "{self.description}">'

    def set(self, parent, value):
        # first call the validator on the value:
        try:
            for validator in self.validator:
                validated_value = validator(value, parent)
        except Exception as e:
            raise StandardAttributeError(f'The attribute "{self.name}" is standardized. '
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
