"""

Contains the core classes that are wrapped around the
h5py interface (around HDF5 files)

"""

import datetime
import json
import logging
import os
import shutil
import warnings
from pathlib import Path
from typing import Dict
from typing import List

import h5py
import numpy as np
import pint_xarray
import xarray as xr
import yaml
from IPython.display import HTML, display
from h5py._hl.base import phil, with_phil
from h5py._objects import ObjectID
from pint_xarray import unit_registry as ureg
from tqdm import tqdm

from . import config
from ._hdf_constants import H5_DIM_ATTRS
from .html_repr import h5file_html_repr
from .. import __version__, user_data_dir, utils, conventions
from ..x2hdf import xr2hdf

logger = logging.getLogger(__package__)

# keep this line, otherwise pycharm will remove obsolete import, but it isn't as it enables pint with xarray
assert pint_xarray.__version__ == '0.2.1'
assert xr2hdf.__version__ == '0.1.0'

ureg.default_format = 'C~'


def pop_hdf_attributes(attrs: Dict) -> dict:
    """removes HDF attributes like NAME, CLASS, ...."""
    return {k: v for k, v in attrs.items() if k not in H5_DIM_ATTRS}


class WrapperAttributeManager(h5py.AttributeManager):
    """
    Subclass of h5py's Attribute Manager.
    Allows to store dictionaries as json strings and to store a dataset or a group as an
    attribute. The latter uses the name of the object. When __getitem__() is called and
    the name (string) is identified as a dataset or group, then this object is returned.
    """

    def __init__(self, parent, **kwargs):
        """ Private constructor."""
        super().__init__(parent)
        self._h5_group_class = kwargs.pop('_h5_group_class', h5py.Group)
        self._h5_dataset_class = kwargs.pop('_h5_dataset_class', h5py.Dataset)

    @with_phil
    def __getitem__(self, name):
        ret = super(WrapperAttributeManager, self).__getitem__(name)
        if isinstance(ret, str):
            if ret:
                if ret[0] == '{':
                    return json.loads(ret)
                elif ret[0] == '/':  # it may be group or dataset path
                    if isinstance(self._id, h5py.h5g.GroupID):
                        # call like this, otherwise recursive call!
                        _root = self._h5_group_class(self._id)
                    else:
                        _root = self._h5_dataset_class(self._id).rootparent
                    if ret in _root:
                        return _root[ret]
                        # obj = _root[ret]
                        # if isinstance(obj, h5py.Dataset):
                        #     return self._h5_dataset_class(obj.id)
                        # return self._h5_group_class(obj.id)
                    else:
                        return ret
                else:
                    return ret
            else:
                return ret
        else:
            return ret

    @with_phil
    def __setitem__(self, name, value):
        """ Set a new attribute, overwriting any existing attribute.

        The type and shape of the attribute are determined from the data.  To
        use a specific type or shape, or to preserve the type of attribute,
        use the methods create() and modify().
        """
        if name in ('_h5_group_class', '_h5_dataset_class'):
            return super().__setattr__(name, value)

        if isinstance(value, dict):
            _value = json.dumps(value)
        elif isinstance(value, Path):
            _value = str(value)
        elif isinstance(value, (h5py.Dataset, h5py.Group)):
            return self.create(name, data=value.name)
        else:
            _value = value
        self.create(name, data=_value)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        outstr = ''
        adict = dict(self.items())
        key_lens = [len(k) for k in adict.keys()]
        if len(key_lens) == 0:
            return None
        keylen = max([len(k) for k in adict.keys()])
        for k, v in adict.items():
            outstr += f'{k:{keylen}}  {v}\n'
        return outstr[:-1]

    def __getattr__(self, item):
        if item in ('_h5_dataset_class', '_h5_group_class'):
            return self.__getattribute__(item)
        if config.natural_naming:
            if item in self.keys():
                return self[item]
            return super().__getattribute__(item)
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if not isinstance(value, ObjectID):
            self.__setitem__(key, value)
        else:
            super().__setattr__(key, value)


def _is_not_valid_natural_name(instance, name, is_natural_naming_enabled):
    """checks if name is already a function call or a property"""
    if is_natural_naming_enabled:
        if isinstance(name, str):
            return hasattr(instance, name)
        else:
            return hasattr(instance, name.decode("utf-8"))


class H5BaseLayout:
    """class defining the static layout of the HDF5 file"""

    def __init__(self, filename: Path):
        self.filename = Path(filename)
        if not self.filename.exists():
            self.write()

    @property
    def File(self):
        """Returns h5py.File"""
        return h5py.File(self.filename, mode='r')

    def _repr_html_(self):
        preamble = f'<p>Layout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            return h5file_html_repr(h5, max_attr_length=None, preamble=preamble,
                                    build_debug_html_page=False)

    def sdump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        sp_name, sp_shape, sp_unit, sp_desc = eval(config.info_table_spacing)

        with h5py.File(self.filename, mode='r') as h5:
            out = f'Layout File "{self.filename.stem}"\n'
            spaces = ' ' * nspaces

            if not hide_attributes:
                # write attributes:
                for ak, av in h5.attrs.items():
                    if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                        _ak = f'{ak}:'
                        if isinstance(av, (h5py.Dataset, h5py.Group)):
                            _av = av.name
                        else:
                            _av = f'{av}'
                        if len(_av) > sp_desc:
                            _av = f'{_av[0:sp_desc]}...'
                        out += utils._make_italic(f'\n{spaces}a: {_ak:{sp_name}} {_av}')

            grp_keys = [k for k in h5.keys() if isinstance(h5[k], h5py.Group)]
            if not grp_only:
                dataset_names = [k for k in h5.keys() if isinstance(h5[k], h5py.Dataset)]
                for dataset_name in dataset_names:
                    varname = utils._make_bold(os.path.basename(
                        h5[dataset_name].name))
                    # shape = h5[dataset_name].shape
                    # units = h5[dataset_name].attrs.get('units')
                    # if units is None:
                    #     units = 'NA'
                    # else:
                    #     if units == ' ':
                    #         units = '-'
                    # out += f'\n{spaces}{varname:{sp_name}} {str(shape):<{sp_shape}}  {units:<{sp_unit}}'
                    out += f'\n{spaces}{varname:{sp_name}} '

                    if not hide_attributes:
                        # write attributes:
                        for ak, av in h5[dataset_name].attrs.items():
                            if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                                _ak = f'{ak}:'
                                if isinstance(av, (h5py.Dataset, h5py.Group)):
                                    _av = av.name
                                else:
                                    _av = f'{av}'
                                if len(_av) > sp_desc:
                                    _av = f'{av[0:sp_desc]}...'
                                out += utils._make_italic(
                                    f'\n\t{spaces}a: {_ak:{sp_name}} {_av}')
                out += '\n'
            nspaces += 2
            for k in grp_keys:
                _grp_name = utils._make_italic(utils._make_bold(f'{spaces}/{k}'))
                _grp_long_name = h5[k].long_name
                if grp_only:
                    if _grp_long_name is None:
                        out += f'\n{_grp_name}'
                    else:
                        out += f'\n{_grp_name}  ({h5[k].long_name})'
                else:
                    if _grp_long_name is None:
                        out += f'{_grp_name}'
                    else:
                        out += f'{_grp_name}  ({h5[k].long_name})'

                out += h5[k].info(ret=True, nspaces=nspaces, grp_only=grp_only,
                                  color_code_verification=color_code_verification,
                                  hide_attributes=hide_attributes)
            if ret:
                return out
            else:
                print(out)

    def dump(self, max_attr_length=None, **kwargs):
        """dumps the layout to the screen (for jupyter notebooks)"""
        build_debug_html_page = kwargs.pop('build_debug_html_page', False)
        preamble = f'<p>Layout File "{self.filename.stem}"</p>\n'
        with h5py.File(self.filename, mode='r') as h5:
            display(HTML(h5file_html_repr(h5, max_attr_length, preamble=preamble,
                                          build_debug_html_page=build_debug_html_page)))

    def write(self):
        """write the static layout file to user data dir"""
        if not self.filename.parent.exists():
            self.filename.parent.mkdir(parents=True)
        logger.debug(
            f'Layout file for class {self.__class__.__name__} is written to {self.filename}')
        with h5py.File(self.filename, mode='w') as h5:
            h5.attrs['__h5rdmtoolbox_version__'] = '__version of this package'
            h5.attrs['creation_time'] = '__time of file creation'
            h5.attrs['modification_time'] = '__time of last file modification'

    def check_dynamic(self, root_grp: h5py.Group, silent: bool = False) -> int:
        return 0

    def check_static(self, root_grp: h5py.Group, silent: bool = False):
        return conventions.layout.layout_inspection(root_grp, self.filename, silent=silent)

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


