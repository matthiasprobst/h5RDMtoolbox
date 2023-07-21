import abc


class StandardAttributeValidator:
    """Abstract Validator class of Standard Name Attribute classes"""

    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def __call__(self, value, parent, **kwargs):
        pass
