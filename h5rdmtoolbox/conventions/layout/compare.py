class Equal:
    def __init__(self, reference):
        self.reference = reference

    def __call__(self, other):
        return self.reference == other


def AnyString(value):
    if isinstance(value, str):
        return True
    return False


class Regex(Equal):
    """check if value matches the regular expression.
    Parameters
    ----------
    reference : str
        regular expression
    """

    def __call__(self, value):
        """check if value matches the regular expression."""
        import re
        return re.match(self.reference, value)