class DatasetValues:
    """helper class to work around xarray"""

    def __init__(self, h5dataset):
        self.h5dataset = h5dataset

    def __getitem__(self, args, new_dtype=None):
        return self.h5dataset.__getitem__(args, new_dtype=new_dtype, nparray=True)

    def __setitem__(self, args, val):
        return self.h5dataset.__setitem__(args, val)


class H5BaseDataset(h5py.Dataset):
    """
    Subclass of h5py.Dataset. It extends the class with 
    practical methods and properties to meet the FAIR
    prcinciples.
    Main additional features:
        - __getitem__ returns xr.Dataset
        - dictionary attributes are allowed
    """

    _h5ds = None
    _h5grp = None

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return WrapperAttributeManager(self,
                                           _h5_dataset_class=self._h5ds,
                                           _h5_group_class=self._h5grp)

    @property
    def rootparent(self):
        """Returns the root group instance."""

        def get_root(parent):
            global found
            found = parent.parent

            def search(parent):
                global found
                parent = parent.parent
                if parent.name == '/':
                    found = parent
                else:
                    _ = search(parent)

            search(parent)
            return found

        return get_root(self.parent)

    @property
    def values(self):
        """avoiding using xarray"""
        return DatasetValues(self)

    def __setitem__(self, key, value):
        if isinstance(value, xr.DataArray):
            self.attrs.update(value.attrs)
            super().__setitem__(key, value.data)
        else:
            super().__setitem__(key, value)

    def __getitem__(self, args, new_dtype=None, nparray=False) -> xr.DataArray:
        """Returns sliced HDF dataset as xr.DataArray.
        By passing nparray=True the return array is forced 
        to be of type np.array and the super method of
        __getitem__ is called. Alternatively, call .values[:,...]"""
        args = args if isinstance(args, tuple) else (args,)
        if nparray:
            return super().__getitem__(args, new_dtype=new_dtype)
        if Ellipsis in args:
            warnings.warn(
                'Ellipsis not supported at this stage. returning numpy array')
            return super().__getitem__(args, new_dtype=new_dtype)
        else:
            arr = super().__getitem__(args, new_dtype=new_dtype)
            attrs = pop_hdf_attributes(self.attrs)

            if 'DIMENSION_LIST' in self.attrs:
                # there are coordinates to attach...

                myargs = [slice(None) for _ in range(self.ndim)]
                for ia, a in enumerate(args):
                    myargs[ia] = a

                # remember the first dimension name for all axis:
                dims_names = [Path(d[0].name).stem if len(
                    d) > 0 else 'None' for d in self.dims]

                coords = {}
                used_dims = []
                for dim, dim_name, arg in zip(self.dims, dims_names, myargs):
                    for iax, _ in enumerate(dim):
                        dim_ds = dim[iax]
                        coord_name = Path(dim[iax].name).stem
                        if dim_ds.ndim == 0:
                            if isinstance(arg, int):
                                coords[coord_name] = xr.DataArray(name=coord_name,
                                                                  dims=(
                                                                  ), data=dim_ds[()],
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                            else:
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=coord_name,
                                                                  data=[
                                                                      dim_ds[()], ],
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                        else:
                            used_dims.append(dim_name)
                            _data = dim_ds[arg]
                            if isinstance(_data, np.ndarray):
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=dim_name,
                                                                  data=_data,
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                            else:
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=(),
                                                                  data=_data,
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))

                used_dims = [dim_name for arg, dim_name in zip(
                    myargs, dims_names) if isinstance(arg, slice)]

                COORDINATES = self.attrs.get('COORDINATES')
                if COORDINATES is not None:
                    if isinstance(COORDINATES, str):
                        COORDINATES = [COORDINATES, ]
                    for c in COORDINATES:
                        if c[0] == '/':
                            _data = self.rootparent[c]
                        else:
                            _data = self.parent[c]
                        _name = Path(c).stem
                        coords.update({_name: xr.DataArray(name=_name, dims=(),
                                                           data=_data,
                                                           attrs=pop_hdf_attributes(self.parent[c].attrs))})

                return xr.DataArray(name=Path(self.name).stem, data=arr, dims=used_dims,
                                    coords=coords, attrs=attrs)
            return xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)

    def set_primary_scale(self, axis, iscale: int):
        """define the axis for which the first scale should be set. iscale is the index
        of the available scales to be set as primary.
        Make sure you have write intent on file"""
        nscales = len(self.dims[axis])
        if iscale >= nscales:
            raise ValueError(
                f'The target scale index "iscale" is out of range [0, {nscales - 1}]')
        backup_scales = self.dims[axis].items()
        for _, ds in backup_scales:
            self.dims[axis].detach_scale(ds)
        ils = [iscale, *[i for i in range(nscales) if i != iscale]]
        for i in ils:
            self.dims[axis].attach_scale(backup_scales[i][1])
        logger.debug(f'new primary scale: {self.dims[axis][0]}')

    # def rearrange_scale(self, dim, inidces):
    #     if dim == None:
    #         for i in range(self.dims):
    #             print('')

    def rename(self, newname):
        """renames the dataset. Note this may be a process that kills your RAM"""
        # hard copy:
        if 'CLASS' and 'NAME' in self.attrs:
            raise RuntimeError(
                'Cannot rename {self.name} because it is a dimension scale!')

        self.parent[newname] = self
        del self.parent[self.name]


