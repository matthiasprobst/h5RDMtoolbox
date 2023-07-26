import abc


class StandardAttributeValidator:
    """Abstract Validator class of Standard Name Attribute classes"""

    def __init__(self, ref=None):
        self.ref = ref

    @abc.abstractmethod
    def __call__(self, value, parent):
        pass
