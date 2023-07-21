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
            self.types = (types,)
        else:
            self.types = types

    def __call__(self, value, parent):
        if not any(isinstance(value, _eval_type(t)) for t in self.types):
            raise ValueError(f'The value "{value}" has wrong type: {type(value)}. Expected: {self.types}')
        return value


class InValidator(StandardAttributeValidator):
    """Validates if the attribute value is in the list of expected values"""

    def __init__(self, expectation):
        if not isinstance(expectation, (tuple, list)):
            raise TypeError(f'Invalid type for parameter "expectation": {type(expectation)}')
        self.expectation = expectation

    def __call__(self, value, parent):
        if value not in self.expectation:
            raise ValueError(f'The value "{value}" has not in {self.expectation}. '
                             f'Expecting one of these: {self.expectation}')
        return value