class H5BaseGroup(h5py.Group):
    """
    Subclass of h5py.Group. It extends the class with 
    practical methods and properties to meet the FAIR
    prcinciples.
    Main additional features:
        - __getitem__ returns xr.Dataset
        - dictionary attributes are allowed
        - natural naming
        - special dataset creation (e.g. from csv, from image,...)
        - dump() -> pretty representation in jupyter notebooks
    """
    _h5ds = None
    _h5grp = None

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return WrapperAttributeManager(self,
                                           _h5_group_class=self._h5grp,
                                           _h5_dataset_class=self._h5ds)

    @property
    def rootparent(self):
        """Returns the root group instance."""

        def get_root(parent):
            global found
            found = None

            def search(parent):
                global found
                parent = parent.parent
                if parent.name == '/':
                    found = parent
                else:
                    _ = search(parent)

            search(parent)
            return found

        return get_root(self.parent)

    @property
    def datasets(self) -> List[h5py.Dataset]:
        """returns list of the group's datasets"""
        return [v for k, v in self.items() if isinstance(v, h5py.Dataset)]

    @property
    def groups(self):
        """returns list of the group's groups"""
        return [v for v in self.values() if isinstance(v, h5py.Group)]

    @property
    def long_name(self):
        """Returns the attribute long_name. Returns None if it does not exist."""
        return self.attrs.get('long_name')

    @long_name.setter
    def long_name(self, long_name):
        """Writes attribute long_name if passed string is not None"""
        if long_name:
            self.attrs.modify('long_name', long_name)
        else:
            raise TypeError('long_name must not be type None.')

    def __init__(self, _id):
        if isinstance(_id, h5py.Group):
            _id = _id.id
        if isinstance(_id, h5py.h5g.GroupID):
            super().__init__(_id)
        else:
            ValueError('Could not initialize Group. A h5py.h5f.FileID object must be passed')

    def __setitem__(self, name, obj):
        if isinstance(obj, xr.DataArray):
            return obj.hdf.to_group(self, name)
        else:
            super().__setitem__(name, obj)

    def __getitem__(self, name):
        ret = super().__getitem__(name)
        if isinstance(ret, h5py.Dataset):
            return self._h5ds(ret.id)
        elif isinstance(ret, h5py.Group):
            return self._h5grp(ret.id)
        return ret

    def __getattr__(self, item):
        if config.natural_naming:
            if item != '_id':  # needed if running pycharm-debug mode
                try:
                    if item in self:
                        if isinstance(self[item], h5py.Group):
                            return self._h5grp(self[item].id)
                        else:
                            return self._h5ds(self[item].id)
                    else:
                        # try replacing underscores with spaces:
                        _item = item.replace('_', ' ')
                        if _item in self:
                            if isinstance(self[_item], h5py.Group):
                                return self.__class__(self[_item].id)
                            else:
                                return self._h5ds(self[_item].id)
                        else:
                            return super().__getattribute__(item)
                except AttributeError:
                    raise AttributeError(item)
        else:
            return super().__getattribute__(item)

    def __str__(self):
        return self.sdump(ret=True)

    def create_group(self, name, overwrite=None,
                     attrs=None, track_order=None):
        """
        Overwrites parent methods. Additional parameters are "attrs" and "overwrite".
        Besides, it does and behaves the same.

        Parameters
        ----------
        name : str
            Name of group
        overwrite : bool, optional=None
            If the group does not already exist, the new group is written and this parameter has no effect.
            If the group exists and ...
            ... overwrite is None: h5py behaviour is enabled meaning that if a group exists h5py will raise
            ... overwrite is True: group is deleted and rewritten according to method parameters
            ... overwrite is False: group creation has no effect. Existing group is returned.
        attrs : dict, optional
            Attributes of the group, default is None which is an empty dict
        track_order : bool or None
            Track creation order under this group. Default is None.
        """
        if name in self:
            if overwrite is True:
                del self[name]
            elif overwrite is False:
                return self[name]
            else:
                # let h5py.Group raise the error...
                h5py.Group.create_group(self, name, track_order=track_order)

        if _is_not_valid_natural_name(self, name, config.natural_naming):
            raise ValueError(f'The group name "{name}" is not valid. It is an '
                             f'attribute of the class and cannot be used '
                             f'while natural naming is enabled')

        new_subgroup = super().create_group(name, track_order=track_order)

        # new_subgroup = h5py.Group.create_group(self, name, track_order=track_order)
        logger.debug(f'Created group "{name}" at "{self.name}"-level.')

        if attrs:
            for k, v in attrs.items():
                new_subgroup.attrs[k] = v

        return self._h5grp(new_subgroup)

    def create_dataset(self, name, shape=None, dtype=None, data=None,
                       overwrite=None,
                       chunks=None,
                       attrs=None, attach_scales=None,
                       make_scale=False, **kwargs):
        """
        Creates an HDF dataset. Differently to h5py.Dataset, it encourages to
        additionally pass units and long_name or standard_name otherwise a
        warnings are displayed.

        Additional parameters as compared to h5py-method:
            - attach_scales
            - make_scale

        Parameters
        ----------
        name : str
            Name of dataset
        shape : tuple, optiona=None
            Dataset shape. see h5py doc. Default None. Required if data=None.
        dtype : str, optional
            dtype of dataset. see h5py doc. Default is dtype('f')
        data : numpy ndarray, optional
            Provide data to initialize the dataset.  If not used,
            provide shape and optionally dtype via kwargs (see more in
            h5py documentation regarding arguments for create_dataset
        overwrite : bool, optional=None
            If the dataset does not already exist, the new dataset is written and this parameter has no effect.
            If the dataset exists and ...
            ... overwrite is None: h5py behaviour is enabled meaning that if a dataset exists h5py will raise
            ... overwrite is True: dataset is deleted and rewritten according to method parameters
            ... overwrite is False: dataset creation has no effect. Existing dataset is returned.
        chunks : bool or according to h5py.File.create_dataset documentation
            Needs to be True if later resizing is planned
        attrs : dict, optional=None
            Allows to set attributes directly after dataset creation. Default is
            None, which is an empty dict
        attach_scales : tuple, optional=None
            Tuple defining the datasets to attach scales to. Content of tuples are
            internal hdf paths. If an axis should not be attached to any axis leave it
            empty (''). Default is ('',) which attaches no scales
            Note: internal hdf5 path is relative w.r.t. this dataset, so be careful
            where to create the dataset and to which to attach the scales!
            Also note, that if data is a xr.DataArray and attach_scales is not None,
            coordinates of xr.DataArray are ignored and only attach_scales is
            considered.
        make_scale: bool, optional=False
            Makes this dataset scale. The parameter attach_scale must be uses, thus be None.

        **kwargs
            see documentation of h5py.File.create_dataset

        Returns
        -------
        ds : h5py.Dataset
            created dataset
        """
        if name:
            if name in self:
                if overwrite is True:
                    del self[name]  # delete existing dataset
                elif overwrite is False:
                    return self[name]  # return existing dataset
                else:
                    # let h5py run into the error...
                    super().create_dataset(name, shape, dtype, data, **kwargs)

        # take compression from kwargs or config:
        compression = kwargs.pop('compression', config.hdf_compression)
        compression_opts = kwargs.pop('compression_opts', config.hdf_compression_opts)
        if shape is not None:
            if len(shape) == 0:
                compression, compression_opts, chunks = None, None, None

        if attrs is None:
            attrs = {}

        if isinstance(data, xr.DataArray):
            attrs.update(data.attrs)

            dset = data.hdf.to_group(self, name=name, overwrite=overwrite,
                                     compression=compression,
                                     compression_opts=compression_opts, attrs=attrs)

            # for k, v in attrs.items():
            #     dset.attrs.modify(k, v)

            return dset

        if attach_scales is None:
            # maybe there's a typo:
            attach_scales = kwargs.pop('attach_scale', None)

        if name:
            if _is_not_valid_natural_name(self, name, config.natural_naming):
                raise ValueError(f'The dataset name "{name}" is not a valid. It is an '
                                 f'attribute of the class and cannot be used '
                                 f'while natural naming is enabled')

        if isinstance(shape, np.ndarray):  # need if no keyword is used
            data = shape
            shape = None

        if data is not None:
            _data = np.asarray(data)
        else:
            _data = data

        _maxshape = kwargs.get('maxshape', shape)

        if attach_scales:
            if not isinstance(attach_scales, (list, tuple)):
                attach_scales = (attach_scales,)
            if any([True for a in attach_scales if a]) and make_scale:
                raise ValueError(
                    'Cannot make scale and attach scale at the same time!')

        logger.debug(
            f'Creating H5DatasetModel "{name}" in "{self.name}" with maxshape {_maxshape} " '
            f'and using compression "{compression}" with opt "{compression_opts}"')

        if _data is not None:
            if _data.ndim == 0:
                _ds = super().create_dataset(name, shape=shape, dtype=dtype, data=_data,
                                             **kwargs)
            else:
                _ds = super().create_dataset(name, shape=shape, dtype=dtype, data=_data,
                                             chunks=chunks,
                                             compression=compression,
                                             compression_opts=compression_opts,
                                             **kwargs)
        else:
            _ds = super().create_dataset(name, shape=shape, dtype=dtype, data=_data,
                                         compression=compression,
                                         compression_opts=compression_opts,
                                         chunks=chunks,
                                         **kwargs)

        ds = self._h5ds(_ds.id)

        if attrs:
            for k, v in attrs.items():
                ds.attrs[k] = v

        # make scale
        if make_scale:
            ds.make_scale()

        # attach scales:
        if attach_scales:
            for i, s in enumerate(attach_scales):
                if s:
                    if not isinstance(s, (tuple, list)):
                        _s = (s,)
                    else:
                        _s = s
                    for ss in _s:
                        if isinstance(ss, h5py.Dataset):
                            ds.dims[i].attach_scale(ss)
                        else:
                            if ss in self:
                                ds.dims[i].attach_scale(self[ss])
                            else:
                                raise ValueError(f'Cannot assign {ss} to {ds.name} because it seems not '
                                                 f'to exist!')

        return self._h5ds(ds.id)

    def create_datasets_from_csv(self, csv_filename, shape=None, overwrite=False,
                                 combine_opt='stack', axis=0, chunks=None, **kwargs):
        """
        Reads data from a csv and adds a dataset according to column names.
        Pandas.read_csv() is used. So all arguments for this function may be passed.

        Parameters
        ----------
        csv_filename : Path or list of Path
            CSV filename or list of filenames.
            If list is passed, structure must be the same for all
        shape : tuple
            Target shape of data. Default is None.
            As data is column data. it can be reshaped to desired shape.
        overwrite : bool
            Whether to overwrite an existing dataset. Default is False.
        combine_opt : str
            Defines the method how to combine data from multiple files.
            Therefore, csv_filename must be a list. Default is stack.
            If set, make sure, axis is set accordingly.
            Other input can be concatenate
        axis : int
            Stacking or concatenating according to combine_opt along
            if multiple csv files are passes
        chunks : tuple
            Chunking option for HDF5 dataset creation. Equal for all
            datasets

        Returns
        -------
        ds : HDF Dataset
            The created dataset

        """
        from pandas import read_csv as pd_read_csv
        if 'names' in kwargs.keys():
            if 'header' not in kwargs.keys():
                raise RuntimeError('if you pass names also pass header=...')

        if isinstance(csv_filename, (list, tuple)):
            # depending on the meaning of multiple csv_filename axis can be 0 (z-plane)
            # or 1 (time-plane)
            axis = kwargs.pop('axis', 0)
            csv_fname = csv_filename[0]
            is_single_file = False
        elif isinstance(csv_filename, (str, Path)):
            is_single_file = True
            csv_fname = csv_filename
        else:
            raise ValueError(
                f'Wrong input for "csv_filename: {type(csv_filename)}')

        df = pd_read_csv(csv_fname, **kwargs)
        # ncols = len(df.columns)

        compression, compression_opts = config.hdf_compression, config.hdf_compression_opts

        if is_single_file:
            for variable_name in df.columns:
                ds_name = utils.remove_special_chars(str(variable_name))
                data = df[str(variable_name)].values.reshape(shape)
                try:
                    self.create_dataset(name=ds_name,
                                        data=data,
                                        overwrite=overwrite, compression=compression,
                                        compression_opts=compression_opts)
                except RuntimeError as e:
                    logger.error(
                        f'Could not read {variable_name} from csv file due to: {e}')
        else:
            _data = df[df.columns[0]].values.reshape(shape)
            nfiles = len(csv_filename)
            for variable_name in df.columns:
                ds_name = utils.remove_special_chars(str(variable_name))
                if combine_opt == 'concatenate':
                    _shape = list(_data.shape)
                    _shape[axis] = nfiles
                    self.create_dataset(name=ds_name, shape=_shape,
                                        compression=compression,
                                        compression_opts=compression_opts,
                                        chunks=chunks)
                elif combine_opt == 'stack':
                    if axis == 0:
                        self.create_dataset(name=ds_name, shape=(nfiles, *_data.shape),
                                            compression=compression,
                                            compression_opts=compression_opts,
                                            chunks=chunks)
                    elif axis == 1:
                        self.create_dataset(name=ds_name, shape=(_data.shape[0], nfiles, *_data.shape[1:]),
                                            compression=compression,
                                            compression_opts=compression_opts,
                                            chunks=chunks)
                    else:
                        raise ValueError('axis must be 0 or -1')

                else:
                    raise ValueError(
                        f'"combine_opt" must be "concatenate" or "stack", not {combine_opt}')

            for i, csv_fname in enumerate(csv_filename):
                df = pd_read_csv(csv_fname, **kwargs)
                for c in df.columns:
                    ds_name = utils.remove_special_chars(str(c))
                    data = df[str(c)].values.reshape(shape)

                    if combine_opt == 'concatenate':
                        if axis == 0:
                            self[ds_name][i, ...] = data[0, ...]
                        elif axis == 1:
                            self[ds_name][:, i, ...] = data[0, ...]
                    elif combine_opt == 'stack':
                        if axis == 0:
                            self[ds_name][i, ...] = data
                        elif axis == 1:
                            self[ds_name][:, i, ...] = data

    def create_dataset_from_image(self, img_filename, name=None,
                                  overwrite=False, dtype=None, ufunc=None,
                                  axis=0, **kwargs):
        """
        Creates a dataset for a single or multiple files. If a list of filenames is passed
        All images are stacked (thus shape of all images must be equal!)

        Parameters
        ----------
        img_filename : {Path, list}
            Image filename or list of image file names. See also axis in case of multiple files
        name : str
            Name of create dataset
        units : string
            Unit of image. Typically, pixels which is also default.
        long_name : str
            long_name of dataset
        overwrite : bool
            Whether to overwrite an existing dataset with this name
        dtype : str
            Data type used for hdf dataset creation
        axis: int, optional
            Axis along which to stack images in case of multiple ones.
            Valid axis values are either 0 or -1.
            Default is 0.

        Returns
        -------
        ds : hdf Dataset
            The created dataset.

        """

        # take compression from kwargs or config:
        _compression, _compression_opts = config.hdf_compression, config.hdf_compression_opts
        compression = kwargs.pop('compression', _compression)
        compression_opts = kwargs.pop('compression_opts', _compression_opts)
        ds = None

        if isinstance(img_filename, (str, Path)):
            if name is None:
                name = utils.remove_special_chars(
                    os.path.basename(img_filename).rsplit('.', 1)[0])
            img = utils.load_img(img_filename)
            if ufunc is not None:
                if isinstance(ufunc, (list, tuple)):
                    _ufunc = ufunc[0]
                    _ufunc_param = ufunc[1:]
                    raise NotImplementedError(
                        'user function with parameter not implemented yet')
                elif hasattr(ufunc, '__call__'):
                    try:
                        img_processed = ufunc(img)
                    except RuntimeError as e:
                        raise logger.error(f'Failed running user function {ufunc} '
                                           f'with this error: {e}')
                    if img_processed is not None:
                        ds = self.create_dataset(name=name, data=img_processed,
                                                 overwrite=overwrite,
                                                 dtype=dtype, compression=compression,
                                                 compression_opts=compression_opts,
                                                 **kwargs)
                        return ds

            else:
                ds = self.create_dataset(name=name, data=img,
                                         overwrite=overwrite, dtype=dtype,
                                         compression=compression, compression_opts=compression_opts)
                return ds
        elif isinstance(img_filename, (list, tuple)):
            if not name:  # take the first image name
                name = os.path.commonprefix(img_filename)
            nimg = len(img_filename)

            if ufunc is not None:  # user function given. final size of dataset unknown
                if isinstance(ufunc, (list, tuple)):
                    _ufunc = ufunc[0]
                    _ufunc_param = ufunc[1:]
                    # raise NotImplementedError('user function with parameter not implemented yet')
                else:
                    _ufunc = ufunc
                    _ufunc_param = list()

                if hasattr(_ufunc, '__call__'):
                    for i, img_fname in tqdm(enumerate(img_filename)):
                        img = utils.load_img(img_fname)
                        img_shape = img.shape
                        try:
                            if hasattr(ufunc, '__call__'):
                                img_processed = _ufunc(img)
                            else:
                                img_processed = _ufunc(img, *_ufunc_param)
                        except RuntimeError as e:
                            raise logger.error(f'Failed running user function {_ufunc} '
                                               f'with this error: {e}')
                        if img_processed is not None:
                            if name in self:  # dataset already exists
                                ds = self[name]
                                ds_shape = list(ds.shape)
                                if axis == 0:
                                    ds_shape[0] += 1
                                else:
                                    ds_shape[-1] += 1
                                ds.resize(tuple(ds_shape))
                                if axis == 0:
                                    ds[-1, ...] = img_processed
                                else:
                                    ds[..., -1] = img_processed
                            else:  # dataset must be created first
                                if axis == 0:
                                    dataset_shape = (1, *img_shape)
                                    _maxshape = (None, *img_shape)
                                    _chunks = (1, *img_shape)
                                elif axis == -1:
                                    dataset_shape = (*img_shape, 1)
                                    _maxshape = (*img_shape, None)
                                    _chunks = (*img_shape, 1)
                                else:
                                    raise ValueError(
                                        f'Other axis than 0 or -1 not accepted!')
                                ds = self.create_dataset(name, shape=dataset_shape, overwrite=overwrite,
                                                         maxshape=_maxshape, dtype=dtype, compression=compression,
                                                         compression_opts=compression_opts, chunks=_chunks)
                                if axis == 0:
                                    ds[0, ...] = img
                                else:
                                    ds[..., 0] = img
                else:
                    raise ValueError(f'Wrong ufunc type: {type(ufunc)}')
                return ds
            else:  # no user function passed. shape of dataset is known and can be pre-allocated
                img = utils.load_img(img_filename[0])
                img_shape = img.shape
                if axis == 0:
                    dataset_shape = (nimg, *img_shape)
                elif axis == -1:
                    dataset_shape = (*img_shape, nimg)
                else:
                    raise ValueError(f'Other axis than 0 or -1 not accepted!')

                # pre-allocate dataset with shape:
                ds = self.create_dataset(name, shape=dataset_shape, overwrite=overwrite,
                                         dtype=dtype, compression=compression, compression_opts=compression_opts)

                # fill dataset with data:
                if ds is not None:
                    if axis == 0:
                        ds[0, ...] = img
                        for i, img_fname in tqdm(enumerate(img_filename[1:]), unit='file', desc='processing images'):
                            img = utils.load_img(img_fname)
                            if img.shape == img_shape:
                                ds[i + 1, ...] = img
                            else:
                                logger.critical(
                                    f'Shape of {img_fname} has wrong shape {img.shape}. Expected shape: {img_shape}'
                                    f' Dataset will be deleted again!')
                                del self[ds.name]
                    elif axis == -1:
                        ds[..., 0] = img
                        for i, img_fname in tqdm(enumerate(img_filename[1:]), unit='file', desc='processing images'):
                            img = utils.load_img(img_filename[0])
                            if img.shape == img_shape:
                                ds[..., i + 1] = img
                            else:
                                logger.critical(
                                    f'Shape if {img_fname} has wrong shape {img.shape}. Expected shape: {img_shape}'
                                    f' Dataset will be deleted again!')
                                del self[ds.name]
                    return ds
                else:
                    logger.critical(
                        'Could not create dataset because it already exists and overwritr=False.')

    def create_dataset_from_xarray_dataset(self, dataset: xr.Dataset) -> None:
        """creates the xr.DataArrays of the passed xr.Dataset, writes all attributes
        and handles the dimension scales."""
        """creates the xr.DataArrays of the passed xr.Dataset, writes all attributes
        and handles the dimension scales."""
        ds_coords = {}
        for coord in dataset.coords.keys():
            ds = self.create_dataset(coord, data=dataset.coords[coord].values,
                                     attrs=dataset.coords[coord].attrs, overwrite=False)
            ds.make_scale()
            ds_coords[coord] = ds
        for data_var in dataset.data_vars.keys():
            ds = self.create_dataset(data_var, data=dataset[data_var].values,
                                     attrs=dataset[data_var].attrs, overwrite=False)
            for idim, dim in enumerate(dataset[data_var].dims):
                ds.dims[idim].attach_scale(ds_coords[dim])

    def create_external_link(self, name, filename, path, overwrite=False,
                             keep_relative=False):
        """
        Creates a group which points to group in another file. See h5py.ExternalLink()
        for more information.

        Parameters
        ----------
        name : str
            Group name that is created in this hdf file
        filename : Path
            File name of remote HDF5 file
        path : Path
            HDF5 internal path to group that should be linked to
        overwrite : bool, optional
            Whether to overwrite an existing dataset. Default is False.
        keep_relative : bool, optional
            If true, path is untouched. If False, it os.path.abspath() is applied.
        """
        logger.debug(f'Trying to create external link group with name "{name}". Source is filename="{filename}" and '
                     f'path="{path}". Overwrite is set to {overwrite} and keep_relative to {keep_relative}')
        if not keep_relative:
            filename = os.path.abspath(filename)
        if name in self:
            if overwrite:
                del self[name]
                self[name] = h5py.ExternalLink(filename, path)
                return self[name]
            else:
                logger.debug(f'External link {name} was not created. A Dataset with this name'
                             f' already exists and overwrite is set to False! '
                             f'You can pass overwrite=True in order to overwrite the '
                             f'existing dataset')
                raise ValueError(f'External link {name} was not created. A Dataset with this name'
                                 f' already exists and overwrite is set to False! '
                                 f'You can pass overwrite=True in order to overwrite the '
                                 f'existing dataset')
        else:
            self[name] = h5py.ExternalLink(filename, path)
            return self[name]

    def from_yaml(self, yamlfile: Path):
        """creates groups, datasets and attributes defined in a yaml file. Creations
        is performed relative to the current group level.

        Note the required yaml file structure, e.g.
        datasets:
          grp/supgrp/y:
            data: 2
            standard_name: y_coordinate
            units: m
            overwrite: True
        groups:
          grp/supgrp:
            attrs:
        attrs:
          grp/supgrp:
            comment: This is a group comment
        """
        with open(yamlfile, 'r') as f:
            data = yaml.safe_load(f)

        if 'groups' in data:
            for grp in data['groups']:
                kwargs = data['groups'][grp]
                logger.debug(
                    f"dumping group defined by yaml file. name: {grp}, kwargs: {kwargs}")
                try:
                    self.create_group(grp, **kwargs)
                except Exception as e:
                    logger.critical(
                        f'Group {grp} from yaml definition not written due to {e}')

        if 'datasets' in data:
            for ds in data['datasets']:
                kwargs = data['datasets'][ds]
                logger.debug(
                    f"dumping dataset defined by yaml file. name: {ds}, kwargs: {kwargs}")
                try:
                    self.create_dataset(ds, **kwargs)
                except Exception as e:
                    logger.critical(
                        f'Dataset {ds} from yaml definition not written due to {e}')

        if 'attrs' in data:
            for objname in data['attrs']:
                kwargs = data['attrs'][objname]
                logger.debug(
                    f"dumping attribute data defined by yaml file for {objname}: {kwargs}")
                for ak, av in data['attrs'][objname].items():
                    try:
                        self[objname].attrs[ak] = av
                    except Exception as e:
                        logger.critical(
                            f'Could not write attribute {ak} to {objname} due to {e}')

    def get_by_attribute(self, attribute_name, attribute_value=None,
                         h5type=None, recursive=True):
        """returns the object(s) (dataset or group) with a certain attribute name
        and if specified a specific value.
        Via h5type it can be filtered for only datasets or groups

        Parameters
        ----------
        attribute_name: str
            Name of the attribute
        attribute_value: any, optional=None
            Value of the attribute. If None, the value is not checked
        h5type: str, optional=None
            If specified, looking only for groups or datasets.
            To look only for groups, pass 'group' or 'grp'.
            To look only for datasets, pass 'dataset' or 'ds'.
            Default is None, which looks in both object types.
        recursive: bool, optional=True
            If True, scans recursively through all groups below current.

        Returns
        ------
        names: List[str]
            List of dataset and/or group names
        """
        names = []

        def _get_grp(name, node):
            if isinstance(node, h5py.Group):
                if attribute_name in node.attrs:
                    if attribute_value is None:
                        names.append(name)
                    else:
                        if node.attrs[attribute_name] == attribute_value:
                            names.append(name)

        def _get_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if attribute_name in node.attrs:
                    if attribute_value is None:
                        names.append(name)
                    else:
                        if node.attrs[attribute_name] == attribute_value:
                            names.append(name)

        def _get_ds_grp(name, node):
            if attribute_name in node.attrs:
                if attribute_value is None:
                    names.append(name)
                else:
                    if node.attrs[attribute_name] == attribute_value:
                        names.append(name)

        if recursive:
            if h5type is None:
                self.visititems(_get_ds_grp)
            elif h5type.lower() in ('dataset', 'ds'):
                self.visititems(_get_ds)
            elif h5type.lower() in ('group', 'grp', 'gr'):
                self.visititems(_get_grp)
        else:
            if h5type is None:
                for ds in self.values():
                    if attribute_name in ds.attrs:
                        if ds.attrs[attribute_name] == attribute_value:
                            names.append(ds)
            elif h5type.lower() in ('dataset', 'ds'):
                for ds in self.values():
                    if isinstance(ds, h5py.Dataset):
                        if attribute_name in ds.attrs:
                            if ds.attrs[attribute_name] == attribute_value:
                                names.append(ds)
            elif h5type.lower() in ('group', 'grp', 'gr'):
                for ds in self.values():
                    if isinstance(ds, h5py.Group):
                        if attribute_name in ds.attrs:
                            if ds.attrs[attribute_name] == attribute_value:
                                names.append(ds)
        return names

    def get_datasets_by_attribute(self, attribute_name, attribute_value=None, recursive=True):
        return self.get_by_attribute(attribute_name, attribute_value, 'dataset', recursive)

    def get_groups_by_attribute(self, attribute_name, attribute_value=None, recursive=True):
        return self.get_by_attribute(attribute_name, attribute_value, 'group', recursive)

    def _get_obj_names(self, obj_type, recursive):
        """returns all names of specified object type
        in this group and if recursive==True also
        all below"""
        _names = []

        def _get_obj_name(name, node):
            if isinstance(node, obj_type):
                _names.append(name)

        if recursive:
            self.visititems(_get_obj_name)
            return _names
        return [g for g in self.keys() if isinstance(self[g], obj_type)]

    def get_group_names(self, recursive=True):
        """returns all group names in this group and if recursive==True also
        all below"""
        return self._get_obj_names(h5py.Group, recursive)

    def get_dataset_names(self, recursive=True):
        """returns all dataset names in this group and if recursive==True also
        all below"""
        return self._get_obj_names(h5py.Dataset, recursive)

    def dump(self, max_attr_length=None, **kwargs):
        """Outputs xarray-inspired _html representation of the file content if a
        notebook environment is used"""
        if max_attr_length is None:
            max_attr_length = config.html_max_string_length
        if self.name == '/':
            pre_text = f'<p>{Path(self.filename).name}</p>\n'
        else:
            pre_text = f'<p>Group: {self.name}</p>\n'
        build_debug_html_page = kwargs.pop('build_debug_html_page', False)
        display(HTML(h5file_html_repr(self, max_attr_length, preamble=pre_text,
                                      build_debug_html_page=build_debug_html_page)))

    def _repr_html_(self):
        return h5file_html_repr(self, config.html_max_string_length)

    def sdump(self, ret=False, nspaces=0, grp_only=False, hide_attributes=False, color_code_verification=True):
        """
        Generates string representation of the hdf5 file content (name, shape, units, long_name)

        Parameters
        ----------
        ret : bool, optional
            Whether to return the information string or
            print it. Default is False, which prints the string
        nspaces : int, optional
            number of spaces used as indentation. Default is 0
        grp_only : bool, optional=False
            Only gets group information
        hide_attributes : bool, optional=False
            Hides attributes in output string.
        color_code_verification: bool, optional=True

        Returns
        -------
        out : str
            Information string if asked

        Notes
        -----
        Working under notebooks, explore() gives a greater representation, including attributes.
        """

        def apply_color(_str, flag=1):
            if color_code_verification:
                if flag:
                    return utils._oktext(_str)
                else:
                    return utils._failtext(_str)
            else:
                return _str

        sp_name, sp_shape, sp_unit, sp_desc = eval(
            config.info_table_spacing)
        # out = f"Group ({__class__.__name__}): {self.name}\n"
        out = ''
        spaces = ' ' * nspaces

        if self.name == '/':  # only for root
            if isinstance(self, h5py.Group):
                out += f'> {self.__class__.__name__}: Group name: {self.name}.\n'
            else:
                out += f'> {self.__class__.__name__}: {self.filename}.\n'

            # if isinstance(self, h5py.File):
            #     nissues = self.check(silent=True)
            #     if nissues > 0:
            #         out += apply_color(f'> File has {nissues} issues.', 0)
            #     else:
            #         out += apply_color(f'> File has {nissues} issues.', 1)
            #     out += '\n'

        if not hide_attributes:
            # write attributes:
            for ak, av in self.attrs.items():
                if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                    _ak = f'{ak}:'
                    if isinstance(av, (h5py.Dataset, h5py.Group)):
                        _av = av.name
                    else:
                        _av = f'{av}'
                    if len(_av) > sp_desc:
                        _av = f'{_av[0:sp_desc]}...'
                    out += utils._make_italic(f'\n{spaces}a: {_ak:{sp_name}} {_av}')

        grp_keys = [k for k in self.keys() if isinstance(self[k], h5py.Group)]
        if not grp_only:
            dataset_names = [k for k in self.keys(
            ) if isinstance(self[k], h5py.Dataset)]
            for dataset_name in dataset_names:
                varname = utils._make_bold(os.path.basename(
                    self._h5ds(self[dataset_name]).name))
                shape = self[dataset_name].shape
                units = self[dataset_name].units
                if units is None:
                    units = 'NA'
                else:
                    if units == ' ':
                        units = '-'

                out += f'\n{spaces}{varname:{sp_name}} {str(shape):<{sp_shape}}  {units:<{sp_unit}}'

                if not hide_attributes:
                    # write attributes:
                    for ak, av in self[dataset_name].attrs.items():
                        if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                            _ak = f'{ak}:'
                            if isinstance(av, (h5py.Dataset, h5py.Group)):
                                _av = av.name
                            else:
                                _av = f'{av}'
                            if len(_av) > sp_desc:
                                _av = f'{_av[0:sp_desc]}...'
                            out += utils._make_italic(
                                f'\n\t{spaces}a: {_ak:{sp_name}} {_av}')
            out += '\n'
        nspaces += 2
        for k in grp_keys:
            _grp_name = utils._make_italic(utils._make_bold(f'{spaces}/{k}'))
            _grp_long_name = self[k].long_name
            if grp_only:
                if _grp_long_name is None:
                    out += f'\n{_grp_name}'
                else:
                    out += f'\n{_grp_name}  ({self[k].long_name})'
            else:
                if _grp_long_name is None:
                    out += f'{_grp_name}'
                else:
                    out += f'{_grp_name}  ({self[k].long_name})'

            if isinstance(self, h5py.Group):
                out += self[k].sdump(ret=True, nspaces=nspaces, grp_only=grp_only,
                                     color_code_verification=color_code_verification,
                                     hide_attributes=hide_attributes)
            # else:
            #     out += self[k].info(ret=True, nspaces=nspaces, grp_only=grp_only,
            #                         color_code_verification=color_code_verification,
            #                                         hide_attributes=hide_attributes)
        if ret:
            return out
        else:
            print(out)


