import logging
import pathlib
from pathlib import Path

import h5py
import numpy as np
import pint_xarray
from IPython.display import HTML, display

from .identifier import equal_base_units
from .. import _repr

logger = logging.getLogger(__package__)

assert pint_xarray.__version__ >= '0.2.1'


class H5Inspect:
    """Inspection class"""

    def __init__(self, h5_root_group, inspect_group, inspect_dataset, silent=False, ignore_names=None):
        if ignore_names is None:
            self.ignore_names = []
        else:
            self.ignore_names = ignore_names
        self.names = []
        self.silent = silent
        self.root = h5_root_group
        self.nissues = 0
        self.inspect_group = inspect_group
        self.inspect_dataset = inspect_dataset
        self.inspect_group(self.root)

    def __call__(self, name, h5obj):
        self.names.append(h5obj.name)
        if h5obj.name not in self.ignore_names:
            if isinstance(h5obj, h5py.Dataset):
                self.inspect_dataset(h5obj)
            else:
                self.inspect_group(h5obj)


class H5InspectLayout:
    """HDF5 Inspection class for layouts"""

    def __init__(self, h5_root_group, h5_root_layout_group, silent=False, ignore_names=None):
        if ignore_names is None:
            self.ignore_names = []
        else:
            self.ignore_names = ignore_names
        self.names = []
        self.silent = silent
        self.root = h5_root_group
        self.root_layout = h5_root_layout_group
        self.nissues = 0
        self.inspect_group(self.root, h5_root_layout_group)

    def __call__(self, name, h5obj):
        self.names.append(h5obj.name)
        if isinstance(h5obj, h5py.Dataset):
            self.inspect_dataset(self.root, h5obj)
        else:
            self.inspect_dataset(self.root, h5obj)

    def inspect_group(self, targetgrp, layoutgrp):
        """inspects a group"""
        if not self.silent:
            print(f'inspecting group {targetgrp.name}')
        layout_group_attributes = dict(layoutgrp.attrs)
        # if layoutgrp.name == '/':
        #     if 'title' not in layout_group_attributes:
        #         layout_group_attributes['title'] = '__title'
        for kl, vl in layout_group_attributes.items():
            if len(kl) >= 2:
                if kl[0:2] == '__':  # attribute name starts with __ --> special meaning
                    pass
                else:
                    if kl not in targetgrp.attrs:
                        if not self.silent:
                            print(f' [gr] {targetgrp.name}: attribute "{kl}" missing')
                        self.nissues += 1
                    else:
                        if len(vl) >= 2:
                            if vl[0:2] == '__':  # value starts with __ -> dont compare value. attribute must only exist
                                pass
                            else:
                                if vl != targetgrp.attrs[kl]:
                                    if not self.silent:
                                        print(f' > attribute "{kl}" has the wrong value: "{targetgrp.attrs[kl]}" '
                                              f'instead of "{vl}"')
                                    self.nissues += 1

    def inspect_dataset(self, target_group, layout_dataset):
        """inspects a dataset"""
        if not self.silent:
            print(f'inspecting dataset {layout_dataset.name}')
        if layout_dataset.name not in target_group:
            if not self.silent:
                print(f' [ds] {layout_dataset.name}: missing')
            self.nissues += 1
        else:
            layout_dataset_attributes = dict(layout_dataset.attrs)
            if 'units' in layout_dataset_attributes:
                target_units = target_group[layout_dataset.name].attrs['units']
                required_units = layout_dataset_attributes['units']
                if not equal_base_units(target_units, required_units):
                    if not self.silent:
                        print(
                            f'Units issue for dataset {layout_dataset.name}: Unequal base units: {target_units} <> {required_units}')
                    self.nissues += 1

            else:
                layout_dataset_attributes['units'] = '__units'
            if 'long_name' not in layout_dataset_attributes and 'standard_name' not in layout_dataset_attributes:
                if 'long_name' not in target_group[layout_dataset.name].attrs and 'standard_name' not in \
                        target_group[layout_dataset.name].attrs:
                    if not self.silent:
                        print(f'Dataset "{layout_dataset.name}" has neither the attribute '
                              f'"long_name" nor "standard_name"')
                    self.nissues += 1

            for kl, vl in layout_dataset.attrs.items():
                if kl == '__shape__':
                    if target_group[layout_dataset.name].shape != vl:
                        if not self.silent:
                            print(f' [ds] {layout_dataset.name}: wrong dataset shape: '
                                  f'{target_group[layout_dataset.name].shape} instead of: {vl}.')
                        self.nissues += 1
                elif kl == '__ndim__':
                    if isinstance(vl, np.ndarray):
                        _ndim = list(vl)
                    elif not isinstance(vl, (list, tuple)):
                        _ndim = (vl,)
                    else:
                        _ndim = vl
                    if target_group[layout_dataset.name].ndim not in _ndim:
                        if not self.silent:
                            print(f' [ds] {layout_dataset.name}: wrong dataset dimension: '
                                  f'{target_group[layout_dataset.name].ndim} instead of: {vl}.')
                        self.nissues += 1
                elif kl[0:2] != '__':
                    if kl not in target_group[layout_dataset.name].attrs:
                        if not self.silent:
                            print(f' [ds] {layout_dataset.name}: attribute "{kl}" missing')
                        self.nissues += 1


