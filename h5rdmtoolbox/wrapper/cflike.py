"""Implementation of wrapper classes using the CF-like conventions
"""
import h5py
import logging
import pathlib
import warnings
import xarray as xr
from typing import Union, List

from h5rdmtoolbox.conventions.registration import register_hdf_attribute
from . import core
from .. import _repr
from .. import config
from .. import errors
from .._config import ureg
from ..conventions import cflike

logger = logging.getLogger(__package__)


class Group(core.Group):
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
                     *,
                     track_order=None) -> 'Group':
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
        subgrp = super().create_group(name, overwrite, attrs, track_order=track_order)

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
                    data.attrs['units'] = f"{ureg.Unit(data.attrs['units'])}"
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
            if config.require_unit:
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


# H5Group is depreciated
class H5Group(Group):
    """Inherited from Group. Is depreciated. Use Group instead"""

    def __init__(self, _id):
        warnings.warn('H5Group is depreciated. Use Group instead', DeprecationWarning)
        super(H5Group, self).__init__(self, _id)


class CFLikeHDF5StructureStrRepr(_repr.HDF5StructureStrRepr):
    """String representation class for sdump()"""

    def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
        """string representation of a 0D dataset"""
        value = h5dataset.values[()]
        if isinstance(value, float):
            value = f'{float(value)} '
        elif isinstance(value, int):
            value = f'{int(value)} '
        units = self.get_string_repr_of_unit(h5dataset)
        return f"\033[1m{name}\033[0m {value} [{units}], dtype: {h5dataset.dtype}"

    def __NDdataset__(self, name, h5dataset):
        """string representation of a ND dataset"""
        units = self.get_string_repr_of_unit(h5dataset)
        return f"\033[1m{name}\033[0m [{units}]: {h5dataset.shape}, dtype: {h5dataset.dtype}"

    @staticmethod
    def get_string_repr_of_unit(h5dataset: h5py.Dataset) -> str:
        """Get the unit attribute from the dataset and adjust the string
        according to the found/not found data"""
        if 'units' in h5dataset.attrs:
            try:
                _unit = h5dataset.attrs['units']
            except KeyError:
                return 'ERR:NOUNITS'

            if _unit in ('', ' '):
                return '-'
            return _unit
        return 'N.A.'


class CFLikeHDF5StructureHTMLRepr(_repr.HDF5StructureHTMLRepr):

    def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
        _html = super().__0Ddataset__(name, h5dataset)
        _unit = CFLikeHDF5StructureStrRepr.get_string_repr_of_unit(h5dataset)
        _html += f' [{_unit}]'
        return _html

    def __NDdataset__(self, name, h5dataset):
        _html = super().__NDdataset__(name, h5dataset)
        _unit = CFLikeHDF5StructureStrRepr.get_string_repr_of_unit(h5dataset)
        _html += f' [{_unit}]'
        return _html


