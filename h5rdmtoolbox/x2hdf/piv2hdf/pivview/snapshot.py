import json
import logging
from pathlib import Path
from typing import Tuple

import h5py
import numpy as np
import pandas as pd

from . import core
from .utils import _get_header_line, _get_headernames_from_pivview_dat, _get_ijk_from_pivview_dat, \
    _get_first_N_lines_from_file
from ..utils import PIVviewFlag
from ..nc import process_pivview_nc_data
from ..par import PivViewParFile, PivViewConfigFile
from ....conventions.translations import pivview_name_to_standard_name

logger = logging.getLogger('x2hdf')


class NotAFileError(Exception):

    def __init__(self, filename):
        self.filename = filename
        self.message = f'"{filename}" is not a file.'
        super().__init__(self.message)


class PIVSnapshot(core.PIVNCConverter):
    """Converter class to build a single hdf file from a single nc file containing pivview data"""

    _is_2d2c: bool = None
    parameter_file: Path = None

    def __init__(self, name: Path, recording_time: float,
                 ignore_parameter_file: bool = False):
        """
        name: Path
            Path to the netCDF4 file.
        recording_time : float, default
            Time in seconds when snapshot was taken relative to the start of the PIV recording.
            First snapshot of a plane gets recording_time=0
        ignore_parameter_file: bool, optional=False
            Ignore PIVview parameters (or configuration). If True, no effort is
            spent in reading a parameter or configuration file located in the
            plane folder.
        """
        name = Path(name)
        if not name.is_file():
            raise NotAFileError(name)

        super().__init__(Path(name))

        if not self.is_snapshot():
            raise core.PIVConversionInputError(self.name, self)

        self.recording_time = recording_time
        self.ignore_parameter_file = ignore_parameter_file
        if not ignore_parameter_file:
            # load parameter/config file from file if exists
            self.parameter_file = core.get_parameter_file_from_plane(self.name.parent)

    @property
    def is_2d2c(self):
        return self._is_2d2c

    def _get_nc_data(self, build_coord_datasets=True):
        masking = self.configuration['masking']
        interpolation = self.configuration['interpolation']
        apply_mask = self.configuration['apply_mask']
        z_source = core.PIV_Z_Source(self.configuration['z_source']).value
        return process_pivview_nc_data(self.name, z_source=z_source,
                                       timestep=self.recording_time,
                                       masking=masking,
                                       interpolate=interpolation,
                                       apply_mask=apply_mask,
                                       build_coord_datasets=build_coord_datasets)

    @core.piv_conversion
    def convert(self, target_hdf_filename: Path = None,
                configuration: dict or Path = None,
                create_hdf: bool = True,
                build_coord_datasets: bool = True) -> Tuple[dict, dict, dict]:
        """
        Converting method to convert input data into a single Case HDF file.

        Parameters
        ----------
        target_hdf_filename : pathlib.Path
            hdf file to fill with data from multiple planes --> case hdf file
        configuration: dict or Path, optional=False
            Dictionary or path to yaml file. The configuration must provide the
            following keys:
                - interpolation
                - apply_mask
                - masking (if apply_mask==True)
                - z_source
            The default loads the user (default) configuration from the yaml file
            located at the tmp user data dir.
        create_hdf: bool, optional=True
            Whether to create an HDF file. Default is True. If False, nc data is available
            for further processing.

        Returns
        -------
        target_hdf_filename: pathlib.Path
            The file name of the snapshot hdf file
        """
        super().convert(target_hdf_filename, configuration)

        # read data from nc_file
        nc_data, nc_root_attr, nc_variable_attr = self._get_nc_data(create_hdf)
        self._is_2d2c = 'w' not in nc_data

        self.ny, self.nx = nc_data['dx'].shape

        # change some attribute names to meet standard name convention:
        nc_root_attr['filename'] = nc_root_attr.pop('long_name')

        if not create_hdf:
            return nc_data, nc_root_attr, nc_variable_attr

        # building HDF file
        if target_hdf_filename is None:
            self.hdf_filename = Path.joinpath(self.name.parent, f'{self.name.stem}.hdf')
        else:
            self.hdf_filename = target_hdf_filename

        with h5py.File(self.hdf_filename, "w") as main:
            main.attrs['plane_directory'] = str(self.name.parent.resolve())
            main.attrs['software'] = 'PIVTec PIVview'
            if not self.ignore_parameter_file:
                if self.parameter_file is not None:
                    if self.parameter_file.suffix == '.par':
                        par = PivViewParFile()
                    else:
                        par = PivViewConfigFile()
                    par.read(self.parameter_file)
                    main.attrs[core.PIV_PARAMTER_HDF_NAME] = json.dumps(par.to_dict())
                else:
                    par = PivViewConfigFile()
                    par.read_nc(self.name)
                    main.attrs[core.PIV_PARAMTER_HDF_NAME] = json.dumps(par.to_dict())

            for i, cname in enumerate(('x', 'y', 'ix', 'iy')):
                ds = main.create_dataset(
                    name=cname, shape=nc_data[cname].shape,
                    maxshape=nc_data[cname].shape,
                    chunks=nc_data[cname].shape,
                    data=nc_data[cname], dtype=nc_data[cname].dtype,
                    compression=self.configuration['compression'],
                    compression_opts=self.configuration['compression_opts'])
                for k, v in nc_variable_attr[cname].items():
                    ds.attrs[k] = v
                ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[cname])

            for i, cname in enumerate(('z', 'time')):
                ds = main.create_dataset(cname, data=nc_data[cname])
                for k, v in nc_variable_attr[cname].items():
                    ds.attrs[k] = v
                ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[cname])

            # Data Arrays
            _shape = (self.ny, self.nx)
            for k, v in nc_data.items():
                if k not in core.DIM_NAMES:
                    ds = main.create_dataset(
                        name=k, shape=_shape, dtype=v.dtype,
                        maxshape=_shape,
                        chunks=_shape,
                        compression=self.configuration['compression'],
                        compression_opts=self.configuration['compression_opts'])
                    ds[:] = v
                    for ic, c in enumerate((('y', 'iy'), ('x', 'ix'))):
                        ds.dims[ic].attach_scale(main[c[0]])
                        ds.dims[ic].attach_scale(main[c[1]])
                    ds.attrs['COORDINATES'] = ['time', 'z']

                    if k in nc_variable_attr:
                        for attr_key, attr_val in nc_variable_attr[k].items():
                            if attr_key not in core.IGNORE_ATTRS:
                                ds.attrs[attr_key] = attr_val
            # pivflags explanation:
            unique_flags = np.unique(main['piv_flags'][:])
            main['piv_flags'].attrs['flag_translation'] = json.dumps({str(PIVviewFlag(u)): int(u) for u in unique_flags})
        return nc_data, nc_root_attr, nc_variable_attr

    def _coordinates_from_nc(self):
        """returns x,y,z datasets from snapshot nc data"""

    def to_vtk(self, vtk_filename_wo_ext: str = None) -> Path:
        """converts the hdf file into vtk file. only considers time averages!

        Parameters
        ----------
        vtk_filename_wo_ext : pathlib.Path
            File name without suffix to write vtk data to.

        Returns
        -------
        vtk filename
        """
        from ..vtk_utils import result_3D_to_vtk
        super().to_vtk(vtk_filename_wo_suffix=vtk_filename_wo_ext)

        data = dict()
        with h5py.File(self.hdf_filename, 'r') as h5:
            x = h5['x'][()]
            y = h5['y'][()]
            z = h5['z'][()]
            xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
            data['x'] = xx  # vtk only accepts 3d data
            data['y'] = yy
            data['z'] = zz
            for k in h5.keys():
                if k not in ('x', 'y', 'z', 'time', 'ix', 'iy'):
                    if isinstance(h5[k], h5py.Dataset):
                        ds = h5[k]
                        if ds.ndim == 5:
                            for i in range(ds.shape[-1]):
                                data[f'{ds.name}-{i}'] = ds[:, 0, ..., i].T
                        else:
                            data[k] = ds[:, 0, ...].T

        if 'valid' in data:  # bool is not allowed --> change to int
            data['valid'] = data['valid'].astype(int)

        _, vtk_path = result_3D_to_vtk(data, target_filename=str(self.vtk_file_name))
        return Path(vtk_path)

    def use_nc_pivview_parameters(self, overwrite: bool = False) -> None:
        """Reads the PIVview parameters stored in the nc file and writes it to a root attribute.
        Useful function if parameter/config file is not available at plane level."""
        p = PivViewParFile()
        p.read_nc(self.name)
        with h5py.File(self.hdf_filename, 'r+') as h5:
            if core.PIV_PARAMTER_HDF_NAME in h5.attrs:
                if not overwrite:
                    print('PIVview parameters exist and overwrite was set to False! Nothing changed!')
                    return
            h5.attrs[core.PIV_PARAMTER_HDF_NAME] = p.to_json_dict()

    def get_parameters(self):
        if self.parameter_file:
            if self.parameter_file.suffix == '.par':
                par = PivViewParFile()
            else:
                par = PivViewConfigFile()
            par.read(self.parameter_file)
            return par


