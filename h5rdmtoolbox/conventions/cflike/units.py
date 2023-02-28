import pint
from typing import Union

from ... import config
from .errors import UnitsError


class UnitsAttribute:
    """Units attribute"""

    def set(self, new_units: Union[str, pint.Unit]):
        """Sets the attribute units to attribute 'units'
        default unit registry format of pint is used."""
        if new_units:
            if isinstance(new_units, str):
                _new_units = f'{config.ureg.Unit(new_units)}'
            elif isinstance(new_units, pint.Unit):
                _new_units = f'{new_units}'
            else:
                raise UnitsError(f'Unit must be a string or pint.Unit but not {type(new_units)}')
        else:
            _new_units = new_units
        standard_name = self.attrs.get('standard_name')
        if standard_name:
            self.standard_name_table.check_units(standard_name, _new_units)

        self.attrs.create('units', _new_units)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        return self.attrs.get('units', None)

    def delete(self):
        """Delete attribute units"""
        self.attrs.__delitem__('units')
