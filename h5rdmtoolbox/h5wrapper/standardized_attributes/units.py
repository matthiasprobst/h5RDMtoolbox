import pint
from pint_xarray import unit_registry as ureg

from ..accessory import register_special_property
from ..h5file import H5Dataset
from ... import config

ureg.default_format = config.ureg_format


@register_special_property(H5Dataset)
class units:

    def set(self, units):
        """Sets the attribute units to attribute 'units'
        default unit registry format of pint is used."""
        if units:
            if isinstance(units, str):
                _units = ureg.Unit(units).__format__(ureg.default_format)
            elif isinstance(units, pint.Unit):
                _units = units.__format__(ureg.default_format)
            else:
                raise TypeError(f'Unit must be a string or pint.Unit but not {type(units)}')
        else:
            _units = units
        standard_name = self.attrs.get('standard_name')
        if standard_name:
            self.standard_name_table.check_units(standard_name, _units)

        self.attrs.create('units', _units)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        return self.attrs.get('units', None)

    def delete(self):
        self.attrs.__delitem__('units')
