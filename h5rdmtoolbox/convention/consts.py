import enum


class _SpecialDefaults(enum.Enum):
    NONE = 0
    EMPTY = 1


class DefaultValue:
    EMPTY = _SpecialDefaults.EMPTY
    NONE = _SpecialDefaults.NONE

    def __init__(self, value):
        if value == '$none':
            self.value = _SpecialDefaults.NONE
        elif value == '$empty':
            self.value = _SpecialDefaults.EMPTY
        else:
            self.value = value

    def __eq__(self, other):
        return self.value == other
