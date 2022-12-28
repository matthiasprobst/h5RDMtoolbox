"""Implementation of wrapper classes using the CF-like conventions
"""
import h5py
import logging
import pathlib
import warnings
import xarray as xr
from pint_xarray import unit_registry as ureg
from typing import Union, List

from time import perf_counter_ns
from h5rdmtoolbox.conventions.registration import register_hdf_attribute
from . import core
from .. import errors
from .._repr import HDF5Printer
from ..config import CONFIG
from ..conventions import cflike
import os

ureg.default_format = CONFIG.UREG_FORMAT

logger = logging.getLogger(__package__)


class H5Group(core.H5Group):
    """
    It enforces the usage of units
    and standard_names for every dataset and informative metadata at
    root level (creation time etc.).

     It provides and long_name for every group.
    Furthermore, methods that facilitate the work with HDF files are provided,
    such as
    * create_dataset_from_image
    * create_dataset_from_csv
    * stack()
    * concatenate()
    * ...

    Automatic generation of root attributes:
    - __h5rdmtoolbox_version__: version of this package

    providing additional features through
    specific properties such as units and long_name or through special or
    adapted methods like create_dataset, create_external_link.
    """

    convention = 'cflike'

    def create_group(self,
                     name,
                     long_name=None,
                     overwrite=None,
                     attrs=None,
                     track_order=None) -> 'H5Group':
        """
        Overwrites parent methods. Additional parameters are "long_name" and "attrs".
        Besides, it does and behaves the same. Differently to dataset creating
        long_name is not mandatory (i.e. will not raise a warning).

        Parameters
        ----------
        name : str
            Name of group
        long_name : str
            The long name of the group. Rules for long_name is checked in method
            check_long_name
        overwrite : bool, default=None
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
        subgrp = super().create_group(name, overwrite, attrs, track_order)

        if attrs is not None:
            long_name = attrs.pop('long_name', long_name)
        if long_name is not None:
            subgrp.attrs['long_name'] = long_name
        return self._h5grp(subgrp)

    def create_dataset(self,
                       name,
                       shape=None,
                       dtype=None,
                       data=None,
                       units=None,
                       long_name=None,
                       standard_name: Union[str, "StandardName"] = None,
                       overwrite=None,
                       chunks=True,
                       attrs=None,
                       attach_scales=None,
                       make_scale=False,
                       **kwargs):
        """
        Adapting parent dataset creation:
        Additional parameters are
            - long_name or standard_name (either is required. possible to pass both though)
            - units

        Parameters
        ----------
        name : str
            Name of dataset
        shape : tuple, optional
            Dataset shape. see h5py doc. Default None. Required if data=None.
        dtype : str, optional
            dtype of dataset. see h5py doc. Default is dtype('f')
        data : numpy ndarray, default=None
            Provide data to initialize the dataset.  If not used,
            provide shape and optionally dtype via kwargs (see more in
            h5py documentation regarding arguments for create_dataset
        long_name : str
            The long name (human-readable description of the dataset).
            If None, standard_name must be provided
        standard_name: str or conventions.StandardName
            The standard name of the dataset. If None, long_name must be provided
        units : str, default=None
            Physical units of the data. Can only be None if data is not attached with such attribute,
            e.g. through xarray.
        overwrite : bool, default=None
            If the dataset does not already exist, the new dataset is written and this parameter has no effect.
            If the dataset exists and ...
            ... overwrite is None: h5py behaviour is enabled meaning that if a dataset exists h5py will raise
            ... overwrite is True: dataset is deleted and rewritten according to method parameters
            ... overwrite is False: dataset creation has no effect. Existing dataset is returned.
        chunks : bool or according to h5py.File.create_dataset documentation
            Needs to be True if later resizing is planned
        attrs : dict, optional
            Allows to set attributes directly after dataset creation. Default is
            None, which is an empty dict
        attach_scales : tuple, optional
            Tuple defining the datasets to attach scales to. Content of tuples are
            internal hdf paths. If an axis should not be attached to any axis leave it
            empty (''). Default is ('',) which attaches no scales
            Note: internal hdf5 path is relative w.r.t. this dataset, so be careful
            where to create the dataset and to which to attach the scales!
            Also note, that if data is a xr.DataArray and attach_scales is not None,
            coordinates of xr.DataArray are ignored and only attach_scales is
            considered.
        make_scale: bool, default=False
            Makes this dataset scale. The parameter attach_scale must be uses, thus be None.
        **kwargs
            see documentation of h5py.File.create_dataset

        Returns
        -------
        ds : h5py.Dataset
            created dataset
        """
        if isinstance(data, str):
            return self.create_string_dataset(name=name,
                                              data=data,
                                              overwrite=overwrite,
                                              standard_name=standard_name,
                                              long_name=long_name,
                                              attrs=attrs, **kwargs)
        if attrs is None:
            attrs = {}
        if isinstance(data, xr.DataArray):
            if attrs is not None:
                data.attrs.update(attrs)
            if units is None:  # maybe DataArray has pint accessor
                try:
                    data = data.pint.dequantify()
                except:
                    pass
                if 'units' in data.attrs:
                    data.attrs['units'] = ureg.Unit(data.attrs['units']).__format__(ureg.default_format)
                    units = data.attrs.get('units')

                if units is None:  # xr.DataArray had no units!
                    units = attrs.get('units', None)  # is it in function parameter attrs?
                    if units is None:  # let's check for a typo:
                        units = kwargs.get('unit', None)
                else:  # xr.DataArray had units ...
                    if 'units' in attrs:  # ...but also there is units in attrs!
                        units = attrs.get('units')
                        warnings.warn(
                            '"units" is over-defined. Your data array is associated with the attribute "units" and '
                            'you passed the parameter "units". Will use the units that has been passed via the '
                            f'function call: {units}')
            else:
                data.attrs['units'] = units

            if long_name is not None and 'long_name' in data.attrs:
                warnings.warn(
                    f'"long_name" is over-defined in dataset "{name}". \nYour data array is already associated '
                    f'with the attribute "long_name" and you passed the parameter "long_name".\n'
                    f'The latter will overwrite the data array attribute long_name!'
                )

            if 'standard_name' in data.attrs:
                attrs['standard_name'] = data.attrs['standard_name']
            if 'long_name' in data.attrs:
                attrs['long_name'] = data.attrs['long_name']

        if units is None:
            if attrs:
                units = attrs.get('units', None)
            else:
                units = kwargs.get('unit', None)  # forgive the typo!
        else:
            if 'units' in attrs:
                warnings.warn(f'Parameter "units" of dataset "{name}" is over-defined. Your data array is '
                              'associated with the attribute "units" and '
                              'you passed the parameter "units". The latter will overwrite the data array units!')
        if units is None:
            if CONFIG.REQUIRE_UNITS:
                raise errors.UnitsError(f'Units of dataset "{name}" cannot be None.'
                                        ' A dimensionless dataset has units "''"')
            attrs['units'] = ''
        else:
            attrs['units'] = units

        if 'long_name' in attrs and long_name is not None:
            warnings.warn('"long_name" is over-defined.\nYour data array is already associated with the attribute '
                          '"long_name" and you passed the parameter "long_name".\nThe latter will overwrite '
                          'the data array units!')
        if long_name is not None:
            attrs['long_name'] = long_name

        if 'standard_name' in attrs and standard_name is not None:
            warnings.warn(f'"standard_name" is over-defined for dataset "{name}". '
                          f'Your data array is associated with the attribute '
                          '"standard_name" and you passed the parameter "standard_name". The latter will overwrite '
                          'the data array units!')
        if standard_name is not None:
            self.standard_name_table.check_units(standard_name, attrs['units'])
            attrs['standard_name'] = standard_name

        if attrs.get('standard_name') is None and attrs.get('long_name') is None:
            raise RuntimeError(f'No long_name or standard_name is given for dataset "{name}". Either must be provided')

        ds = super().create_dataset(name, shape, dtype, data, overwrite,
                                    chunks, attrs, attach_scales, make_scale, **kwargs)
        return self._h5ds(ds.id)

    def create_string_dataset(self,
                              name: str,
                              data: Union[str, List[str]],
                              overwrite=False,
                              standard_name=None,
                              long_name=None,
                              attrs=None):
        """Create a string dataset. In this version only one string is allowed.
        In future version a list of strings may be allowed, too.
        No long or standard name needed"""
        if attrs is None:
            attrs = {}
        if long_name:
            attrs.update({'long_name': long_name})
        if standard_name:
            attrs.update({'standard_name': long_name})
        return super().create_string_dataset(name, data, overwrite, attrs)

    def get_dataset_by_standard_name(self, standard_name: str, n: int = None, rec: bool = True) -> h5py.Dataset or None:
        """Return the dataset with a specific standard_name within the current group.
        Raises error if multiple datasets are found!
        To recursive scan through all datasets, use
        get_by_attribute('standard_name', <your_value>, 'ds').
        Returns None if no matching dataset has been found.
        """
        if n == 1:
            return self.find_one({'standard_name': standard_name}, objfilter=h5py.Dataset, rec=rec)
        return self.find({'standard_name': standard_name}, objfilter=h5py.Dataset, rec=rec)


class CFLikeHDF5Printer(HDF5Printer):
    """Takes care of printing the HDF5 Strucure"""

    def __dataset_str__(self, key, item):
        try:
            units = item.attrs['units']
        except KeyError:
            units = 'ERR:NOUNITS'
        return f"\033[1m{key}\033[0m [{units}]: {item.shape}, dtype: {item.dtype}"

    def __dataset_html__(self, ds_name, h5dataset, max_attr_length: Union[int, None],
                         _ignore_attrs=('units', 'DIMENSION_LIST', 'REFERENCE_LIST', 'NAME', 'CLASS', 'COORDINATES')):
        _value0d = ''
        if h5dataset.dtype.char == 'S':
            pass
        else:
            if h5dataset.ndim == 0:
                _value0d = h5dataset.values[()]
                if isinstance(_value0d, float):
                    _value0d = f'{float(_value0d)} '
                elif isinstance(_value0d, int):
                    _value0d = f'{int(_value0d)} '
            else:
                _value0d = ''
            if 'units' in h5dataset.attrs:
                _unit = h5dataset.attrs['units']
                if _unit in ('', ' '):
                    _unit = '-'
            else:
                _unit = 'N.A.'

        ds_dirname = os.path.dirname(h5dataset.name)
        if h5dataset.ndim == 0:
            _shape_repr = ''
        else:
            _shape = h5dataset.shape
            if CONFIG.ADVANCED_SHAPE_REPR:
                _shape_repr = '('
                ndim = h5dataset.ndim
                for i in range(ndim):
                    try:
                        orig_dim_name = h5dataset.dims[i][0].name
                        if os.path.dirname(orig_dim_name) == ds_dirname:
                            dim_name = os.path.basename(orig_dim_name)
                        else:
                            dim_name = orig_dim_name
                        if i == 0:
                            _shape_repr += f'{dim_name}: {_shape[i]}'
                        else:
                            _shape_repr += f', {dim_name}: {_shape[i]}'
                    except RuntimeError:
                        pass
                _shape_repr += ')'
                if _shape_repr == '()' and ndim > 0:
                    _shape_repr = _shape
            else:
                _shape_repr = _shape
                # print(h5dataset.name, _shape_dim_names)

        _id1 = f'ds-1-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5dataset.name}-{perf_counter_ns().__str__()}'
        if h5dataset.dtype.char == 'S':
            if h5dataset.ndim == 0:
                _html_pre = f"""\n
                            <ul id="{_id1}" class="h5tb-var-list">
                            <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                            <label class='h5tb-varname' 
                                for="{_id2}">{ds_name}</label>
                            <span class="h5tb-dims">{_shape_repr}</span>: {_value0d}"""
            else:
                _html_pre = f"""\n
                            <ul id="{_id1}" class="h5tb-var-list">
                            <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                            <label class='h5tb-varname' 
                                for="{_id2}">{ds_name}</label>
                            <span class="h5tb-dims">{_shape_repr}</span>"""
        else:
            _html_pre = f"""\n
                        <ul id="{_id1}" class="h5tb-var-list">
                        <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                        <label class='h5tb-varname' 
                            for="{_id2}">{ds_name}</label>
                        <span class="h5tb-dims">{_shape_repr}</span>  [
                        <span class="h5tb-unit">{_value0d}{_unit}</span>]"""
        # now all attributes of the dataset:
        # open attribute section:
        _html_ds_attrs = """\n<ul class="h5tb-attr-list">"""
        # write attributes:
        for k, v in h5dataset.attrs.items():
            if k not in _ignore_attrs:
                _html_ds_attrs += self.__attr_html__(k, v, max_attr_length)
        # close attribute section
        _html_ds_attrs += """\n
                    </ul>"""

        # close dataset section
        _html_post = """\n
                 </ul>
                 """
        _html_ds = _html_pre + _html_ds_attrs + _html_post
        return _html_ds


class H5File(core.H5File, H5Group):
    """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
    It enables additional features and adds new methods streamlining the work with
    HDF5 files and incorporates usage of so-called naming-conventions and layouts.
    All features from h5py packages are preserved."""
    convention = 'cflike'
    HDF5printer = CFLikeHDF5Printer(ignore_attrs=['units', ])

    def __init__(self,
                 name: pathlib.Path = None,
                 mode='r',
                 title=None,
                 standard_name_table=None,
                 layout: Union[pathlib.Path, str, 'H5Layout'] = 'H5File',
                 driver=None,
                 libver=None,
                 userblock_size=None,
                 swmr=False,
                 rdcc_nslots=None,
                 rdcc_nbytes=None,
                 rdcc_w0=None,
                 track_order=None,
                 fs_strategy=None,
                 fs_persist=False,
                 fs_threshold=1,
                 **kwds):
        super().__init__(name,
                         mode,
                         layout,
                         driver,
                         libver,
                         userblock_size,
                         swmr,
                         rdcc_nslots,
                         rdcc_nbytes,
                         rdcc_w0,
                         track_order,
                         fs_strategy,
                         fs_persist,
                         fs_threshold,
                         **kwds)

        if self.mode != 'r':
            # set title and layout
            if title is not None:
                self.attrs['title'] = title
        else:
            if title is not None:
                raise RuntimeError('No write intent. Cannot write title.')

        if standard_name_table is not None:
            if isinstance(standard_name_table, str):
                standard_name_table = cflike.standard_name.StandardNameTable.load_registered(standard_name_table)
            if self.standard_name_table != standard_name_table:
                self.standard_name_table = standard_name_table
        self.layout = layout


class H5Dataset(core.H5Dataset):
    """Dataset class following the CF-like conventions"""
    convention = 'cflike'


H5Dataset._h5grp = H5Group
H5Dataset._h5ds = H5Dataset

H5Group._h5grp = H5Group
H5Group._h5ds = H5Dataset

# standard name
register_hdf_attribute(cflike.standard_name.StandardNameDatasetAttribute,
                       H5Dataset,
                       name='standard_name',
                       overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameGroupAttribute, H5Group, name='standard_name', overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameTableAttribute, H5Dataset, name='standard_name_table',
                       overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameTableAttribute, H5Group, name='standard_name_table',
                       overwrite=True)

# units:
register_hdf_attribute(cflike.units.UnitsAttribute, H5Dataset, name='units', overwrite=True)

# long name:
register_hdf_attribute(cflike.long_name.LongNameAttribute, H5Group, name='long_name', overwrite=True)
register_hdf_attribute(cflike.long_name.LongNameAttribute, H5Dataset, name='long_name', overwrite=True)

# title:
register_hdf_attribute(cflike.title.TitleAttribute, H5File, name='title', overwrite=True)