class H5Base(h5py.File, H5BaseGroup):
    """The core wrapper around h5py.File.
    Layout file can be defined, pretty dumping data to the screen,
    and inspection are among the main methods of the class.
    """

    Layout: H5BaseLayout = H5BaseLayout(Path.joinpath(user_data_dir, f'layout/H5Base.hdf'))

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return WrapperAttributeManager(self,
                                           _h5_dataset_class=self._h5ds,
                                           _h5_group_class=self._h5grp)

    @property
    def version(self):
        """returns version stored in file"""
        return self.attrs.get('__h5rdmtoolbox_version__')

    @property
    def creation_time(self) -> datetime.datetime:
        """returns creation time from file"""
        from dateutil import parser
        return parser.parse(self.attrs.get('creation_time'))

    @property
    def filesize(self):
        """
        Returns file size in bytes (or other units if asked)

        Returns
        -------
        _bytes
            file size in byte

        """
        _bytes = os.path.getsize(self.filename)
        return _bytes * ureg.byte

    def __init__(self, name: Path = None, mode='r', driver=None, libver=None, userblock_size=None,
                 swmr=False, rdcc_nslots=None, rdcc_nbytes=None, rdcc_w0=None,
                 track_order=None, fs_strategy=None, fs_persist=False, fs_threshold=1,
                 **kwds):
        """
        Subclass of h5py.File with additional features.
        """
        now_time_str = utils.generate_time_str(datetime.datetime.now(), conventions.datetime_str)
        if name is None:
            logger.debug("An empty H5File class is initialized")
            name = utils.touch_tmp_hdf5_file()
            # mode must be at w or r+ because there is no filename yet (temp willl be created)
            mode = 'r+'
        elif isinstance(name, ObjectID):
            pass
        elif not isinstance(name, (str, Path)):
            raise ValueError(
                f'It seems that no proper file name is passed: type of {name} is {type(name)}')
        else:
            if mode == 'r+':
                if not Path(name).exists():
                    # "touch" the file, so it exists
                    with h5py.File(name, mode='w', driver=driver,
                                   libver=libver, userblock_size=userblock_size, swmr=swmr,
                                   rdcc_nslots=rdcc_nslots, rdcc_nbytes=rdcc_nbytes, rdcc_w0=rdcc_w0,
                                   track_order=track_order, fs_strategy=fs_strategy, fs_persist=fs_persist,
                                   fs_threshold=fs_threshold,
                                   **kwds):
                        pass

        if not isinstance(name, ObjectID):
            self.hdf_filename = Path(name)
        super().__init__(name=name, mode=mode, driver=driver,
                         libver=libver, userblock_size=userblock_size, swmr=swmr,
                         rdcc_nslots=rdcc_nslots, rdcc_nbytes=rdcc_nbytes, rdcc_w0=rdcc_w0,
                         track_order=track_order, fs_strategy=fs_strategy, fs_persist=fs_persist,
                         fs_threshold=fs_threshold,
                         **kwds)

        this_class_name = type(self).__name__
        self.layout_file = Path.joinpath(
            user_data_dir, f'{this_class_name}_Layout.hdf')

        # update file creation/modification times and h5wrapper version
        if self.mode != 'r':
            if 'creation_time' not in self.attrs:
                self.attrs['creation_time'] = now_time_str
            self.attrs['modification_time'] = now_time_str
            self.attrs['__h5rdmtoolbox_version__'] = __version__
            self.attrs['__wrcls__'] = self.__class__.__name__

    def __setitem__(self, name, obj):
        if isinstance(obj, xr.DataArray):
            return obj.hdf.to_group(self, name)
        super().__setitem__(name, obj)

    def use_as_layout_file(self):
        """copies the current instance to user tmp folder and
        replaces existing layout file"""
        shutil.copy(self.filename, self.Layout.filename)

    def check(self, silent: bool = False) -> int:
        """runs a complete check (static+dynamic) and returns number of issues"""
        return self.Layout.check(self['/'], silent)

    def special_inspect(self, silent: bool = False) -> int:
        """Optional special inspection, e.g. conditional checks."""
        return 0

    def moveto(self, target_dir: Path, filename: Path = None, overwrite: bool = False) -> Path:
        """
        moves the file to a new location and optionally renames the file if asked.

        Parameters
        ----------
        target_dir : str
            Target directory to which file is moved.
        filename : str, optional=None
            Filename to be used. If None (default) original filename is not
            changed
        overwrite : bool
            Whether to overwrite an existing name at target_dir with name
            filename

        Return
        ------
        new_filepath : str
            Path to new file location
        """
        target_dir = Path(target_dir)
        if filename is None:
            filename = self.hdf_filename.name
        else:
            filename = Path(filename)
        trg = Path.joinpath(target_dir, filename)
        if trg.exists() and not overwrite:
            raise FileExistsError(f'The target file "{trg}" already exists and overwriting is set to False.'
                                  ' Not moving the file!')
        logger.debug(f'Moving file {self.hdf_filename} to {trg}')

        if not target_dir.exists():
            Path.mkdir(Path(target_dir), parents=True)
            logger.debug(f'Created directory {target_dir}')

        mode = self.mode
        self.close()
        shutil.move(self.hdf_filename, trg)
        super().__init__(trg, mode=mode)
        new_filepath = trg.absolute()
        return new_filepath

    def saveas(self, filename: Path, overwrite: bool = False, keep_old: bool = True):
        """
        This method copies the current file to the new destination. If keep_old is True, the original
        file s kept.
        Closes the current H5Wrapper and returns a new and opened one wih previous file mode

        Parameters
        ----------
        filename: Path
            New filename.
        overwrite: bool, optional=False
            Whether to not to overwrite an existing filename.
        keep_old: bool, optional=True
            Wheher to keep to original file.

        Returns
        -------
        save_path : Path
            new filename

        """
        _filename = Path(filename)
        if _filename.is_file():
            if overwrite:
                os.remove(_filename)
                src = self.filename
                mode = self.mode
                self.close()  # close this instance
                if keep_old:
                    shutil.copy2(src, _filename)
                else:
                    shutil.move(src, _filename)
                self.hdf_filename = _filename
                return super().__init__(_filename, mode=mode)
            else:
                logger.info("Note: File was not moved to new location as a file already exists with this name"
                            " and overwriting was disabled")
                return None
        src = self.filename
        mode = self.mode
        self.close()  # close this instance

        if keep_old:
            shutil.copy2(src, _filename)
        else:
            shutil.move(src, _filename)

        self.hdf_filename = _filename
        super().__init__(_filename, mode=mode)
        save_path = self.hdf_filename.absolute()
        return save_path

    def open(self, mode="r+"):
        """Opens the closed file"""
        super().__init__(self.hdf_filename, mode=mode)


H5BaseGroup._h5grp = H5BaseGroup
H5BaseGroup._h5ds = H5BaseDataset

H5BaseDataset._h5grp = H5BaseGroup
H5BaseDataset._h5ds = H5BaseDataset
