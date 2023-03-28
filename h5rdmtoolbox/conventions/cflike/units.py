import pint
from typing import Union

from .errors import UnitsError
from ..registration import StandardAttribute
from ..._config import ureg


class UnitsAttribute(StandardAttribute):
    """Units attribute"""

    name = 'units'

    def setter(self, obj, new_units: Union[str, pint.Unit]):
        """Sets the attribute units to attribute 'units'
        default unit registry format of pint is used."""
        if new_units:
            if isinstance(new_units, str):
                _new_units = f'{ureg.Unit(new_units)}'
            elif isinstance(new_units, pint.Unit):
                _new_units = f'{new_units}'
            else:
                raise UnitsError(f'Unit must be a string or pint.Unit but not {type(new_units)}')
        else:
            _new_units = new_units
        standard_name = self.safe_attr_getter(obj, 'standard_name')
        if standard_name:
            if not obj.standard_name_table.check_units(standard_name, _new_units):
                raise UnitsError(f'Units "{_new_units}" are not compatible with standard_name "{standard_name}"')
        obj.attrs.create('units', _new_units)

    def getter(self, obj):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        units = self.safe_getter(obj)
        if units is None:
            return None
        return f'{ureg.Unit(units)}'
