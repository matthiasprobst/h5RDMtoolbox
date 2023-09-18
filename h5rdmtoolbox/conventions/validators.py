import abc
import json
from typing import Dict

_type_translation = (
    [('str', '$str', 'string'), str],
    [('int', '$int', 'integer'), int],
    [('float', '$float', 'float'), float],
    [('list', '$list'), list],
)


# def _eval_type(t):
#     if isinstance(t, str):
#         for _stype, _type in _type_translation:
#             if t in _stype:
#                 return _type
#     else:
#         return t
#     raise KeyError(f'Could not process {t}')


class StandardAttributeValidator:
    """Abstract Validator class of Standard Name Attribute classes"""

    keyword = None
    alternative_keywords = []

    def __init__(self, ref=None):
        self.ref = ref
        if self.keyword is None:
            raise ValueError('The keyword attribute must be set')

    @abc.abstractmethod
    def __call__(self, value, parent=None, attrs: Dict = None):
        """validate the value by raising an error if it is not valid or
        return the value you got in case it is valid"""
        pass

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.keyword}" ref="{self.ref}">'

    @abc.abstractmethod
    def get(self, value, parent):
        """Read HDF5 attribute, process and return it. The user should overwrite this method
        in order to return a different data type"""
        return value


# class NoneValidator(StandardAttributeValidator):
#     """Just returns the value without any validation"""
#
#     keyword = '$none'
#
#     def __call__(self, value, parent, attrs: Dict = None):
#         return value
#
#
# class DateTimeValidator(StandardAttributeValidator):
#     keyword = '$datetime'
#
#     def __call__(self, value, parent, attrs: Dict = None):
#         if isinstance(value, str):
#             datetime.fromisoformat(value)
#             return value
#         if not isinstance(value, datetime):
#             raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {datetime}')
#         return str(value.isoformat())
#
#     def get(self, value, parent) -> datetime:
#         """Return datetime object in iso format"""
#         return datetime.fromisoformat(value)
#
#
# class TypeValidator(StandardAttributeValidator):
#     """Validates the data type of the attribute"""
#
#     keyword = '$type'
#
#     def __init__(self, types):
#         if not isinstance(types, (list, tuple)):
#             super().__init__((types,))
#         else:
#             super().__init__(types)
#
#     def __call__(self, value, parent, attrs: Dict = None):
#         if not any(isinstance(value, _eval_type(t)) for t in self.ref):
#             raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {self.ref}')
#         return value
#
#
# class InValidator(StandardAttributeValidator):
#     """Validates if the attribute value is in the list of expected values.
#     During definition, the list of expected values is passed as a list of strings,
#     see the example usage below, where the validator is used in the standard
#     attribute "data_source"
#
#     Parameters
#     ----------
#     expectation: List[str]
#         List of expected values
#
#     Example
#     -------
#     >>> import h5rdmtoolbox as h5tbx
#     >>> data_source = h5tbx.conventions.StandardAttribute(
#     >>>         name='units',
#     >>>         validator={'$in': ['numerical', 'experimental', 'analytical']},
#     >>>         method='__init__'
#     >>>         description='The source of data'
#     >>>     )
#     """
#
#     keyword = '$in'
#
#     def __init__(self, expectation: List[str]):
#         if not isinstance(expectation, (tuple, list)):
#             raise TypeError(f'Invalid type for parameter "expectation": {type(expectation)}')
#
#         super().__init__(expectation)
#
#     def __call__(self, value, parent, attrs: Dict = None):
#         if value not in self.ref:
#             raise ValueError(f'The value "{value}" is not in {self.ref}. '
#                              f'Expecting one of these: {self.ref}')
#         return value
#
#
# class ORCIDValidator(StandardAttributeValidator):
#     """Validator class, that validates ORCIDs. If an internet
#     connection exists, the url is checked, otherwise and if previously
#     validated, the ORCID is locally validated."""
#
#     keyword = '$orcid'
#
#     def __call__(self, orcid, parent=None, attrs: Dict = None) -> Union[str, List[str]]:
#         if not isinstance(orcid, (list, tuple)):
#             orcid = [orcid, ]
#         for o in orcid:
#             if not isinstance(o, str):
#                 raise TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')
#
#             _orcid = ORCID(o)
#             if not _orcid.exists():
#                 raise ValueError(f'Not an ORCID ID: {o}')
#         return orcid
#
#
# class PintQuantityValidator(StandardAttributeValidator):
#     keyword = '$quantity'
#     alternative_keywords = ('$pintquantity',)
#
#     def __call__(self, quantity, parent=None, attrs=None) -> str:
#         """write to attribute"""
#         try:
#             get_ureg().Quantity(quantity)
#         except (pint.UndefinedUnitError, TypeError) as e:
#             raise ValueError(f'Quantity cannot be understood using ureg package: {quantity}. Original error: {e}')
#         return str(quantity)  # convert to string, otherwise error!
#
#     def get(self, value, parent) -> pint.Quantity:
#         return get_ureg().Quantity(value)
#
#
# class OffsetValidator(PintQuantityValidator):
#     keyword = '$offset'
#     alternative_keywords = ()
#
#     def __call__(self, offset: str, parent=None, attrs=None) -> str:
#         qoffset = get_ureg().Quantity(super().__call__(offset, parent, attrs))
#
#         if attrs:
#             scale = attrs.get('scale', parent.attrs.get('scale', None))
#             ds_units = attrs.get('units', parent.attrs.get('units', None))
#         else:
#             scale = parent.attrs.get('scale', None)
#             ds_units = parent.attrs.get('units', None)
#
#         if scale is not None:
#             scale = get_ureg().Quantity(scale)
#
#         if ds_units is None:
#             if scale is None:
#                 # dataset has no units and no scale given, thus offset must be dimensionless
#                 if qoffset.dimensionality != pint.dimensionless.dimensionality:
#                     raise ValueError(f'Offset must be dimensionless if no units are given. '
#                                      f'Got: {qoffset.dimensionality}')
#             else:
#                 # scale is given but dataset is dimensionless, scale and offset must have same units
#                 if qoffset.dimensionality != scale.dimensionality:
#                     raise ValueError(f'Offset and scale must have same units if dataset is dimensionless. '
#                                      f'Got: {qoffset.dimensionality} and {scale.dimensionality}')
#         else:
#             ds_units = get_ureg().Unit(ds_units)
#             # dataset has units, offset must either have units of dataset or product of scale and dataset
#             from .utils import equal_base_units
#             if scale is None:
#                 resulting_units = ds_units
#             else:
#                 resulting_units = get_ureg().Unit(f'{ds_units} {scale.units}')
#             if not equal_base_units(qoffset.units, ds_units) and not equal_base_units(qoffset.units, resulting_units):
#                 raise ValueError(f'Offset must have same units as dataset or product of scale and dataset. '
#                                  f'Got: {qoffset.units} and {ds_units}')
#         return str(qoffset)
#
#
# class PintUnitsValidator(StandardAttributeValidator):
#     keyword = '$units'
#     alternative_keywords = ('$pintunits', '$pintunit', '$unit',)
#
#     def __call__(self, value, parent=None, attrs: Dict = None) -> str:
#         try:
#             get_ureg().Unit(value)
#         except (pint.UndefinedUnitError, TypeError) as e:
#             raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')
#         return str(value)
#
#     def get(self, value, parent) -> pint.Unit:
#         return get_ureg().Unit(value)


def _loads_if_needed(value):
    if isinstance(value, str) and value[0] == '{':
        return json.loads(value)
    return value


def _parse_dict(value):
    """Returns a string representation of a dict if value is a dict else passes value through"""
    if isinstance(value, dict):
        return json.dumps(value)
    return value