class File(core.File, Group):
    """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
    It enables additional features and adds new methods streamlining the work with
    HDF5 files and incorporates usage of so-called naming-conventions and layouts.
    All features from h5py packages are preserved."""
    convention = 'cflike'
    hdfrepr = _repr.H5Repr(str_repr=CFLikeHDF5StructureStrRepr(),
                           html_repr=CFLikeHDF5StructureHTMLRepr())

    def __init__(self,
                 name: Union[str, pathlib.Path, None] = None,
                 mode='r',
                 *,
                 title=None,
                 institution=None,
                 source=None,
                 references=None,
                 comment=None,
                 standard_name_table=None,
                 layout: Union[pathlib.Path, str, 'H5Layout'] = 'File_core',
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
                         layout=layout,
                         driver=driver,
                         libver=libver,
                         userblock_size=userblock_size,
                         swmr=swmr,
                         rdcc_nslots=rdcc_nslots,
                         rdcc_nbytes=rdcc_nbytes,
                         rdcc_w0=rdcc_w0,
                         track_order=track_order,
                         fs_strategy=fs_strategy,
                         fs_persist=fs_persist,
                         fs_threshold=fs_threshold,
                         **kwds)
        """Initialize a File object following the cf-like convention.
        
        Parameters
        ----------
        name : str, pathlib.Path, None
            The name of the file to open. If None, a temporary file is created.
        mode : str
            The mode in which to open the file. Must be one of 'r', 'r+', 'w', or 'a'.
        title : str, optional
            The title of the file. Only used if mode is not 'r'.
        institution : str, optional
            The institution that created the file. Only used if mode is not 'r'.
        source : str, optional
            The source of the data, indicating how the data was produced (model version, ...). 
            Only used if mode is not 'r'.
        references : str, optional
            Publications or web documentations that describe the file. Only used if mode is not 'r'.
        comment : str, optional
            Additional comments. Only used if mode is not 'r'.
        standard_name_table : str, StandardNameTable, optional
            The standard name table to use. If a string is given, the table is loaded from the
            registered tables. If None, the default table is used.
        layout : str, pathlib.Path, H5Layout, optional
            The layout to use. If a string is given, the layout is loaded from the registered layouts.
            If None, the default layout is used.
        driver : str, optional
            The low-level file driver to use. See h5py.File for more information.
        libver : str, optional
            The version of the HDF5 library to use. See h5py.File for more information.
        userblock_size : int, optional
            The size of the user block in bytes. See h5py.File for more information.
        swmr : bool, optional
            Whether to open the file in SWMR read mode. See h5py.File for more information.
        rdcc_nslots : int, optional
            The number of chunk slots in the raw data chunk cache. See h5py.File for more information.
        rdcc_nbytes : int, optional
            The total size of the raw data chunk cache in bytes. See h5py.File for more information.
        rdcc_w0 : float, optional
            The preemption policy for chunks. See h5py.File for more information.
        track_order : bool, optional
            Whether to track the order in which chunks are accessed. See h5py.File for more information.
        fs_strategy : str, optional
            The file space strategy to use. See h5py.File for more information.
        fs_persist : bool, optional
            Whether to persistently allocate file space. See h5py.File for more information.
        fs_threshold : int, optional
            The minimum size of a file space allocation. See h5py.File for more information.
        **kwds
            Additional keyword arguments are passed to h5py.File.
        """

        def _write_non_readonly_attr(name, value):
            if self.mode != 'r':
                self.attrs[name] = value
            else:
                raise RuntimeError(f'No write intent. Cannot write {name}.')

        for attr in ['institution', 'source', 'references', 'comment']:
            if locals()[attr] is not None:
                _write_non_readonly_attr(attr, locals()[attr])

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


# H5File is depreciated
class H5File(File):
    """Inherited from File. It is depreciated and will be removed in future versions."""

    def __init__(self, _id):
        warnings.warn('H5File is depreciated. Use File instead', DeprecationWarning)
        super(H5File, self).__init__(self, _id)


class Dataset(core.Dataset):
    """Dataset class following the CF-like conventions"""
    convention = 'cflike'


# H5Dataset is depreciated
class H5Dataset(Dataset):
    """Inherited from Dataset. It is depreciated and will be removed in future versions."""

    def __init__(self, _id):
        warnings.warn('H5Dataset is depreciated. Use Dataset instead', DeprecationWarning)
        super(H5Dataset, self).__init__(self, _id)


Dataset._h5grp = Group
Dataset._h5ds = Dataset

Group._h5grp = Group
Group._h5ds = Dataset

# standard name
register_hdf_attribute(cflike.standard_name.StandardNameDatasetAttribute,
                       Dataset,
                       name='standard_name',
                       overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameGroupAttribute, Group, name='standard_name', overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameTableAttribute, Dataset, name='standard_name_table',
                       overwrite=True)
register_hdf_attribute(cflike.standard_name.StandardNameTableAttribute, Group, name='standard_name_table',
                       overwrite=True)

# units:
register_hdf_attribute(cflike.units.UnitsAttribute, Dataset, name='units', overwrite=True)

# long name:
register_hdf_attribute(cflike.long_name.LongNameAttribute, Group, name='long_name', overwrite=True)
register_hdf_attribute(cflike.long_name.LongNameAttribute, Dataset, name='long_name', overwrite=True)

# title:
register_hdf_attribute(cflike.title.TitleAttribute, File, name='title', overwrite=True)

# references:
register_hdf_attribute(cflike.references.ReferencesAttribute, File, name='references', overwrite=True)
