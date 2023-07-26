from typing import List

from . import StandardAttributeValidator

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
    """Validates if the attribute value is in the list of expected values"""

    def __init__(self, expectation: List[str]):
        if not isinstance(expectation, (tuple, list)):
            raise TypeError(f'Invalid type for parameter "expectation": {type(expectation)}')
        super().__init__(expectation)

    def __call__(self, value, parent):
        if value not in self.ref:
            raise ValueError(f'The value "{value}" has not in {self.ref}. '
                             f'Expecting one of these: {self.ref}')
        return value
