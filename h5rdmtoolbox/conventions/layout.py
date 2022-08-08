import logging
import os
import pathlib
import re
import shutil
from pathlib import Path
from typing import Union, Dict, List, TypeVar

import h5py
import numpy as np
import pint_xarray
from IPython.display import HTML, display

from .identifier import equal_base_units
from .. import _repr
from ..utils import user_data_dir

logger = logging.getLogger(__package__)
T_Layout = TypeVar('Layout')
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
                target_units = target_group[layout_dataset.name].attrs.get('units')
                required_units = layout_dataset_attributes['units']
                if target_units is None or not equal_base_units(target_units, required_units):
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


def check_attributes(obj: Union[h5py.Dataset, h5py.Group],
                     otherobj: Union[h5py.Dataset, h5py.Group],
                     silent: bool = False):
    """Check consistency of attributes"""
    issues = IssueList()
    for ak, av in obj.attrs.items():
        # first check special attributes
        if ak == '__shape__':
            _shape = tuple(av)
            if otherobj.shape != _shape:
                issues.append({'path': obj.name,
                               'obj_type': 'dataset',
                               'name': ak,
                               'issue': f'wrong shape: {otherobj.shape} != {_shape}'})
            continue
        elif ak == '__ndim__':
            if isinstance(av, np.ndarray):
                _ndim = list(av)
            elif not isinstance(av, (list, tuple)):
                _ndim = (av,)
            else:
                _ndim = av
            if otherobj.ndim not in _ndim:
                issues.append({'path': obj.name,
                               'obj_type': 'dataset',
                               'name': ak,
                               'issue': f'wrong dimension: {otherobj.ndim} != {av}'})
            continue
        elif ak == '__check_isoptional__':
            continue

        elif ak == 'exact_units':
            other_units = otherobj.attrs.get('units')
            if other_units:
                if av != otherobj.attrs[ak]:
                    if not silent:
                        print(f'Exact units check failed for {obj.name}: {av} != {other_units}')
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'wrong'})
            else:
                if not silent:
                    print(f'Attribute units missing in {obj.name}')
                issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'missing'})
            continue

        elif ak in ('units', 'baseunits'):
            other_units = otherobj.attrs.get('units')
            if other_units:
                if not equal_base_units(av, otherobj.attrs[ak]):
                    if not silent:
                        print(f'Base-units check failed for {obj.name}: {av} != {other_units}')
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'wrong'})
            else:
                if not silent:
                    print(f'Attribute units missing in {obj.name}')
                issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'missing'})
            continue
        keys = ak.split('.alt:')
        if len(keys) > 1:
            if not any([k in otherobj.attrs for k in keys]):
                issues.append(
                    {'path': obj.name, 'obj_type': 'attribute', 'name': ' or '.join(keys), 'issue': 'missing'})
            continue

        if ak.startswith('__'):
            continue  # other special meaning

        try:
            other_av = otherobj.attrs[ak]
            # attribute name exits
            # now check value
            if not av.startswith('__'):
                if av != other_av:
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': ak, 'issue': 'unequal'})
                    if not silent:
                        print(f'Attribute value issue for {obj.name}: {av} != {other_av}')
        except KeyError:
            if not silent:
                print(f'Attribute {ak} missing in group {obj.name}')
            issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': ak, 'issue': 'missing'})
    return issues


class IssueList(list):
    """Special list object which can append lists to a list in sequence.
    e.g.: ['a', 'b'].append(['c', 'c']) --> ['a', 'b', 'c', 'd'] instead of ['a', 'b', ['c', 'd']]"""

    def append(self, __object) -> None:
        if isinstance(__object, list):
            for __obj in __object:
                self.append(__obj)
        else:
            super(IssueList, self).append(__object)


class LayoutDataset(h5py.Dataset):
    """H5FileLayout check class for datasets"""

    def check(self, other: h5py.Dataset, silent: bool = True) -> List[Dict]:
        """Run consistency check"""
        issues = IssueList()
        issues.append(check_attributes(self, other, silent))
        return issues


