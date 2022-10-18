"""Implementation of wrapper classes using the CF-like conventions
"""
import json
import logging
import pathlib
import warnings
from typing import Union, List

import h5py
import pint
import xarray as xr
from pint_xarray import unit_registry as ureg

from h5rdmtoolbox.conventions.registration import register_attribute_class
from .. import config
from .. import errors
from .. import utils
from .. import wrapper
from .._logger import logger
from ..conventions import cflike
from ..conventions.cflike.long_name import LongName
from ..conventions.registration import register_standard_attribute

ureg.default_format = config.UREG_FORMAT

logger = logging.getLogger(__package__)


class H5Group(wrapper.core.H5Group):
    """
    It enforces the usage of units
    and standard_names for every dataset and informative metadata at
    root level (creation time etc).

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
    - __wrcls__ wrapper class indication

    providing additional features through
    specific properties such as units and long_name or through special or
    adapted methods like create_dataset, create_external_link.
    """

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
            The long name (human readable description of the dataset).
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
                warnings.warn('"units" is over-defined. Your data array is associated with the attribute "units" and '
                              'you passed the parameter "units". The latter will overwrite the data array units!')
        if units is None:
            if config.REQUIRE_UNITS:
                raise errors.UnitsError('Units cannot be None. A dimensionless dataset has units "''"')
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
            raise RuntimeError('No long_name or standard_name is given. Either must be provided')

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

    def get_dataset_by_standard_name(self, standard_name: str, n: int = None) -> h5py.Dataset or None:
        """Return the dataset with a specific standard_name within the current group.
        Raises error if multiple datasets are found!
        To recursive scan through all datasets, use
        get_by_attribute('standard_name', <your_value>, 'ds').
        Returns None if no matching dataset has been found."""
        candidats = self.get_datasets_by_attribute('standard_name', standard_name, False)
        if n is None:
            if len(candidats) == 0:
                return None
            if len(candidats) > 1:
                raise ValueError(f'Multiple datasets found with standard name "{standard_name}": {candidats}')
            return candidats[0]
        else:
            if len(candidats) == n:
                if len(candidats) == 1:
                    return candidats[0]
                return candidats
            else:
                raise NameError(f'Could not find standard_name "{standard_name}"')

    def create_datasets_from_csv(self, csv_filename, shape=None, overwrite=False,
                                 combine_opt='stack', axis=0, chunks=None, **kwargs):
        """
        Reads data from a csv and adds a dataset according to column names.
        Pandas.read_csv() is used. So all arguments for this function may be passed.

        Parameters
        ----------
        csv_filename : pathlib.Path or list of pathlib.Path
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
        elif isinstance(csv_filename, (str, pathlib.Path)):
            is_single_file = True
            csv_fname = csv_filename
        else:
            raise ValueError(
                f'Wrong input for "csv_filename: {type(csv_filename)}')

        df = pd_read_csv(csv_fname, **kwargs)
        # ncols = len(df.columns)

        compression, compression_opts = config.HDF_COMPRESSION, config.HDF_COMPRESSION_OPTS

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


class H5File(wrapper.core.H5File, H5Group):
    """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
    It enables additional features and adds new methods streamlining the work with
    HDF5 files and incorporates usage of so-called naming-conventions and layouts.
    All features from h5py packages are preserved."""

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


class H5Dataset(wrapper.core.H5Dataset):
    pass


H5Dataset._h5grp = H5Group
H5Dataset._h5ds = H5Dataset

H5Group._h5grp = H5Group
H5Group._h5ds = H5Dataset


@register_standard_attribute(H5Dataset, name='standard_name_table')
@register_standard_attribute(H5Group, name='standard_name_table')
class StandardNameTableAttribute:
    """Standard Name Table attribute"""

    def set(self, snt: Union[str, cflike.standard_name.StandardNameTable]):
        """Set (write to root group) Standard Name Table

        Raises
        ------
        errors.StandardNameTableError
            If no write intent on file.

        """
        if isinstance(snt, str):
            cflike.standard_name.StandardNameTable.print_registered()
            snt = cflike.standard_name.StandardNameTable.load_registered(snt)
        if self.mode == 'r':
            raise errors.StandardNameTableError('Cannot write Standard Name Table (no write intent on file)')
        if snt.STORE_AS == cflike.standard_name.StandardNameTableStoreOption.none:
            if snt.url:
                if cflike.standard_name.url_exists(snt.url):
                    self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, snt.url)
                else:
                    warnings.warn(f'URL {snt.url} not reached. Storing SNT as dictionary instead')
                    self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME,
                                                 snt.to_dict())
            else:
                self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, json.dumps(snt.to_dict()))
        if snt.STORE_AS == cflike.standard_name.StandardNameTableStoreOption.versionname:
            self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, snt.versionname)
        elif snt.STORE_AS == cflike.standard_name.StandardNameTableStoreOption.dict:
            self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, json.dumps(snt.to_dict()))
        elif snt.STORE_AS == cflike.standard_name.StandardNameTableStoreOption.url:
            if snt.url is not None:
                if cflike.standard_name.url_exists(snt.url):
                    self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, snt.url)
                else:
                    warnings.warn(f'URL {snt.url} not reached. Storing SNT as dictionary instead')
                    self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, snt.to_dict())
            else:  # else fall back to writing dict. better than versionname because cannot get lost
                self.rootparent.attrs.modify(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, json.dumps(snt.to_dict()))
        cflike.standard_name._SNT_CACHE[self.id.id] = snt

    def get(self) -> cflike.standard_name.StandardNameTable:
        """Get (if exists) Standard Name Table from file

        Raises
        ------
        KeyError
            If cannot load SNT from registration.
        """
        try:
            return cflike.standard_name._SNT_CACHE[self.file.id.id]
        except KeyError:
            pass  # not cached
        snt = self.rootparent.attrs.get(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME, None)
        if snt is not None:
            # snt is a string
            if isinstance(snt, dict):
                return cflike.standard_name.StandardNameTable(**snt)
            if snt[0] == '{':
                return cflike.standard_name.StandardNameTable(**json.loads(snt))
            elif snt[0:4] in ('http', 'wwww.'):
                return cflike.standard_name.StandardNameTable.from_web(snt)
            else:
                return cflike.standard_name.StandardNameTable.from_versionname(snt)
        return cflike.standard_name.Empty_Standard_Name_Table

    def delete(self):
        """Delete standard name table from root attributes"""
        self.attrs.__delitem__(config.STANDARD_NAME_TABLE_ATTRIBUTE_NAME)


@register_standard_attribute(H5Group, name='standard_name')
class StandardNameGroupAttribute:
    def set(self, new_standard_name):
        raise RuntimeError('A standard name attribute is used for datasets only')


@register_standard_attribute(H5Dataset, name='standard_name')
class StandardNameDatasetAttribute:
    """Standard Name attribute"""

    def set(self, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            if self.standard_name_table.check_name(new_standard_name):
                if cflike.standard_name.STRICT:
                    if 'units' in self.attrs:
                        self.standard_name_table.check_units(new_standard_name,
                                                             self.attrs['units'])
                self.attrs.create('standard_name', new_standard_name)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        val = self.attrs.get('standard_name', None)
        if val is None:
            return None
        return self.standard_name_table[val]

    def delete(self):
        """Delete attribute"""
        self.attrs.__delitem__('standard_name')


@register_standard_attribute(H5Dataset, name='units')
class UnitsAttribute:
    """Units attribute"""

    def set(self, new_units: Union[str, pint.Unit]):
        """Sets the attribute units to attribute 'units'
        default unit registry format of pint is used."""
        if new_units:
            if isinstance(new_units, str):
                _new_units = ureg.Unit(new_units).__format__(ureg.default_format)
            elif isinstance(new_units, pint.Unit):
                _new_units = new_units.__format__(ureg.default_format)
            else:
                raise TypeError(f'Unit must be a string or pint.Unit but not {type(new_units)}')
        else:
            _new_units = new_units
        standard_name = self.attrs.get('standard_name')
        if standard_name:
            self.standard_name_table.check_units(standard_name, _new_units)

        self.attrs.create('units', _new_units)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        return self.attrs.get('units', None)

    def delete(self):
        """Delete attribute units"""
        self.attrs.__delitem__('units')


# @register_standard_attribute(H5Group, name='long_name')
# @register_standard_attribute(H5Dataset, name='long_name')
class LongNameAttribute:
    """Long name attribute"""

    def set(self, value):
        """Set the long_name"""
        ln = LongName(value)  # runs check automatically during initialization
        self.attrs.create('long_name', ln.__str__())

    def get(self) -> Union[str, None]:
        """Get the long_name"""
        return self.attrs.get('long_name', None)

    def delete(self):
        """Delete the long_name"""
        self.attrs.__delitem__('long_name')


register_attribute_class(LongNameAttribute, H5Group, name='long_name', overwrite=True)
register_attribute_class(LongNameAttribute, H5Dataset, name='long_name', overwrite=True)
register_attribute_class(cflike.title.TitleAttribute, H5File, name='title', overwrite=True)
