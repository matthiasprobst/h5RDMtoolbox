import pint
import re
import warnings
from typing import Union, Dict

from h5rdmtoolbox import get_ureg
from .errors import StandardNameError

VALID_CHARACTERS = '[^a-zA-Z0-9_]'
PATTERN = '^[0-9 ].*'


def _units_power_fix(_str: str):
    """Fixes strings like 'm s-1' to 'm s^-1'"""
    s = re.search('[a-zA-Z][+|-]', _str)
    if s:
        return _str[0:s.span()[0] + 1] + '^' + _str[s.span()[1] - 1:]
    return _str


class StandardName:
    """Standard Name class"""

    def __init__(self, name: str,
                 units: Union[str, pint.Unit] = None,
                 description: str = None,
                 canonical_units: str = None,
                 alias: str = None):
        StandardName.check_syntax(name)
        self.name = name
        if canonical_units is not None:
            warnings.warn('Parameter "canonical_units" is depreciated. Use "units" instead.', DeprecationWarning)
            units = canonical_units
        if description is None:
            # TODO if canonical_units is removed, then default value None must be removed for description, too
            raise ValueError('A description must be provided')
        if isinstance(units, str):
            self.units = get_ureg().Unit(_units_power_fix(units))
        elif isinstance(units, pint.Unit):
            self.units = units
        else:
            raise TypeError(f"units must be a str or a pint.Unit, not {type(units)}")
        # convert units to base units:
        q = 1 * self.units
        self.unit = q.to_base_units().units
        self.description = description
        if alias is not None:
            self.check_syntax(alias)
        self.alias = alias

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<StandardName: "{self.name}" units="{self.units}", description="{self.description}">'

    def equal_unit(self, other_unit: pint):
        """compares the base units of this standard name with another unit provided as a string
        or pint.Unit"""
        from ..utils import equal_base_units
        return equal_base_units(self.units, other_unit)

    @staticmethod
    def check_syntax(standard_name: str):
        """formal check of the syntax"""
        if not isinstance(standard_name, str):
            raise TypeError(f'Standard name must be type string but is {type(standard_name)}')
        if len(standard_name) == 0:
            raise StandardNameError('Name too short!')
        if re.sub(VALID_CHARACTERS, '', standard_name) != standard_name:
            raise StandardNameError('Invalid special characters in name '
                                    f'"{standard_name}": Only "{VALID_CHARACTERS}" '
                                    'is allowed.')

        if PATTERN != '' and PATTERN is not None:
            if re.match(PATTERN, standard_name):
                raise StandardNameError(f'Standard name "{standard_name}" does not match pattern "{PATTERN}"')

    def to_dict(self) -> Dict:
        """Return dictionary representation of StandardName"""
        return dict(name=self.name, units=self.units, description=self.description)