class LayoutGroup(h5py.Group):
    """H5FileLayout check class for groups"""

    def __getitem__(self, name):
        ret = super().__getitem__(name)
        if isinstance(ret, h5py.Dataset):
            return LayoutDataset(ret.id)
        elif isinstance(ret, h5py.Group):
            return LayoutGroup(ret.id)
        return ret

    def dump(self, max_attr_length=None, **kwargs):
        """dumps the layout to the screen (for jupyter notebooks)"""
        build_debug_html_page = kwargs.pop('build_debug_html_page', False)
        preamble = f'<p>H5FileLayout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            display(HTML(_repr.h5file_html_repr(h5, max_attr_length, preamble=preamble,
                                                build_debug_html_page=build_debug_html_page)))

    def sdump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        """string representation of file content"""
        with h5py.File(self.filename, mode='r') as h5:
            return _repr.sdump(h5, ret, nspaces, grp_only, hide_attributes, color_code_verification,
                               is_layout=True)

    def check(self, other: h5py.Group, silent: bool = True,
              recursive: bool = True):
        """Run consistency check"""
        issues = IssueList()

        issues.append(check_attributes(self, other, silent))
        for obj_name, obj in self.items():
            if isinstance(obj, h5py.Dataset):
                obj_name_alt_split = obj_name.split('.alt:')
                if len(obj_name_alt_split) == 2:
                    ds_name, alt_grp = obj_name_alt_split
                    # first check if the dataset exist:
                    if ds_name in other:
                        issues.append(self[obj_name].check(other[ds_name], silent))
                    else:
                        # now check alternative:
                        # does the alternative group exist?
                        alt_grp_re = alt_grp.split('re:')
                        if len(alt_grp_re) == 2:
                            for other_grp_name, other_grp in other.items():
                                if isinstance(other_grp, h5py.Group):
                                    if re.match(alt_grp_re[1], other_grp_name):
                                        if ds_name in other_grp:
                                            issues.append(self[obj_name].check(other_grp[ds_name], silent))
                                        else:
                                            issues.append({'path': os.path.join(other.name, alt_grp, ds_name),
                                                           'obj_type': 'dataset',
                                                           'issue': 'missing'})
                                            if not silent:
                                                print(f'Dataset name {ds_name} missing in '
                                                      f'{os.path.join(other.name, alt_grp, ds_name)}.')

                        else:
                            if alt_grp in other.keys():
                                if ds_name in other[alt_grp]:
                                    issues.append(self[obj_name].check(other[alt_grp][ds_name], silent))
                                else:
                                    issues.append({'path': os.path.join(other, alt_grp, ds_name), 'obj_type': 'dataset',
                                                   'issue': 'missing'})
                                    if not silent:
                                        print(f'Dataset name {ds_name} missing in {os.path.join(other, alt_grp, ds_name)}.')
                            else:
                                issues.append({'path': alt_grp, 'obj_type': 'group', 'issue': 'missing'})
                                if not silent:
                                    print(f'Group name {alt_grp} missing in {self.name}.')

                else:
                    if obj_name in other:
                        issues.append(self[obj_name].check(other[obj_name], silent))
                    else:
                        issues.append({'path': obj.name, 'obj_type': 'dataset', 'issue': 'missing'})
                        if not silent:
                            print(f'Dataset name {obj_name} missing in {self.name}.')
            else:
                if recursive:
                    alt_grp_name = obj.attrs.get('__alternative_source_group__')
                    if alt_grp_name:
                        if obj.name in other:
                            issues.append(LayoutGroup(obj.id).check(other[obj.name], silent))
                        else:
                            # check the alternative:
                            if alt_grp_name.startswith('re:'):
                                alt_grp_name = alt_grp_name[3:]
                                # multiple alternatives
                                n_found = 0
                                obj_basename = os.path.basename(obj.name)
                                for other_grp_name, other_grp in other.items():
                                    if isinstance(other_grp, h5py.Group):
                                        if re.match(alt_grp_name, other_grp_name):
                                            if obj_basename in other_grp:
                                                n_found += 1
                                                issues.append(LayoutGroup(obj.id).check(other_grp[obj_basename], silent))

                                if n_found == 0 and not obj.attrs.get('__check_isoptional__', False):
                                    if not silent:
                                        print(f'Group name "{obj_name}" missing in {other.name}.')
                                    issues.append({'path': self[obj_name].name,
                                                   'obj_type': 'group',
                                                   'issue': 'missing'})
                            else:
                                # a single alternative
                                if alt_grp_name not in other:
                                    if not silent:
                                        print(f'Group name "{alt_grp_name}" missing in {other.name}.')
                                    issues.append({'path': os.path.join(self.name, alt_grp_name),
                                                   'obj_type': 'group',
                                                   'issue': 'missing'})
                                else:
                                    pass
                    else:
                        name_re_split = obj_name.split('re:')
                        if len(name_re_split) == 2:
                            n_found = 0
                            for other_grp_name, other_grp in other.items():
                                if isinstance(other_grp, h5py.Group):
                                    if re.match(name_re_split[1], other_grp_name):
                                        n_found += 1
                                        issues.append(LayoutGroup(obj.id).check(other_grp, silent))
                            if n_found == 0 and not obj.attrs.get('__check_isoptional__', False):
                                if not silent:
                                    print(f'Group name "{obj_name}" missing in {other.name}.')
                                issues.append({'path': self[obj_name].name,
                                               'obj_type': 'group',
                                               'issue': 'missing'})
                        else:
                            if obj_name in other:
                                issues.append(LayoutGroup(obj.id).check(other[obj_name]))
                            else:
                                is_optional = obj.attrs.get('__check_isoptional__', False)
                                if not is_optional:
                                    if not silent:
                                        print(f'Group name "{obj_name}" missing in {other.name}.')
                                    issues.append({'path': self[obj_name].name,
                                                   'obj_type': 'group',
                                                   'issue': 'missing'})

        return issues


