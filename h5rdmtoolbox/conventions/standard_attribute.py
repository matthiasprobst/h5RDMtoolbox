"""standard attribute module"""
import abc
import warnings
from typing import Dict

from .validators import RegexValidator, ORCIDValidator, PintUnitsValidator, PintQuantityValidator, ReferencesValidator
from .validators.base import StandardAttributeValidator
from .. import get_ureg


def _pint_quantity(q):
    return get_ureg()(q)


def _pint_unit(u):
    return get_ureg().Unit(u)


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
                 '$url': ReferencesValidator}


def get_validator(**validator: Dict):
    """return the respective StandardAttributeValidator

    validator_identifier: str:
        E.g. $regex, $orcid, $in, $standard_name, $standard_name_unit
    """
    assert len(validator) == 1
    name, value = tuple(validator.items())[0]
    if name in av_validators:
        return av_validators[name](value)
    raise ValueError(f'No validator class found for "{name}"')


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
        assert isinstance(self.validator, StandardAttributeValidator)
        self.method = method
        self.description = description
        self.optional = optional
        self.default_value = default_value
        self.position = position
        if return_type is None:
            return_type = 'str'
        if return_type not in known_types:
            raise ValueError(f'Unknown return type: {return_type}')
        self.return_type = return_type
        for k in kwargs.keys():
            warnings.warn(f'Ignoring parameter {k}', UserWarning)

    def __repr__(self):
        return f'<StdAttr("{self.name}"): "{self.description}">'

    def set(self, parent, value):
        # first call the validator on the value:
        if not self.validator(value, parent):
            raise StandardAttributeError(f'The attribute "{self.name}" is standardized. '
                                         f'It seems, that the input "{value}" is not valid. '
                                         f'Here is the description of the standard attribute, '
                                         f'which may help to find the issue: "{self.description}"')
        super(type(parent.attrs), parent.attrs).__setitem__(self.name, value)

    def get(self, parent):
        try:
            ret_val = super(type(parent.attrs), parent.attrs).__getitem__(self.name)
        except KeyError:
            ret_val = self.default_value
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