class PIVSnapshotDatFile(core.PIVConverter):

    def convert(self, target_hdf_filename: Path = None, timestep: float = 0.,
                configuration: dict or Path = None,
                create_hdf: bool = True) -> Path or None:
        """
        Converting method to convert input data into a single Case HDF file.

        Parameters
        ----------
        target_hdf_filename : pathlib.Path
            hdf file to fill with data from multiple planes --> case hdf file
        timestep: float, optional=0.
            Relative time in seconds since start of recording
        configuration: dict or Path, optional=False
            Dictionary or path to yaml file. The configuration must provide the
            following keys:
                - attr_unit_name
        create_hdf: bool, optional=True
            Whether to create an HDF file. Default is True. If False, nc data is available
            for further processing.

        Returns
        -------
        target_hdf_filename: pathlib.Path
            The file name of the snapshot hdf file
        """
        super().convert(target_hdf_filename, configuration)

        variable_names = _get_headernames_from_pivview_dat(self.name)
        variable_names.append('ignore')  # needed because PivView has a space at end of line...
        nx, ny, K = _get_ijk_from_pivview_dat(self.name)
        iheader = _get_header_line(self.name)

        df = pd.read_csv(self.name, header=iheader + 2, sep=' ', names=variable_names)
        variable_dict = {}
        for variable_name in variable_names:
            if variable_name != 'ignore':
                variable_dict[variable_name] = df[variable_name].values.reshape((ny, nx))

        x = variable_dict['x'][0, :]
        y = variable_dict['y'][:, 0]
        z = float(variable_dict['z'][0, 0])
        variable_dict['x'] = x
        variable_dict['y'] = y
        variable_dict['z'] = z

        variable_dict['time'] = timestep

        # get units from header:
        variable_units_dict = {vname: '' for vname in variable_dict.keys()}
        variable_long_name_dict = {vname: vname for vname in variable_dict.keys()}

        lines = _get_first_N_lines_from_file(self.name, iheader)
        for line in lines:
            if '# var' in line:
                _line = line.strip()
                _split = _line.split(' - ')
                _var_name = _split[0].split('\'')[1]
                if f': \'{_var_name}\'' in _line:  # found line describing the variable
                    _info = _split[1].split(' in ')
                    if len(_info) == 1:
                        long_name = _info[0]
                        _unit = ' '
                    else:
                        long_name = _info[0]
                        _unit = _info[1][1:-1]
                    variable_units_dict[_var_name] = _unit
                    variable_long_name_dict[_var_name] = long_name

        if not create_hdf:
            return

        if target_hdf_filename is None:
            self.hdf_filename = Path(self.name.__str__().replace(".dat", ".hdf"))
        else:
            self.hdf_filename = Path(target_hdf_filename)

        with h5py.File(target_hdf_filename, 'w') as h5:
            for variable_name, variable_data in variable_dict.items():
                if not isinstance(variable_data, float):
                    ds = h5.create_dataset(variable_name, data=variable_data,
                                           chunks=variable_data.shape,
                                           maxshape=variable_data.shape,
                                           compression=self.configuration['compression'],
                                           compression_opts=self.configuration['compression_opts'])
                else:
                    ds = h5.create_dataset(variable_name, data=variable_data)
                ds.attrs['units'] = variable_units_dict[variable_name]
                ds.attrs['long_name'] = variable_long_name_dict[variable_name]

                if variable_name == 'z':
                    ds.attrs['standard_name'] = pivview_name_to_standard_name['z']
                elif variable_name == 'x':
                    ds.attrs['standard_name'] = pivview_name_to_standard_name['x']
                    ds.make_scale()
                elif variable_name == 'y':
                    ds.attrs['standard_name'] = pivview_name_to_standard_name['y']
                    ds.make_scale()
                elif variable_name == 'time':
                    ds.attrs['standard_name'] = pivview_name_to_standard_name['time']
                    ds.make_scale()
                else:
                    ds.attrs['COORDINATES'] = ['z', ]

            for variable_name in variable_dict.keys():
                if variable_name not in core.DIM_NAMES:
                    for idim, dn in enumerate(('y', 'x')):
                        h5[variable_name].dims[idim].attach_scale(h5[dn])
        return target_hdf_filename
