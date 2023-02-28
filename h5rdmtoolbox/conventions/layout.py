"""layout module to manage/check layout of HDF files"""
import h5py
import logging
import numpy as np
import os
import pathlib
# noinspection PyUnresolvedReferences
import pint_xarray
import re
import shutil
from IPython.display import HTML, display
from pathlib import Path
from typing import Union, Dict, List

from .utils import equal_base_units
from .. import _repr
from .._user import UserDir
from ..utils import generate_temporary_filename

logger = logging.getLogger(__package__)


def check_attributes(obj: Union[h5py.Dataset, h5py.Group],
                     otherobj: Union[h5py.Dataset, h5py.Group]):
    """Check consistency of attributes"""
    issues = IssueList()
    for ak, av in obj.attrs.items():
        # first check special attributes
        if ak == '__shape__':
            _shape = tuple(av)
            if otherobj.shape != _shape:
                logger.error(f'Wrong shape of dataset {obj.name}: {_shape} != {otherobj.shape}')
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
            if other_units is not None:
                if av != otherobj.attrs[ak]:
                    logger.error(f'Exact units check failed for {obj.name}: {av} != {other_units}')
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'wrong'})
            else:
                logger.error(f'Attribute units missing in {obj.name}')
                issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'missing'})
            continue

        elif ak in ('units', 'baseunits'):
            other_units = otherobj.attrs.get('units')
            if other_units is not None:
                if not equal_base_units(av, otherobj.attrs[ak]):
                    logger.error(f'Base-units check failed for {obj.name}: {av} != {other_units}')
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'wrong'})
            else:
                logger.error(f'Attribute units missing in {obj.name}')
                issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': 'units', 'issue': 'missing'})
            continue
        keys = ak.split('.alt:')
        if len(keys) > 1:
            if not any(k in otherobj.attrs for k in keys):
                logger.error(f'Neither of the attribute {", ".join(keys)} exist in {otherobj.name}')
                issues.append(
                    {'path': obj.name, 'obj_type': 'attribute', 'name': ' or '.join(keys), 'issue': 'missing'})
            continue

        if ak.startswith('__'):
            continue  # other special meaning

        if ak in otherobj.attrs:
            other_av = otherobj.attrs[ak]
            # attribute name exits
            # now check value
            if not av.startswith('__'):
                if av != other_av:
                    issues.append({'path': obj.name, 'obj_type': 'attribute', 'name': ak, 'issue': 'unequal'})
                    logger.error(f'Attribute value issue for {obj.name}: {av} != {other_av}')
        else:
            logger.error(f'Attribute {ak} missing in group {obj.name}')
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

    def check(self, other: h5py.Dataset) -> List[Dict]:
        """Run consistency check"""
        issues = IssueList()
        issues.append(check_attributes(self, other))
        return issues