class H5FileLayout:
    """class defining the static layout of the HDF5 file"""

    def __init__(self, filename: Path):
        self.filename = Path(filename)
        if not self.filename.exists():
            self.write()
        self._file = None

    def __enter__(self):
        self._file = h5py.File(self.filename, mode='r')
        return self._file

    def __exit__(self, *args):
        self._file.close()

    def _repr_html_(self):
        preamble = f'<p>Layout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            return _repr.h5file_html_repr(h5, max_attr_length=None, preamble=preamble,
                                          build_debug_html_page=False)

    def sdump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        """string representation of file content"""
        with h5py.File(self.filename, mode='r') as h5:
            return _repr.sdump(h5, ret, nspaces, grp_only, hide_attributes, color_code_verification,
                               is_layout=True)

    def dump(self, max_attr_length=None, **kwargs):
        """dumps the layout to the screen (for jupyter notebooks)"""
        build_debug_html_page = kwargs.pop('build_debug_html_page', False)
        preamble = f'<p>Layout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            display(HTML(_repr.h5file_html_repr(h5, max_attr_length, preamble=preamble,
                                                build_debug_html_page=build_debug_html_page)))

    def write(self) -> pathlib.Path:
        """write the static layout file to user data dir"""
        if not self.filename.parent.exists():
            self.filename.parent.mkdir(parents=True)
        logger.debug(
            f'Layout file for class {self.__class__.__name__} is written to {self.filename}')
        with h5py.File(self.filename, mode='w') as h5:
            h5.attrs['__h5rdmtoolbox_version__'] = '__version of this package'
            h5.attrs['creation_time'] = '__time of file creation'
            h5.attrs['modification_time'] = '__time of last file modification'
        return self.filename

    def check_dynamic(self, root_grp: h5py.Group, silent: bool = False) -> int:
        return 0

    def check_static(self, root_grp: h5py.Group, silent: bool = False):
        return layout_inspection(root_grp, self.filename, silent=silent)

    def check(self, root_grp: Path, silent: bool = False) -> int:
        """combined (static+dynamic) check

        Parameters
        ----------
        root_grp: h5py.Group
            HDF5 root group of the file to be inspected
        silent: bool, optional=False
            Control extra string output.

        Returns
        -------
        n_issues: int
            Number of issues
        silent: bool, optional=False
            Controlling verbose output to screen. If True issue information is printed,
            which is especcially helpful.
        """
        if not isinstance(root_grp, h5py.Group):
            raise TypeError(f'Expecting h5py.Group, not type {type(root_grp)}')
        return self.check_static(root_grp, silent) + self.check_dynamic(root_grp, silent)

    def write(self):
        if not self.filename.parent.exists():
            self.filename.parent.mkdir(parents=True)
        logger.debug(
            f'Layout file for class {self.__class__.__name__} is written to {self.filename}')
        with h5py.File(self.filename, mode='w') as h5:
            h5.attrs['__h5rdmtoolbox_version__'] = '__version of this package'
            h5.attrs['creation_time'] = '__time of file creation'
            h5.attrs['modification_time'] = '__time of last file modification'
        with h5py.File(self.filename, mode='r+') as h5:
            h5.attrs['title'] = '__Description of file content'

    @staticmethod
    def __check_group__(group, silent: bool = False) -> int:
        return 0

    @staticmethod
    def __check_dataset__(dataset, silent: bool = False) -> int:
        # check if dataset has units, long_name or standard_name
        nissues = 0
        if 'units' not in dataset.attrs:
            if not silent:
                print(f' [ds] {dataset.name} : attribute "units" missing')
            nissues += 1

        if 'long_name' not in dataset.attrs and 'standard_name' not in dataset.attrs:
            if not silent:
                print(f' [ds] {dataset.name} : attribute "long_name" and "standard_name" missing. Either of it must '
                      f'exist')
            nissues += 1

        return nissues

    def check_dynamic(self, h5root: h5py.Group, silent: bool = False) -> int:
        h5inspect = H5Inspect(h5root, inspect_group=self.__check_group__,
                              inspect_dataset=self.__check_dataset__, silent=silent)
        h5root.visititems(h5inspect)
        return h5inspect.nissues


def layout_inspection(h5root: h5py.Group, layout_file: Path, silent: bool = False) -> int:
    """compares layout content with passed root

    Parameters
    ----------
    h5root: h5py.File
        Root group of the HDF5 file
    layout_file: Path
        File path to layout file
    silent: bool, optional=False
        Whether to print out verbose test or not
    """

    if not silent:
        print('\nFile layout inspection')
        print('------------')

    with h5py.File(layout_file) as h5layout:
        # check root attributes
        h5inspect = H5InspectLayout(h5root, h5layout, silent)
        h5layout.visititems(h5inspect)
        if not silent:
            print(f' --> {h5inspect.nissues} issue(s) found during layout inspection')
    return h5inspect.nissues