class H5FileLayout(h5py.File, LayoutGroup):
    """Abstract class for HDF5 layouts"""

    def __init__(self, filename: Path = None, mode='r'):
        filename = pathlib.Path(filename)
        super().__init__(filename, mode=mode)
        self._file = None

    def _repr_html_(self):
        preamble = f'<p>H5FileLayout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            return _repr.h5file_html_repr(h5, max_attr_length=None, preamble=preamble,
                                          build_debug_html_page=False)

    # @abc.abstractmethod
    def write(self) -> pathlib.Path:
        """Write the attribute, datasets and groups to the file that
        are then used to compare to another HDF file"""
        pass

    # @abc.abstractmethod
    def check(self, other: h5py.File) -> pathlib.Path:
        """Compare this file content to another hHDF5 file.
        Note, as this is a layout class, the comparion is special because
        HDF object names may hav prefixes like 'any:' or 'pergroup:'
        indiating a conditional check"""
        pass


class Layout:
    """class defining the static layout of the HDF5 file"""

    @property
    def n_issues(self):
        """Return number of found issues"""
        return len(self._issues_list)

    def __repr__(self) -> str:
        return f'<H5FileLayout with {self.n_issues} issues>'

    def __str__(self) -> str:
        out = f'H5FileLayout issue report ({self.n_issues} issues)\n-------------------'
        for issue in self._issues_list:
            if issue['obj_type'] == 'attribute':
                out += f'\n{issue["path"]}.{issue["name"]}: -> {issue["issue"]}'
            else:
                out += f'\n{issue["path"]}: -> {issue["issue"]}'
        return out

    def __init__(self, filename: Path):
        self.filename = Path(filename)
        self._issues_list = []
        if not self.filename.exists():
            # touch file:
            with H5FileLayout(self.filename, 'w'):
                pass

    @staticmethod
    def init_from(src_filename: Path, filename: Path) -> T_Layout:
        """Copy src filename and return Layout object with filename"""
        shutil.copy2(src_filename, filename)
        return Layout(filename)

    def File(self, mode='r'):
        self._file = H5FileLayout(self.filename, mode=mode)
        return self._file

    def _repr_html_(self):
        preamble = f'<p>H5FileLayout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            return _repr.h5file_html_repr(h5, max_attr_length=None, preamble=preamble,
                                          build_debug_html_page=False)

    def sdump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        """string representation of file content"""
        with H5FileLayout(self.filename) as lay:
            return lay.sdump(ret, nspaces, grp_only, hide_attributes, color_code_verification)

    def dump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        """string representation of file content"""
        with H5FileLayout(self.filename) as lay:
            return lay.sdump(ret, nspaces, grp_only, hide_attributes, color_code_verification)

    def write(self) -> pathlib.Path:
        """write the static layout file to user data dir"""
        if not self.filename.parent.exists():
            self.filename.parent.mkdir(parents=True)
        logger.debug(
            f'H5FileLayout file for class {self.__class__.__name__} is written to {self.filename}')
        with h5py.File(self.filename, mode='w') as h5:
            h5.attrs['__h5rdmtoolbox_version__'] = '__version of this package'
            h5.attrs['creation_time'] = '__time of file creation'
            h5.attrs['modification_time'] = '__time of last file modification'
        return self.filename

    def check(self, grp: h5py.Group, silent: bool = False,
              recursive: bool = True) -> int:
        """combined (static+dynamic) check

        Parameters
        ----------
        grp: h5py.Group
            HDF5 root group of the file to be inspected
        silent: bool, optional=False
            Control extra string output.
        recursive: boo, optional=True
            Recursive check.

        Returns
        -------
        n_issues: int
            Number of issues
        silent: bool, optional=False
            Controlling verbose output to screen. If True issue information is printed,
            which is especcially helpful.
        """
        if not isinstance(grp, h5py.Group):
            raise TypeError(f'Expecting h5py.Group, not type {type(grp)}')
        issues = IssueList()
        grp_name = grp.name
        with H5FileLayout(self.filename) as lay:
            if grp_name in lay:
                issues.append(lay[grp_name].check(grp, silent=silent,
                                                  recursive=recursive))
            else:
                raise KeyError(f'Group {grp_name} does not exist in layout')
        self._issues_list = issues
        return self.n_issues

        # return self.check_static(grp, silent) + self.check_dynamic(root_grp, silent)


def save_layout(layout: Layout, name=None, parent=None):
    """Save the layout HDF file in a specific location"""
    if not isinstance(layout, Layout):
        raise TypeError(f'Expecting type Layout but got {type(layout)}')
    if name is None:
        name = f'{layout.__name__}.hdf'
    if parent is None:
        parent = user_data_dir / 'layout'
    Path.joinpath(parent, name)


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
