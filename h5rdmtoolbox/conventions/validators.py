import abc
import json
import pint
import re
from datetime import datetime
from typing import List, Union

from h5rdmtoolbox.orcid import ORCID
from . import errors
from .references import validate_reference, validate_bibtex, validate_url
from .. import get_ureg

_type_translation = (
    [('str', '$str'), str],
    [('int', '$int'), int],
    [('float', '$float'), float],
    [('list', '$list'), list],
)


def _eval_type(t):
    if isinstance(t, str):
        for _stype, _type in _type_translation:
            if t in _stype:
                return _type
    else:
        return t
    raise KeyError(f'Could not process {t}')


class StandardAttributeValidator:
    """Abstract Validator class of Standard Name Attribute classes"""

    keyword = None

    def __init__(self, ref=None, allow_None: bool = False):
        self.ref = ref
        self.allow_None = allow_None
        if self.keyword is None:
            raise ValueError('The keyword attribute must be set')

    @abc.abstractmethod
    def __call__(self, value, parent=None):
        pass

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.keyword}" ref="{self.ref}">'


class NoneValidator(StandardAttributeValidator):
    """Just returns the value without any validation"""

    keyword = '$none'

    def __call__(self, value, parent):
        return value


class DateTimeValidator(StandardAttributeValidator):
    keyword = '$datetime'

    def __call__(self, value, parent):
        if isinstance(value, str):
            datetime.fromisoformat(value)
            return value
        if not isinstance(value, datetime):
            raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {datetime}')
        return str(value.isoformat())


class TypeValidator(StandardAttributeValidator):
    """Validates the data type of the attribute"""

    keyword = '$type'

    def __init__(self, types):
        if not isinstance(types, (list, tuple)):
            super().__init__((types,))
        else:
            super().__init__(types)

    def __call__(self, value, parent):
        if not any(isinstance(value, _eval_type(t)) for t in self.ref):
            raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {self.ref}')
        return value


class InValidator(StandardAttributeValidator):
    """Validates if the attribute value is in the list of expected values.
    During definition, the list of expected values is passed as a list of strings,
    see the example usage below, where the validator is used in the standard
    attribute "data_source"

    Parameters
    ----------
    expectation: List[str]
        List of expected values

    Example
    -------
    >>> import h5rdmtoolbox as h5tbx
    >>> data_source = h5tbx.conventions.StandardAttribute(
    >>>         name='units',
    >>>         validator={'$in': ['numerical', 'experimental', 'analytical']},
    >>>         method='__init__'
    >>>         description='The source of data'
    >>>     )
    """

    keyword = '$in'

    def __init__(self, expectation: List[str]):
        if not isinstance(expectation, (tuple, list)):
            raise TypeError(f'Invalid type for parameter "expectation": {type(expectation)}')

        super().__init__(expectation)

    def __call__(self, value, parent):
        if value not in self.ref:
            raise ValueError(f'The value "{value}" is not in {self.ref}. '
                             f'Expecting one of these: {self.ref}')
        return value


class ORCIDValidator(StandardAttributeValidator):
    """Validator class, that validates ORCIDs. If an internet
    connection exists, the url is checked, otherwise and if previously
    validated, the ORCID is locally validated."""

    keyword = '$orcid'

    def __call__(self, orcid, *args, **kwargs) -> Union[str, List[str]]:
        if not isinstance(orcid, (list, tuple)):
            orcid = [orcid, ]
        for o in orcid:
            if not isinstance(o, str):
                raise TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')

            _orcid = ORCID(o)
            if not _orcid.exists():
                raise ValueError(f'Not an ORCID ID: {o}')
        return orcid


class PintQuantityValidator(StandardAttributeValidator):
    keyword = '$pintquantity'

    def __call__(self, quantity, parent, **kwargs):
        try:
            get_ureg().Quantity(quantity)
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Quantity cannot be understood using ureg package: {quantity}. Original error: {e}')
        return str(quantity)


class PintUnitsValidator(StandardAttributeValidator):
    keyword = '$pintunit'

    def __call__(self, value, parent, **kwargs) -> str:
        try:
            get_ureg().Unit(value)
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')
        return str(value)


class _BaseReferenceValidator(StandardAttributeValidator, abc.ABC):

    @staticmethod
    def _parse_dict(value):
        """Returns a string representation of a dict if value is a dict else passes value through"""
        if isinstance(value, dict):
            return json.dumps(value)
        return value


class ReferencesValidator(_BaseReferenceValidator):
    keyword = '$ref'

    def __call__(self, references, *args, **kwargs):
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        if all(validate_reference(r) for r in references):
            if len(references) == 1:
                return ReferencesValidator._parse_dict(references[0])
            return [ReferencesValidator._parse_dict(r) for r in references]


class URLValidator(StandardAttributeValidator):
    keyword = '$url'

    def __call__(self, references, *args, **kwargs):
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        if all(validate_url(r) for r in references):
            if len(references) == 1:
                return references[0]
            return references
        raise ValueError(f'Invalid URL: {references}')


class BibTeXValidator(_BaseReferenceValidator):
    keyword = '$bibtex'

    def __call__(self, bibtex, *args, **kwargs) -> List[str]:
        if not isinstance(bibtex, (list, tuple)):
            bibtex = [bibtex, ]
        if all(validate_bibtex(b) for b in bibtex):
            if len(bibtex) == 1:
                return BibTeXValidator._parse_dict(bibtex[0])
            return [BibTeXValidator._parse_dict(b) for b in bibtex]
        raise ValueError(f'Invalid Bibtex entry: {bibtex}')


class MinLengthValidator(StandardAttributeValidator):
    keyword = '$minlength'

    def __call__(self, value, parent=None):
        if len(value) < self.ref:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.ref}')
        return value


class MaxLengthValidator(StandardAttributeValidator):
    keyword = '$maxlength'

    def __call__(self, value, parent=None):
        if len(value) > self.ref:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.ref}')
        return value


class RegexValidator(StandardAttributeValidator):
    """The RegexValidator matches the input against a regular expression.

    Examples
    --------
    >>> from h5rdmtoolbox.conventions.validators import RegexValidator
    >>> validator = RegexValidator('^[a-z]+$', '^[a-z]+$')
    >>> validator('abc', None)
    """

    keyword = '$regex'

    def __call__(self, value, parent=None):
        if re.match(self.ref, value) is None:
            raise errors.ValidatorError(f'The value "{value}" does not match the pattern "{self.ref}"')
        return value


# list of all validator classes:
VALIDATORS = {v.keyword: v for k, v in locals().items() if
              k.endswith('Validator') and k != 'StandardAttributeValidator' and not k.startswith('_')}


def get_validator(validator_keyword=None) -> Union[dict, StandardAttributeValidator]:
    """Returns a validator class or a dictionary of all validator classes."""
    if validator_keyword is None:
        return VALIDATORS
    return VALIDATORS[validator_keyword]


def add_validator(validator: StandardAttributeValidator):
    """Adds a validator to the list of available validators."""
    VALIDATORS[validator.keyword] = validator
