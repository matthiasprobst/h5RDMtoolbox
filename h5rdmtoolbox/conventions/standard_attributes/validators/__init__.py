import abc


class StandardAttributeValidator:
    """Abstract Validator class of Standard Name Attribute classes"""

    def __init__(self, ref=None, allow_None: bool = False):
        self.ref = ref
        self.allow_None = allow_None

    @abc.abstractmethod
    def __call__(self, value, parent):
        pass
