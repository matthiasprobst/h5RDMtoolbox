from pathlib import Path

import h5py
import numpy as np
import pint_xarray

from .identifier import equal_base_units

assert pint_xarray.__version__ == '0.2.1'


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
                        print(f'Units have unequal base units: {target_units} <> {required_units}')
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


# def basic_inspection(h5group: h5py.Group, silent=False):
#     """recursively runs through hdf file starting from given group and checks the following:
#     1. checks (if h5group is root) if an attribute "title" exists, which describes the file's content
#        (this convention comes from cf)
#     2. dataset has an attribute units
#     3. dataset has an attribute either long_name or standard_name
#     """
#     if not silent:
#         print('\nBasic file inspection')
#         print('------------')
#     h5inspect = H5BasicInspect(h5group, silent)
#     h5inspect.inspect_group(h5group['/'])
#     h5group.visititems(h5inspect)
#     if not silent:
#         print(f'--> {h5inspect.nissues} issue(s) found during basic inspection')
#     return h5inspect.nissues

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
        h5inspect = H5InspectLayout(h5root, h5layout)
        h5layout.visititems(h5inspect)
        if not silent:
            print(f' --> {h5inspect.nissues} issue(s) found during layout inspection')
    return h5inspect.nissues
