"""general validation functions of the toolbox usable by convention. If users wish to user
their own validators, they need to define them separately. The respective python script then
must be provided during initialization of a Convention"""
import re
from typing import Union, Dict

import pint
import typing_extensions
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

from h5rdmtoolbox import get_ureg
from h5rdmtoolbox import identifiers


def __verify_version(version, handler, info) -> str:
    """Verify that version is a valid as defined in https://semver.org/"""
    re_pattern = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    if re.match(pattern=re_pattern, string=version) is not None:
        return version
    raise ValueError(f'Version {version} is not valid!')


def __validate_orcid(value, handler, info):
    if not isinstance(value, str):
        raise TypeError(f'Expected a string but got {type(value)}')
    orcid = identifiers.ORCID(value)
    if not orcid.validate():
        raise ValueError(f'ORCID {value} is not valid!')
    return orcid


def __validate_identifier(value, handler, info) -> Union[None, identifiers.ObjectIdentifier]:
    if not isinstance(value, str):
        raise TypeError(f'Expected a string but got "{type(value)}"')
    ident = identifiers.from_url(value)
    if ident:
        if not ident.validate():
            raise ValueError(f'Identifier "{value}" is not valid!')
    else:
        raise ValueError(f'Identifier "{value}" is not valid!')
    return ident


def __validate_url(value, handler, info):
    from h5rdmtoolbox.convention.references import validate_url
    if not isinstance(value, (list, tuple)):
        references = [value, ]
    else:
        references = value

    for r in references:
        if not isinstance(r, str):
            raise TypeError(f'Expected a string but got {type(r)}')

    if all(validate_url(r) for r in references):
        if len(references) == 1:
            return references[0]
        return references
    raise ValueError(f'Invalid URL: {references}')


def __validate_quantity(value, handler, info):
    if isinstance(value, pint.Quantity):
        return value
    try:
        return get_ureg().Quantity(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Quantity cannot be understood using ureg package: {value}. Original error: {e}')


def __validate_units(value, handler, info):
    """validate units using pint package"""
    if isinstance(value, (int, float)):
        raise TypeError(f'Expected a string but got {type(value)}')
    try:
        return get_ureg().Unit(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')


# def __validate_scale(value, handler, info):
#     if not info.context:
#         raise RuntimeError('Require context to validate offset!')
#     parent = info.context.get('parent', None)
#     if parent is None:
#         raise RuntimeError('Require parent dataset to validate offset!')
#     # attrs = info.context.get('attrs', None)
#
#     parent_group = info.context['parent'].parent
#
#     if isinstance(value, str) and value in parent_group:
#         return parent_group[value][()]
#
#     raise KeyError(f'No dataset found with name {value}!')


# def __validate_offset_or_scale(value, handler, info):
#     if not info.context:
#         raise RuntimeError('Require context to validate offset!')
#     parent = info.context.get('parent', None)
#     if parent is None:
#         raise RuntimeError('Require parent dataset to validate offset!')
#
#     parent_group = info.context['parent'].parent
#
#     if isinstance(value, str):
#         if value.startswith('/'):
#             try:
#                 offset_or_scale_ds = parent.rootparent[value]
#             except KeyError:
#                 raise KeyError(f'No dataset found with name {value}!')
#         else:
#             try:
#                 offset_or_scale_ds = parent_group[value]
#             except KeyError:
#                 raise KeyError(f'No dataset found with name {value}!')
#     else:
#         raise TypeError(f'Offset dataset must be dataset name of dataset object, not {type(value)}')
#
#     assert offset_or_scale_ds.ndim == 0
#
#     offset_or_scale_ds_name = offset_or_scale_ds.name
#     return offset_or_scale_ds_name


def __validate_date_format(value, handler, info):
    """value: str, e.g. '1991-01-19T13:45:05TZD'"""
    import dateutil.parser
    import warnings
    # will raise an error if not a valid datetime
    try:
        warnings.filterwarnings("error")
        dt = dateutil.parser.parse(value)
    except TypeError as e:
        raise TypeError(f'Invalid datetime: {value}. Original error: {e}')
    finally:
        warnings.filterwarnings("ignore")
    return dt


unitsType = Annotated[str, WrapValidator(__validate_units)]

dateFormatType = Annotated[str, WrapValidator(__validate_date_format)]

quantityType = Annotated[str, WrapValidator(__validate_quantity)]

# dataOffsetType = Annotated[str, WrapValidator(__validate_offset_or_scale)]
#
# dataScaleType = Annotated[str, WrapValidator(__validate_offset_or_scale)]

orcidType = Annotated[str, WrapValidator(__validate_orcid)]

identifierType = Annotated[str, WrapValidator(__validate_identifier)]

urlType = Annotated[str, WrapValidator(__validate_url)]

versionType = Annotated[str, WrapValidator(__verify_version)]

validators = {
    'units': unitsType,
    'dateFormat': dateFormatType,
    'quantity': quantityType,
    # 'data_offset': dataOffsetType,
    # 'data_scale': dataScaleType,
    'orcid': orcidType,
    'identifier': identifierType,
    'url': urlType,
    'version': versionType
}


def get_list_of_validators() -> Dict[str, typing_extensions._AnnotatedAlias]:
    """Get a list of all available validators"""
    return validators
