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


class ScaleError(Exception):
    """Scale Error"""


class ScaleAttribute(StandardAttribute):
    """Units attribute"""

    name = 'scale'

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        scale = super().get()
        if scale is None:
            return None
        return ureg.Quantity(scale)

    def set(self, scale: Union[str, pint.Quantity]):
        """Set scale"""
        if not scale:
            return None

        if isinstance(scale, str):
            try:
                _scale = ureg.Quantity('scale')
            except (pint.UndefinedUnitError, ValueError) as e:
                raise ScaleError(f'Invalid scale. Orig error: {e}')
        elif isinstance(scale, pint.Quantity):
            _scale = scale
        else:
            raise ScaleError(f'Unit must be a string or pint.Unit but not {type(scale)}')

        self.parent.attrs.create(self.name, str(_scale))


class OffsetError(Exception):
    """Offset Error"""


class OffsetAttribute(StandardAttribute):
    """Units attribute"""

    name = 'offset'

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        offset = super().get()
        if offset is None:
            return None
        return float(offset)

    def set(self, offset: Union[float, int]):
        """Set scale"""
        if not offset:
            return None
        if not isinstance(offset, (float, int)):
            raise OffsetError(f'Offset must be a float or int but not {type(offset)}')
        self.parent.attrs.create(self.name, float(offset))
