import enum


class _SpecialDefaults(enum.Enum):
    NONE = 0
    EMPTY = 1


class DefaultValue:
    """Helper class to distinguish between optional and obligatory standard attributes."""

    EMPTY = _SpecialDefaults.EMPTY
    NONE = _SpecialDefaults.NONE

    def __init__(self, value):
        if value.lower() == '$none':
            self.value = _SpecialDefaults.NONE
        elif value.lower() == '$optional':
            self.value = _SpecialDefaults.NONE
        elif value.lower() == '$obligatory':
            self.value = _SpecialDefaults.EMPTY
        elif value == '$empty':
            self.value = _SpecialDefaults.EMPTY
        else:
            self.value = value

    def __eq__(self, other):
        return self.value == other
