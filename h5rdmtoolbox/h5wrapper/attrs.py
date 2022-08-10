from h5rdmtoolbox.h5wrapper.h5file import H5Group, H5Dataset
from .accessory import register_special_property
from ..conventions import LongName


@register_special_property(H5Group)
@register_special_property(H5Dataset)
class long_name:

    def set(self, value):
        ln = LongName(value)  # runs check automatically during initialization
        self.attrs['long_name'] = ln

    def get(self):
        return self.attrs.get('long_name', None)

    def delete(self):
        del self.attrs['long_name']


@register_special_property(H5Group)
class standard_name:
    def set(self, new_standard_name):
        raise RuntimeError('A standard name attribute is used for datasets only')


@register_special_property(H5Dataset)
class standard_name:

    def set(self, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            if self.standard_name_table.check_name(new_standard_name):
                self.attrs['standard_name'] = new_standard_name

    def get(self):
        """Returns the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        val = self.attrs.get('standard_name', None)
        if val is None:
            return None
        return self.standard_name_table[val]

    def delete(self):
        del self.attrs['standard_name']

# import abc
# import re
#
# import h5py
#
#
# class StandardizedAttribute(str, abc.ABC):
#     """Abstract class for standardized attributes"""
#     TYPE_LIMITATION = None
#
#     @staticmethod
#     @abc.abstractmethod
#     def check(value) -> bool:
#         """Run check or raise Error"""
#         return True
#
#     def __new__(cls, value):
#         cls.check(value)
#         return str.__new__(cls, value)
#
#
# class LongName(StandardizedAttribute):
#     """Long Name"""
#     MIN_LENGTH = 1
#     PATTERN = ('^[0-9 ].*', 'Name must not start with a number or a space')
#     TYPE_LIMITATION = (h5py.Group, h5py.File)
#
#     @staticmethod
#     def check(value) -> bool:
#         """Run check or raise Error"""
#         # 1. Must be longer than MIN_LENGTH
#         if len(value) < LongName.MIN_LENGTH:
#             raise ValueError(f'Name is too short. Must at least have {LongName.MIN_LENGTH} character')
#         # if value[0] == ' ':
#         #     raise ValueError(f'Name must not start with a space')
#         if re.match(LongName.PATTERN[0], value):
#             raise ValueError(LongName.PATTERN[1])
#         return True
#
#
# from typing import Union
# from ..conventions.identifier import _NameIdentifierConvention
#
#
# @dataclass
# class StandardName(StandardizedAttribute):
#     description: Union[str, None]
#     canonical_units: Union[str, None]
#     convention: _NameIdentifierConvention
#
#     def __init__(self, name: str, parent: Union[h5py.Group, h5py.Dataset]):
#         self._name = name
#         self._parent = parent
#
#     def __str__(self):
#         return self.name
