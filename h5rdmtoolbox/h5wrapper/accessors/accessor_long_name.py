from typing import Union

from ..accessory import register_special_property
from ..h5file import H5Dataset, H5Group
from ...conventions import LongName


@register_special_property(H5Group)
@register_special_property(H5Dataset)
class long_name:
    """Long name attribute"""

    def set(self, value):
        """Set the long_name"""
        ln = LongName(value)  # runs check automatically during initialization
        self.attrs.create('long_name', ln.__str__())

    def get(self) -> Union[str, None]:
        """Get the long_name"""
        return self.attrs.get('long_name', None)

    def delete(self):
        """Delete the long_name"""
        self.attrs.__delitem__('long_name')
