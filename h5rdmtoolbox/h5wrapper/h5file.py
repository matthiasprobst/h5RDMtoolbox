import json
import logging
import warnings
from pathlib import Path
from typing import Union

import h5py
import pint
import pint_xarray
import xarray as xr
from h5py import h5i
from h5py._hl.base import phil, with_phil
from pint_xarray import unit_registry as ureg

from .h5base import H5BaseDataset, H5BaseGroup, H5Base, H5BaseLayout, WrapperAttributeManager
from .. import conventions
from .. import user_data_dir
from .. import utils
from ..x2hdf import xr2hdf

logger = logging.getLogger(__package__)

# the following two lines are needed, otherwise automating formatting of the code will remove pint and xarray2hdf accessors
assert pint_xarray.__version__ == '0.2.1'
assert xr2hdf.__version__ == '0.1.0'

ureg.default_format = 'C~'

_SNC_LS = {}


class ConventionSensitiveAttributeManager(WrapperAttributeManager):
    """Attribute manager class which checks validity if attribute name
    is standard_name."""

    @with_phil
    def __setitem__(self, name, value):
        """ Set a new attribute, overwriting any existing attribute.

        The type and shape of the attribute are determined from the data.  To
        use a specific type or shape, or to preserve the type of attribute,
        use the methods create() and modify().
        """

        if name == conventions.NAME_IDENTIFIER_ATTR_NAME:
            if h5i.get_type(self._id) in (h5i.GROUP, h5i.FILE):
                raise AttributeError(f'Attribute name {name} is reserverd '
                                     'for dataset only.')
            if h5i.get_type(self._id) == h5i.DATASET:
                # check for standardized data-name identifiers
                self.identifier_convention.check_name(value, strict=conventions.identifier.STRICT)

        super().__setitem__(name, value)

        if isinstance(value, dict):
            _value = json.dumps(value)
        elif isinstance(value, Path):
            _value = str(value)
        elif isinstance(value, (h5py.Dataset, h5py.Group)):
            return self.create(name, data=value.name)
        else:
            _value = value
        self.create(name, data=_value)