class LayoutGroup(h5py.Group):
    """H5FileLayout check class for groups"""

    def __getitem__(self, name):
        ret = super().__getitem__(name)
        if isinstance(ret, h5py.Dataset):
            return LayoutDataset(ret.id)
        if isinstance(ret, h5py.Group):
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

    def check(self, other: h5py.Group, recursive: bool = True):
        """Run consistency check"""
        issues = IssueList()

        issues.append(check_attributes(self, other))
        for obj_name, obj in self.items():
            if isinstance(obj, h5py.Dataset):
                alt_grp_name = obj.attrs.get('__alternative_source_group__')
                if alt_grp_name:
                    ds_name = obj_name
                    # first check if the dataset exist:
                    if ds_name in other:
                        issues.append(obj.check(other[ds_name]))
                    else:
                        # now check alternative:
                        # does the alternative group exist?
                        if alt_grp_name.startswith('re:'):
                            for other_grp_name, other_grp in other.items():
                                if isinstance(other_grp, h5py.Group):
                                    if re.match(alt_grp_name[3:], other_grp_name):
                                        if ds_name in other_grp:
                                            issues.append(obj.check(other_grp[ds_name]))
                                        else:
                                            issues.append({'path': os.path.join(other.name, alt_grp_name, ds_name),
                                                           'obj_type': 'dataset',
                                                           'issue': 'missing'})
                                            logger.error(f'Dataset name {ds_name} missing in '
                                                         f'{os.path.join(other.name, alt_grp_name, ds_name)}.')

                        else:
                            if alt_grp_name in other.keys():
                                if ds_name in other[alt_grp_name]:
                                    issues.append(obj.check(other[alt_grp_name][ds_name]))
                                else:
                                    issues.append(
                                        {'path': os.path.join(other, alt_grp_name, ds_name), 'obj_type': 'dataset',
                                         'issue': 'missing'})
                                    logger.error(
                                        f'Dataset name {ds_name} missing in '
                                        f'{os.path.join(other, alt_grp_name, ds_name)}.')
                            else:
                                issues.append({'path': alt_grp_name, 'obj_type': 'group', 'issue': 'missing'})
                                logger.error(f'Group name {alt_grp_name} missing in {self.name}.')

                else:
                    if obj_name in other:
                        issues.append(obj.check(other[obj_name]))
                    else:
                        if '__optional__' not in obj.attrs:
                            issues.append({'path': obj.name, 'obj_type': 'dataset', 'issue': 'missing'})
                            logger.error(f'Dataset name {obj_name} missing in {self.name}.')
            else:
                if recursive:
                    alt_grp_name = obj.attrs.get('__alternative_source_group__')
                    if alt_grp_name:
                        if obj.name in other:
                            issues.append(LayoutGroup(obj.id).check(other[obj.name]))
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
                                                issues.append(
                                                    LayoutGroup(obj.id).check(other_grp[obj_basename]))

                                if n_found == 0 and not obj.attrs.get('__check_isoptional__', False):
                                    logger.error(f'Group name "{obj_name}" missing in {other.name}.')
                                    issues.append({'path': obj.name,
                                                   'obj_type': 'group',
                                                   'issue': 'missing'})
                            else:
                                # a single alternative
                                if alt_grp_name not in other:
                                    logger.error(f'Group name "{alt_grp_name}" missing in {other.name}.')
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
                                        issues.append(LayoutGroup(obj.id).check(other_grp))
                            if n_found == 0 and not obj.attrs.get('__check_isoptional__', False):
                                logger.error(f'Group name "{obj_name}" missing in {other.name}.')
                                issues.append({'path': obj.name,
                                               'obj_type': 'group',
                                               'issue': 'missing'})
                        else:
                            if obj_name in other:
                                issues.append(LayoutGroup(obj.id).check(other[obj_name]))
                            else:
                                is_optional = obj.attrs.get('__check_isoptional__', False)
                                if not is_optional:
                                    logger.error(f'Group name "{obj_name}" missing in {other.name}.')
                                    issues.append({'path': obj.name,
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
            return _repr.HDF5StructureStrRepr(h5)(preamble=preamble)

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
        indicating a conditional check"""
        pass


class H5Layout:
    """HDF5 Layout interface class"""

    @property
    def n_issues(self):
        """Return number of found issues"""
        return len(self._issues_list)

    def __init__(self, filename: Path, h5repr: _repr.H5Repr = None):
        self.filename = Path(filename)
        if h5repr is None:
            self.h5repr = _repr.H5Repr()
        else:
            self.h5repr = h5repr
        self._issues_list = []
        if not self.filename.exists():
            # touch file:
            with H5FileLayout(self.filename, 'w'):
                pass

    def __repr__(self) -> str:
        return f'<H5FileLayout with {self.n_issues} issues>'

    def __str__(self) -> str:
        return f'<H5FileLayout with {self.n_issues} issues>'

    def report(self) -> None:
        """Print issue report"""
        out = f'H5FileLayout issue report ({self.n_issues} issues)\n-------------------'
        for issue in self._issues_list:
            if issue['obj_type'] == 'attribute':
                out += f'\n{issue["path"]}.{issue["name"]}: -> {issue["issue"]}'
            else:
                out += f'\n{issue["path"]}: -> {issue["issue"]}'
        print(out)

    @staticmethod
    def find_registered_filename(name: str) -> pathlib.Path:
        """Return the file of the registered layout

        Parameters
        ----------
        name: str
            Name under which the layout is registered.

        Returns
        -------
        pathlib.Path
            The found filename in the user directory for registered layouts

        Raises
        ------
        FileNotFoundError
            If no unique filename found be idetified.

        """
        src = UserDir['layouts'] / name
        if src.exists():
            return src
        # search for names:
        candidates = list(UserDir['layouts'].glob(f'{name}.*'))
        if len(candidates) == 1:
            return pathlib.Path(candidates[0])
        raise FileNotFoundError(
            f'File {name} could not be found or passed name was not unique. Check the user layout dir '
            f'{UserDir["layouts"]}'
        )

    @staticmethod
    def load_registered(name: str, *, h5repr: _repr.H5Repr) -> 'H5Layout':
        """Load from user data dir, copy to filename. If filename is None a tmp file is created"""
        src_filename = H5Layout.find_registered_filename(name)
        filename = generate_temporary_filename(suffix='.hdf')
        shutil.copy2(src_filename, filename)
        return H5Layout(filename, h5repr=h5repr)

    def File(self, mode='r') -> H5FileLayout:
        """File instance"""
        self._file = H5FileLayout(self.filename, mode=mode)
        return self._file

    def _repr_html_(self, max_attr_length=None):
        preamble = f'<p>H5FileLayout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            if max_attr_length:
                self.h5repr.__html__.max_attr_length = max_attr_length
            self.h5repr.__html__(h5, preamble=preamble)

    def sdump(self):
        """string representation of file content"""
        with H5FileLayout(self.filename) as lay:
            return self.h5repr.__str__(lay)

    def dump(self, max_attr_length=None):
        """string representation of file content"""
        with H5FileLayout(self.filename) as lay:
            if max_attr_length:
                self.h5repr.__html__.max_attr_length = max_attr_length
            self.h5repr.__html__(lay)

    def write(self) -> pathlib.Path:
        """write the static layout file to user data dir"""
        if not self.filename.parent.exists():
            self.filename.parent.mkdir(parents=True)
        logger.debug(
            f'H5FileLayout file for class {self.__class__.__name__} is written to {self.filename}')
        with h5py.File(self.filename, mode='w') as h5:
            h5.attrs['__h5rdmtoolbox_version__'] = '__version of this package'
        return self.filename

    def check_file(self, filename: Union[str, pathlib.Path],
                   recursive: bool = True) -> int:
        """Run check on a file. Class method check() is called on the root group"""
        with h5py.File(filename) as h5:
            return self.check(h5, recursive=recursive)

    def check(self, grp: h5py.Group,
              recursive: bool = True) -> int:
        """Run layout check.

        Parameters
        ----------
        grp: h5py.Group
            HDF5 group of the file to be inspected
        recursive: boo, optional=True
            Recursive check.

        Returns
        -------
        n_issues: int
            Number of detected issues.
        """
        if not isinstance(grp, h5py.Group):
            raise TypeError(f'Expecting h5py.Group, not type {type(grp)}')
        issues = IssueList()
        grp_name = grp.name
        with H5FileLayout(self.filename) as lay:
            if grp_name in lay:
                issues.append(lay[grp_name].check(grp, recursive=recursive))
            else:
                raise KeyError(f'Group {grp_name} does not exist in layout')
        self._issues_list = issues
        return self.n_issues

    def register(self, name=None, overwrite=False) -> pathlib.Path:
        """Copy file to user data dir"""
        if name is None:
            trg = UserDir['layouts'] / self.filename.name
        else:
            trg = UserDir['layouts'] / name
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Target file already exists: {trg}')
        print(f'copying here: {trg}')
        return shutil.copy2(self.filename, trg)

    @staticmethod
    def get_registered() -> List[pathlib.Path]:
        """Return sorted list of layout HDF files"""
        return sorted(UserDir['layouts'].glob('*'))

    @staticmethod
    def print_registered() -> None:
        """Return sorted list of standard names files"""
        print(f'@ {UserDir["layouts"]}:')
        for f in H5Layout.get_registered():
            print(f' > {f.stem}')

# # @register_standard_attribute(H5File, name='layout')
# class LayoutAttribute:
#     """Layout attribute"""
#
#     def set(self, layout: Union[str, Path, H5Layout]) -> None:
#         """Set layout"""
#         if isinstance(layout, str):
#             _layout = H5Layout.load_registered(layout)
#         elif isinstance(layout, Path):
#             _layout = H5Layout(layout)
#         elif isinstance(layout, H5Layout):
#             _layout = layout
#         else:
#             raise TypeError('Unexpected type for layout. Expect str, pathlib.Path or H5Layout but got '
#                             f'{type(layout)}')
#         self._layout = _layout
#
#     def get(self) -> H5Layout:
#         """Get layout"""
#         return self._layout
#
#     def delete(self) -> None:
#         """Get layout attribute"""
#         self.attrs.__delitem__('layout')
