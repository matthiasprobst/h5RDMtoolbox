import abc

from datetime import datetime
from typing import List, Dict

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

    def __init__(self, ref=None, allow_None: bool = False):
        self.ref = ref
        self.allow_None = allow_None

    @abc.abstractmethod
    def __call__(self, value, parent):
        pass


class NoneValidator(StandardAttributeValidator):
    """Just returns the value without any validation"""

    def __call__(self, value, parent):
        return value


class DateTimeValidator(StandardAttributeValidator):

    def __call__(self, value, parent):
        if isinstance(value, str):
            datetime.fromisoformat(value)
            return value
        if not isinstance(value, datetime):
            raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {datetime}')
        return str(value.isoformat())


class TypeValidator(StandardAttributeValidator):
    """Validates the data type of the attribute"""

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

    def __init__(self, expectation: List[str]):
        if not isinstance(expectation, (tuple, list)):
            raise TypeError(f'Invalid type for parameter "expectation": {type(expectation)}')
        super().__init__(expectation)

    def __call__(self, value, parent):
        if value not in self.ref:
            raise ValueError(f'The value "{value}" is not in {self.ref}. '
                             f'Expecting one of these: {self.ref}')
        return value


def get_validator() -> Dict:
    """Return all validators"""
    from .orcid import ORCIDValidator
    from .references import URLValidator, ReferencesValidator, BibTeXValidator
    from .standard_names import StandardNameValidator, StandardNameTableValidator
    from .strings import RegexValidator, MaxLengthValidator, MinLengthValidator
    from .pint import PintUnitsValidator, PintQuantityValidator

    validators = {'$type': TypeValidator,
                  '$in': InValidator,
                  '$regex': RegexValidator,
                  '$pintunit': PintUnitsValidator,
                  '$pintquantity': PintQuantityValidator,
                  '$orcid': ORCIDValidator,
                  '$url': URLValidator,
                  '$ref': ReferencesValidator,
                  '$bibtex': BibTeXValidator,
                  '$standard_name': StandardNameValidator,
                  '$standard_name_table': StandardNameTableValidator,
                  '$minlength': MinLengthValidator,
                  '$maxlength': MaxLengthValidator,
                  '$datetime': DateTimeValidator,
                  'None': NoneValidator,
                  }
    return validators
