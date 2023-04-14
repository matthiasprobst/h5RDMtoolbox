"""layout path module"""


class LayoutPath(str):
    """A path in a HDF5 file used in the Layout class."""

    @property
    def name(self) -> str:
        """Return the basename of the path."""
        return self.rsplit('/', 1)[-1]

    @property
    def parent(self) -> str:
        """Return the parent path."""
        p = self.rsplit('/', 1)[0]
        if p == '':
            return '/'
        return p

    @property
    def has_wildcard_suffix(self) -> bool:
        """Return True if the path ends with a wildcard suffix."""
        return self[-1] == '*'

    def __add__(self, other) -> "LayoutPath":
        if len(other) == 0:
            raise ValueError('Other name must not be empty')
        if other == '/':
            return self
        if other[0] == '/':
            other = other[1:]
        if self == '/':
            return LayoutPath(f'{self}{other}')
        return LayoutPath(f'{self}/{other}')

    def __truediv__(self, other):
        return self.__add__(other)
