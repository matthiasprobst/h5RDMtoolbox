# """Toolbox wrapper classes for HDF5 files. Various standard attributes are
# automatically registered to the root group, groups and datasets.
# """
# import h5py
# import logging
# import pathlib
# import warnings
# import xarray as xr
# from typing import Union, List
#
# from . import core
# from .. import _repr
# from .. import config
# from .. import conventions
# from ..conventions.units import UnitsError
#
# logger = logging.getLogger(__package__)
#
#
# class Group(core.Group):
#     """
#     It enforces the usage of units
#     and standard_names for every dataset and informative metadata at
#     root level (creation time etc.).
#
#      It provides and long_name for every group.
#     Furthermore, methods that facilitate the work with HDF files are provided,
#     such as
#     * create_dataset_from_image
#     * create_dataset_from_csv
#     * stack()
#     * concatenate()
#     * ...
#
#     Automatic generation of root attributes:
#     - __h5rdmtoolbox_version__: version of this package
#
#     providing additional features through
#     specific properties such as units and long_name or through special or
#     adapted methods like create_dataset, create_external_link.
#     """
#
#     convention = 'tbx'
#
#     # def create_group(self,
#     #                  name,
#     #                  long_name=None,
#     #                  overwrite=None,
#     #                  attrs=None,
#     #                  *,
#     #                  track_order=None,
#     #                  **kwargs) -> 'Group':
#     #     """
#     #     Overwrites parent methods. Additional parameters are "long_name" and "attrs".
#     #     Besides, it does and behaves the same. Differently to dataset creating
#     #     long_name is not mandatory (i.e. will not raise a warning).
#     #
#     #     Parameters
#     #     ----------
#     #     name : str
#     #         Name of group
#     #     long_name : str
#     #         The long name of the group. Rules for long_name is checked in method
#     #         check_long_name
#     #     overwrite : bool, default=None
#     #         If the group does not already exist, the new group is written and this parameter has no effect.
#     #         If the group exists and ...
#     #         ... overwrite is None: h5py behaviour is enabled meaning that if a group exists h5py will raise
#     #         ... overwrite is True: group is deleted and rewritten according to method parameters
#     #         ... overwrite is False: group creation has no effect. Existing group is returned.
#     #     attrs : dict, optional
#     #         Attributes of the group, default is None which is an empty dict
#     #     track_order : bool or None
#     #         Track creation order under this group. Default is None.
#     #     """
#     #     kwargs, std_attrs = core._pop_standard_attributes(self, kwargs)
#     #     subgrp = super().create_group(name, overwrite, attrs, track_order=track_order, **kwargs)
#     #     core._write_standard_attributes(subgrp, std_attrs)
#     #
#     #     if attrs is not None:
#     #         long_name = attrs.pop('long_name', long_name)
#     #     if long_name is not None:
#     #         subgrp.attrs['long_name'] = long_name
#     #     return self._h5grp(subgrp)
#     #
#     # def create_dataset(self,
#     #                    name,
#     #                    shape=None,
#     #                    dtype=None,
#     #                    data=None,
#     #                    # units=None,
#     #                    # long_name=None,
#     #                    # standard_name: Union[str, conventions.StandardName] = None,
#     #                    # responsible_person: str = None,
#     #                    overwrite=None,
#     #                    chunks=True,
#     #                    attrs=None,
#     #                    attach_scales=None,
#     #                    make_scale=False,
#     #                    **kwargs):
#     #     """
#     #     Adapting parent dataset creation:
#     #     Additional parameters are
#     #         - long_name or standard_name (either is required. possible to pass both though)
#     #         - units
#     #
#     #     Parameters
#     #     ----------
#     #     name : str
#     #         Name of dataset
#     #     shape : tuple, optional
#     #         Dataset shape. see h5py doc. Default None. Required if data=None.
#     #     dtype : str, optional
#     #         dtype of dataset. see h5py doc. Default is dtype('f')
#     #     data : numpy ndarray, default=None
#     #         Provide data to initialize the dataset.  If not used,
#     #         provide shape and optionally dtype via kwargs (see more in
#     #         h5py documentation regarding arguments for create_dataset
#     #     long_name : str
#     #         The long name (human-readable description of the dataset).
#     #         If None, standard_name must be provided
#     #     standard_name: str or conventions.StandardName
#     #         The standard name of the dataset. If None, long_name must be provided
#     #     units : str, default=None
#     #         Physical units of the data. Can only be None if data is not attached with such attribute,
#     #         e.g. through xarray.
#     #     overwrite : bool, default=None
#     #         If the dataset does not already exist, the new dataset is written and this parameter has no effect.
#     #         If the dataset exists and ...
#     #         ... overwrite is None: h5py behaviour is enabled meaning that if a dataset exists h5py will raise
#     #         ... overwrite is True: dataset is deleted and rewritten according to method parameters
#     #         ... overwrite is False: dataset creation has no effect. Existing dataset is returned.
#     #     chunks : bool or according to h5py.File.create_dataset documentation
#     #         Needs to be True if later resizing is planned
#     #     attrs : dict, optional
#     #         Allows to set attributes directly after dataset creation. Default is
#     #         None, which is an empty dict
#     #     attach_scales : tuple, optional
#     #         Tuple defining the datasets to attach scales to. Content of tuples are
#     #         internal hdf paths. If an axis should not be attached to any axis leave it
#     #         empty (''). Default is ('',) which attaches no scales
#     #         Note: internal hdf5 path is relative w.r.t. this dataset, so be careful
#     #         where to create the dataset and to which to attach the scales!
#     #         Also note, that if data is a xr.DataArray and attach_scales is not None,
#     #         coordinates of xr.DataArray are ignored and only attach_scales is
#     #         considered.
#     #     make_scale: bool, default=False
#     #         Makes this dataset scale. The parameter attach_scale must be uses, thus be None.
#     #     **kwargs
#     #         see documentation of h5py.File.create_dataset
#     #
#     #     Returns
#     #     -------
#     #     ds : h5py.Dataset
#     #         created dataset
#     #     """
#     #     return super().create_dataset(name=name,
#     #                                   shape=shape,
#     #                                   dtype=dtype,
#     #                                   data=data,
#     #                                   overwrite=overwrite,
#     #                                   chunks=chunks,
#     #                                   attrs=attrs,
#     #                                   attach_scales=attach_scales,
#     #                                   make_scale=make_scale,
#     #                                   **kwargs)
#     #     if isinstance(data, str):
#     #         return self.create_string_dataset(name=name,
#     #                                           data=data,
#     #                                           overwrite=overwrite,
#     #                                           standard_name=standard_name,
#     #                                           long_name=long_name,
#     #                                           attrs=attrs,
#     #                                           **kwargs)
#     #     # first get attribute, then check conventions before writing data.
#     #     # metadata may not respect conventions!
#     #     # easiest may be to get shape of data, create dataset with shape, write attributes (during which
#     #     # error may be raised), then write data
#     #     if attrs is None:
#     #         attrs = {}
#     #     if 'units' in attrs and units is not None:
#     #         raise ValueError('Cannot pass units as argument and as attribute')
#     #     if 'units' in attrs:
#     #         units = attrs.pop('units')
#     #
#     #     if isinstance(data, xr.DataArray):
#     #         try:
#     #             data = data.pint.dequantify()
#     #         except:
#     #             pass
#     #         # now check if units is in data:
#     #         if 'units' in data.attrs:
#     #             if units is not None:
#     #                 warnings.warn(
#     #                     'DataArray has units attribute, but units have been passed to create_dataset. '
#     #                     'Will use units from DataArray.')
#     #             units = data.attrs['units']
#     #
#     #         # pass xarray attributes to attrs argument:
#     #         attrs.update(data.attrs)
#     #         data.attrs = {}
#     #
#     #     if units is None:
#     #         if config.require_unit:
#     #             raise UnitsError(f'Units of dataset "{name}" cannot be None.'
#     #                              ' A dimensionless dataset has units "''"')
#     #         attrs['units'] = ''
#     #     else:
#     #         attrs['units'] = units
#     #
#     #     if 'long_name' in attrs and long_name is not None:
#     #         warnings.warn('"long_name" is over-defined.\nYour data array is already associated with the attribute '
#     #                       '"long_name" and you passed the parameter "long_name".\nThe latter will overwrite '
#     #                       'the data array units!')
#     #
#     #     if long_name is not None:
#     #         attrs['long_name'] = long_name
#     #
#     #     if 'standard_name' in attrs and standard_name is not None:
#     #         warnings.warn(f'"standard_name" is over-defined for dataset "{name}". '
#     #                       f'Your data array is associated with the attribute '
#     #                       '"standard_name" and you passed the parameter "standard_name". The latter will overwrite '
#     #                       'the data array units!')
#     #     if standard_name is not None:
#     #         attrs['standard_name'] = standard_name
#     #
#     #     if attrs.get('standard_name') is None and attrs.get('long_name') is None:
#     #         raise RuntimeError(f'No long_name or standard_name is given for dataset "{name}". Either must be provided')
#     #
#     #     return super().create_dataset(name=name,
#     #                                   shape=shape,
#     #                                   dtype=dtype,
#     #                                   data=data,
#     #                                   overwrite=overwrite,
#     #                                   chunks=chunks,
#     #                                   attrs=attrs,
#     #                                   attach_scales=attach_scales,
#     #                                   make_scale=make_scale,
#     #                                   **kwargs)
#     #
#     # def create_string_dataset(self,
#     #                           name: str,
#     #                           data: Union[str, List[str]],
#     #                           overwrite=False,
#     #                           standard_name=None,
#     #                           long_name=None,
#     #                           attrs=None):
#     #     """Create a string dataset. In this version only one string is allowed.
#     #     In future version a list of strings may be allowed, too.
#     #     No long or standard name needed"""
#     #     if attrs is None:
#     #         attrs = {}
#     #     if long_name:
#     #         attrs.update({'long_name': long_name})
#     #     if standard_name:
#     #         attrs.update({'standard_name': long_name})
#     #     return super().create_string_dataset(name, data, overwrite, attrs)
#
#
# # H5Group is depreciated
# class H5Group(Group):
#     """Inherited from Group. Is depreciated. Use Group instead"""
#
#     # def __init__(self, _id):
#     #     warnings.warn('H5Group is depreciated. Use Group instead', DeprecationWarning)
#     #     super(H5Group, self).__init__(self, _id)
#
#
# class TbxWrapperHDF5StructureStrRepr(_repr.HDF5StructureStrRepr):
#     """String representation class for sdump()"""
#
#     def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
#         """string representation of a 0D dataset"""
#         value = h5dataset.values[()]
#         if isinstance(value, float):
#             value = f'{float(value)} '
#         elif isinstance(value, int):
#             value = f'{int(value)} '
#         units = self.get_string_repr_of_unit(h5dataset)
#         return f"\033[1m{name}\033[0m {value} [{units}], dtype: {h5dataset.dtype}"
#
#     def __NDdataset__(self, name, h5dataset):
#         """string representation of a ND dataset"""
#         units = self.get_string_repr_of_unit(h5dataset)
#         return f"\033[1m{name}\033[0m [{units}]: {h5dataset.shape}, dtype: {h5dataset.dtype}"
#
#     @staticmethod
#     def get_string_repr_of_unit(h5dataset: h5py.Dataset) -> str:
#         """Get the unit attribute from the dataset and adjust the string
#         according to the found/not found data"""
#         if 'units' in h5dataset.attrs:
#             try:
#                 _unit = h5dataset.attrs['units']
#             except KeyError:
#                 return 'ERR:NOUNITS'
#
#             if _unit in ('', ' '):
#                 return '-'
#             return _unit
#         return 'N.A.'
#
#
# class TbxWrapperHDF5StructureHTMLRepr(_repr.HDF5StructureHTMLRepr):
#
#     def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
#         _html = super().__0Ddataset__(name, h5dataset)
#         _unit = TbxWrapperHDF5StructureStrRepr.get_string_repr_of_unit(h5dataset)
#         _html += f' [{_unit}]'
#         return _html
#
#     def __NDdataset__(self, name, h5dataset):
#         _html = super().__NDdataset__(name, h5dataset)
#         _unit = TbxWrapperHDF5StructureStrRepr.get_string_repr_of_unit(h5dataset)
#         _html += f' [{_unit}]'
#         return _html
#
#
# class File(core.File, Group):
#     """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
#     It enables additional features and adds new methods streamlining the work with
#     HDF5 files and incorporates usage of so-called naming-conventions and layouts.
#     All features from h5py packages are preserved.
#
#     .. note::
#
#         The additional arguments "title", "institution", "source", "references",
#         "comment" and "standard_name_table" are not part of the HDF5 standard.
#         They are used for storing additional
#         information about the file and its content. They are stored as attributes of the root
#         group. These attributes are based on the CF-conventions [1]_. If a file is created
#         for the first time, these attributes are required and must not be `None`.
#
#
#     Parameters
#     ----------
#     name : str, pathlib.Path, None
#         The (file)name of the file. If None, a temporary file is created in the temporary directory.
#         .. seealso:: :func:`h5rdmtoolbox.UserDir`
#     mode : str
#         The mode in which to open the file. The default is 'r' (read-only).
#     title : str
#         The title of the file. A succinct description of the file content [1]_.
#         Must not be `None` if the file is created for the first time. If None, the title is
#         taken from the file if it exists. If the file does not contain information about the
#         title, an error is raised.
#     institution : str
#         The institution that created the file. Must not be `None` if the file is created for the
#         first time. If None, the institution is taken from the file if it exists. If the file
#         does not contain information about the institution, an error is raised.
#     source : str
#         The source of the data. Numerical/Model-generated data must contain the software/model
#         and its version. Experimental data can be described by the type of measurement and provide
#         references to published experimental setup descriptions [1]_.
#         May be `None`if `references`is provided. Otherwise, it must not be `None` if the file is
#         created for the first time. If None, the source is taken from the file if it exists. If
#         the file does not contain information about the source, an error is raised.
#     references : str
#         References to publications or web-links, where the data or methods used to generate it
#         is described in detail. May be `None`if `source`is provded. Otherwise, it must not be
#         `None` if the file is created for the first time. If None, the references are taken from
#         the file if it exists. If the file does not contain information about the references, an
#         error is raised.
#     standard_name_table : str, StandardNameTabl
#         The standard name table to use. If a string is given, the table is loaded from the
#         registered tables. Must not be None if the file is created for the first time. If None,
#         the table is taken from the file if it exists. If the file does not contain information
#         about the table, an error is raised.
#     comment : str = None
#         Additional comments about the file content. Is optional.
#     layout : str, pathlib.Path, H5Layout, optional
#         The layout to use. If a string is given, the layout is loaded from the registered layouts.
#         If None, the default layout is used.
#     **kwargs
#         Additional arguments passed to h5py.File.
#         .. seealso:: :class:`h5py.File`
#
#
#     .. [1] http://cfconventions.org/cf-conventions/cf-conventions.html#description-of-file-contents
#
#     """
#
#     convention = 'tbx'
#     hdfrepr = _repr.H5Repr(str_repr=TbxWrapperHDF5StructureStrRepr(),
#                            html_repr=TbxWrapperHDF5StructureHTMLRepr())
#
#     # def __init__(self,
#     #              name: Union[str, pathlib.Path, None] = None,
#     #              mode='r',
#     #              *,
#     #              title: str = None,
#     #              institution: str = None,
#     #              source=None,
#     #              references=None,
#     #              standard_name_table=None,
#     #              comment=None,
#     #              layout: Union[pathlib.Path, str, 'H5Layout', None] = 'TbxLayout',
#     #              **kwargs):
#     #     # if file is written for the first time, some mandatory attributes must be given, such as:
#     #     # - title
#     #     # - institution
#     #     # - source
#     #     # - references
#     #     # - standard_name_table
#     #     if name is None:
#     #         read_and_create = True
#     #     else:
#     #         read_and_create = mode == 'r+' and not pathlib.Path(name).exists()
#     #     if mode == 'w' or read_and_create:
#     #         if title is None:
#     #             raise ValueError('Title must be given in write mode.')
#     #         if institution is None:
#     #             raise ValueError('Institution must be given in write mode.')
#     #         if source is None and references is None:
#     #             raise ValueError('Source or references must be given in write mode.')
#     #         if standard_name_table is None:
#     #             raise ValueError('Standard name table must be given in write mode.')
#     #
#     #     super().__init__(name,
#     #                      mode,
#     #                      layout=layout,
#     #                      **kwargs)
#     #
#     #     def _write_non_readonly_attr(name, value):
#     #         if self.mode != 'r':
#     #             self.attrs[name] = value
#     #         else:
#     #             raise RuntimeError(f'No write intent. Cannot write {name}.')
#     #
#     #     for attr in ['institution', 'source', 'references', 'comment']:
#     #         if locals()[attr] is not None:
#     #             _write_non_readonly_attr(attr, locals()[attr])
#     #
#     #     if self.mode != 'r':
#     #         # set title and layout
#     #         if title is not None:
#     #             self.attrs['title'] = title
#     #     else:
#     #         if title is not None:
#     #             raise RuntimeError('No write intent. Cannot write title.')
#     #
#     #     if standard_name_table is not None:
#     #         if isinstance(standard_name_table, str):
#     #             snt = conventions.standard_name.StandardNameTable.load_registered(standard_name_table)
#     #             self.standard_name_table = snt
#     #         elif self.standard_name_table != standard_name_table:
#     #             # update the current snt:
#     #             self.standard_name_table = standard_name_table
#     #     self.layout = layout
#
#
# # H5File is depreciated
# class H5File(File):
#     """Inherited from File. It is depreciated and will be removed in future versions."""
#
#     # def __init__(self, _id):
#     #     warnings.warn('H5File is depreciated. Use File instead', DeprecationWarning)
#     #     super(H5File, self).__init__(self, _id)
#
#
# class Dataset(core.Dataset):
#     """Dataset class following the CF-like conventions"""
#     convention = 'tbx'
#
#
# # H5Dataset is depreciated
# class H5Dataset(Dataset):
#     """Inherited from Dataset. It is depreciated and will be removed in future versions."""
#
#     def __init__(self, _id):
#         warnings.warn('H5Dataset is depreciated. Use Dataset instead', DeprecationWarning)
#         super(H5Dataset, self).__init__(self, _id)
#
#
# Dataset._h5grp = Group
# Dataset._h5ds = Dataset
#
# Group._h5grp = Group
# Group._h5ds = Dataset
#
# # Register standard attributes:
# if False:
#     conventions.units.UnitsAttribute.register(core.Dataset, method_argument=True)
#     conventions.long_name.LongNameAttribute.register((core.Dataset, core.Group))
#     conventions.standard_name.StandardNameAttribute.register(core.Dataset)
#     conventions.standard_name.StandardNameTableAttribute.register((core.Dataset, core.Group, core.File))
#     conventions.title.TitleAttribute.register(File)
#     conventions.references.ReferencesAttribute.register((core.File, core.Dataset, core.Group))
#     conventions.comment.CommentAttribute.register((File, Dataset, Group))
#     conventions.respuser.RespUserAttribute.register((File, Dataset, Group))
