import typing

from . import validators


_defaults = {}


class LayoutRegistry:
    """Registry interface class for File objects."""

    @staticmethod
    def build_defaults() -> typing.Dict:
        """Build the default layouts."""
        # pre-defined layouts:
        from .layout import Layout
        TbxLayout = Layout()
        TbxLayout.attrs['__h5rdmtoolbox__'] = '__version of this package'
        TbxLayout.attrs['title'] = validators.Any()

        _defaults = {'tbx': TbxLayout}
        return _defaults

    def __init__(self):
        self.layouts = self.build_defaults()

    def __repr__(self):
        names = ','.join(f'"{k}"' for k in self.layouts.keys())
        return f'LayoutRegistry({names},)'

    @property
    def names(self) -> typing.List[str]:
        """Return a list of all registered layout names."""
        return list(self.layouts.keys())

    def __getitem__(self, name) -> "Layout":
        if name in self.layouts:
            return self.layouts[name]
        raise KeyError(f'No layout with name "{name}" found. Available layouts: {self.names}')
