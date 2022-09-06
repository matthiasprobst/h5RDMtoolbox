from ..accessory import register_special_property

from ..h5file import H5Dataset, H5Group


@register_special_property(H5Group)
class standard_name:
    def set(self, new_standard_name):
        raise RuntimeError('A standard name attribute is used for datasets only')


@register_special_property(H5Dataset)
class standard_name:
    """Standard Name attribute"""

    def set(self, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            if self.standard_name_table.check_name(new_standard_name):
                if 'units' in self.attrs:
                    self.standard_name_table.check_units(new_standard_name,
                                                         self.attrs['units'])
                self.attrs.create('standard_name', new_standard_name)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        val = self.attrs.get('standard_name', None)
        if val is None:
            return None
        return self.standard_name_table[val]

    def delete(self):
        """Delete attribute"""
        self.attrs.__delitem__('standard_name')