class H5Dataset(H5BaseDataset):
    """
    Subclass of h5py.Dataset implementing a model.
    This core version enforces the user to use units and
    long_name or standard_name when creating datasets.
    The property standard_name return a standard name
    model.
    """

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return ConventionSensitiveAttributeManager(self, self.standard_name_table)

    @property
    def units(self):
        """Returns the attribute units. Returns None if it does not exist."""
        return self.attrs.get('units')

    @property
    def standard_name_table(self):
        """returns the standard name convention associated with the file instance"""
        return _SNC_LS[self.file.id.id]

    @standard_name_table.setter
    def standard_name_table(self, convention: conventions.StandardizedNameTable):
        """returns the standard name convention associated with the file instance"""
        _SNC_LS[self.id.id] = convention

    @units.setter
    def units(self, units):
        """Sets the attribute units to attribute 'units'
        default unit registry format of pint is used."""
        if units:
            if isinstance(units, str):
                _units = ureg.Unit(units).__format__(ureg.default_format)
            elif isinstance(units, pint.Unit):
                _units = units.__format__(ureg.default_format)
            else:
                raise TypeError(f'Unit must be a string or pint.Unit but not {type(units)}')
        else:
            _units = units
        standard_name = self.attrs.get('standard_name')
        if standard_name:
            self.standard_name_table.check_units(standard_name, _units)

        self.attrs.modify('units', _units)

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

    @property
    def standard_name(self):
        """Returns the attribute standard_name. Returns None if it does not exist."""
        attrs_string = self.attrs.get('standard_name')
        if attrs_string is None:
            return None
        return self.standard_name_table.get(attrs_string)

    @standard_name.setter
    def standard_name(self, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            if self.standard_name_table.is_valid(new_standard_name):
                self.attrs['standard_name'] = new_standard_name

    def __str__(self):
        out = f'{self.__class__.__name__} "{self.name}"'
        out += f'\n{"-" * len(out)}'
        out += f'\n{"shape:":14} {self.shape}'
        out += f'\n{"long_name:":14} {self.long_name}'
        out += f'\n{"standard_name:":14} {self.attrs.get("standard_name")}'
        out += f'\n{"units:":14} {self.units}'

        has_dim = False
        dim_str = f'\n\nDimensions'
        for _id, d in enumerate(self.dims):
            naxis = len(d)
            if naxis > 0:
                has_dim = True
                for iaxis in range(naxis):
                    if naxis > 1:
                        dim_str += f'\n   [{_id}({iaxis})] {utils._make_bold(d[iaxis].name)} {d[iaxis].shape}'
                    else:
                        dim_str += f'\n   [{_id}] {utils._make_bold(d[iaxis].name)} {d[iaxis].shape}'
                    dim_str += f'\n       long_name:     {d[iaxis].attrs.get("long_name")}'
                    dim_str += f'\n       standard_name: {d[iaxis].attrs.get("standard_name")}'
                    dim_str += f'\n       units:         {d[iaxis].attrs.get("units")}'
        if has_dim:
            out += dim_str
        return out

    def __init__(self, _id):
        if isinstance(_id, h5py.Dataset):
            _id = _id.id
        if isinstance(_id, h5py.h5d.DatasetID):
            super().__init__(_id)
        else:
            ValueError('Could not initialize Dataset. A h5py.h5f.FileID object must be passed')

        super().__init__(_id)

    def to_units(self, units):
        """Changes the physical unit of the dataset using pint_xarray.
        Loads to full dataset into RAM!"""
        self[()] = self[()].pint.quantify().pint.to(units).pint.dequantify()


class H5Group(H5BaseGroup):
    """
    It enforces the usage of units
    and standard_names for every dataset and informative meta data at
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
    (a) creation_time: Date time when file was created. Default format see meta_standard.time.datetime_str
    (b) modification_time: Date time when file was used in mode ('r+' or 'a')
    (c) h5wrapper_version: version of this package

    providing additional features through
    specific properties such as units and long_name or through special or
    adapted methods like create_dataset, create_external_link.
    """

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return ConventionSensitiveAttributeManager(self, self.standard_name_table)

    @property
    def data_source_type(self) -> conventions.data.DataSourceType:
        """returns data source type as DataSourceType"""
        ds_value = self.attrs.get(conventions.data.DataSourceType.get_attr_name())
        if ds_value is None:
            return conventions.data.DataSourceType.none
        try:
            return conventions.data.DataSourceType[ds_value.lower()]
        except KeyError:
            warnings.warn(f'Data source type is unknown to meta convention: "{ds_value}"')
            return conventions.data.DataSourceType.unknown

    @property
    def standard_name_table(self) -> conventions.StandardizedNameTable:
        """returns the standar name convention associated with the file instance"""
        if self.file.id.id in _SNC_LS:
            return _SNC_LS[self.file.id.id]
        return None

    @standard_name_table.setter
    def standard_name_table(self, convention: conventions.StandardizedNameTable):
        """returns the standard name convention associated with the file instance"""
        _SNC_LS[self.id.id] = convention

    def create_group(self, name, long_name=None, overwrite=None,
                     attrs=None, track_order=None):
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
        grp = super().create_group(name, overwrite, attrs, track_order)
        if attrs is not None:
            long_name = attrs.pop('long_name', long_name)
        if long_name is not None:
            grp.attrs['long_name'] = long_name
        return self._h5grp(grp)

    def create_dataset(self, name, shape=None, dtype=None, data=None,
                       units=None, long_name=None,
                       standard_name: Union[str, conventions.StandardizedName] = None,
                       overwrite=None, chunks=True,
                       attrs=None, attach_scales=None, make_scale=False,
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
        data : numpy ndarray, optional=None
            Provide data to initialize the dataset.  If not used,
            provide shape and optionally dtype via kwargs (see more in
            h5py documentation regarding arguments for create_dataset
        long_name : str
            The long name (human readable description of the dataset).
            If None, standard_name must be provided
        standard_name: str or StandardName
            The standard name of the dataset. If None, long_name must be provided
        units : str, optional=None
            Physical units of the data. Can only be None if data is not attached with such attribute,
            e.g. through xarray.
        overwrite : bool, optional=None
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
        make_scale: bool, optional=False
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
        else:
            if isinstance(data, xr.DataArray):
                data.attrs.update(attrs)

        if isinstance(data, xr.DataArray):
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

        return super().create_dataset(name, shape, dtype, data, overwrite, chunks,
                                      attrs, attach_scales, make_scale, **kwargs)

    def get_dataset_by_standard_name(self, standard_name: str, n: int = None) -> h5py.Dataset or None:
        """Returns the dataset with a specific standard_name within the current group.
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


class H5FileLayout(H5BaseLayout):

    def write(self):
        super().write()
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
        h5inspect = conventions.layout.H5Inspect(h5root, inspect_group=self.__check_group__,
                                                 inspect_dataset=self.__check_dataset__, silent=silent)
        h5root.visititems(h5inspect)
        return h5inspect.nissues


class H5File(H5Base, H5Group):
    """H5File requires title as root attribute. It is not enforced but if not set
    an issue be shown due to it.
    """

    Layout: H5FileLayout = H5FileLayout(Path.joinpath(user_data_dir, f'layout/H5File.hdf'))

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return ConventionSensitiveAttributeManager(self, self.standard_name_table)

    @property
    def title(self) -> Union[str, None]:
        """Returns the title (stored as HDF5 attribute) of the file. If it does not exist, None is returned"""
        return self.attrs.get('title')

    @title.setter
    def title(self, title):
        """Sets the title of the file"""
        self.attrs.modify('title', title)

    def __init__(self, name: Path = None, mode='r', title=None, standard_name_table=None,
                 driver=None, libver=None, userblock_size=None,
                 swmr=False, rdcc_nslots=None, rdcc_nbytes=None, rdcc_w0=None,
                 track_order=None, fs_strategy=None, fs_persist=False, fs_threshold=1,
                 **kwds):
        _depr_long_name = kwds.pop('long_name', None)
        if _depr_long_name is not None:
            warnings.warn('Using long name when initializing a H5File is deprecated. Use title instead!',
                          DeprecationWarning)
            title = _depr_long_name

        super().__init__(name, mode, driver, libver,
                         userblock_size, swmr, rdcc_nslots,
                         rdcc_nbytes, rdcc_w0, track_order,
                         fs_strategy, fs_persist, fs_threshold)

        if title is not None:
            self.attrs['title'] = title

        if isinstance(standard_name_table, str):
            snc = conventions.StandardizedNameTable.from_xml(standard_name_table)
        elif isinstance(standard_name_table, conventions.StandardizedNameTable):
            snc = standard_name_table
        elif standard_name_table is None:
            snc = conventions.empty_standardized_name_table
        else:
            raise TypeError(f'Unexpected type for standard_name_table: {type(standard_name_table)}')
        self.standard_name_table = snc


H5Dataset._h5grp = H5Group
H5Dataset._h5ds = H5Dataset

H5Group._h5grp = H5Group
H5Group._h5ds = H5Dataset
