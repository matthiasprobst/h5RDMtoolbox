import pint
from typing import Union

from .standard_attribute import StandardAttribute
from .._config import ureg


class UnitsError(Exception):
    """Units Error"""


class UnitsAttribute(StandardAttribute):
    """Units attribute"""

    name = 'units'

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        units = super().get()
        if units is None:
            return None
        return f'{ureg.Unit(units)}'

    def set(self, units: Union[str, pint.Unit]):
        """Set units"""
        if units:
            if isinstance(units, str):
                _units = f'{ureg.Unit(units)}'
            elif isinstance(units, pint.Unit):
                _units = f'{units}'
            else:
                raise UnitsError(f'Unit must be a string or pint.Unit but not {type(units)}')
        else:
            _units = units
        standard_name = super().get(name='standard_name')
        if standard_name:
            if not self.parent.standard_name_table.check_units(standard_name, _units):
                raise UnitsError(f'Units "{_units}" are not compatible with standard_name "{standard_name}"')
        self.parent.attrs.create(self.name, _units)
