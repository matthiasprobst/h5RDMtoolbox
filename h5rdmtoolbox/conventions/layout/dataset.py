import typing

import h5py

from . import properties
from . import validators
from .path import LayoutPath
from .validations import Validation


class Dataset:
    """Layout dataste interface"""
    def __init__(self,
                 *,
                 path: typing.Union[str, "LayoutPath"],
                 file: "Layout"):
        self.path = LayoutPath(path)  # group path!
        from .layout import Layout
        assert isinstance(file, Layout)
        self.file = file

    def __repr__(self):
        return f'LayoutDataset("{self.path}")'

    def dataset(self, name: str):
        pass