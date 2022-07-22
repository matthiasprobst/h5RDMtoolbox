from pathlib import Path
from typing import Dict

import h5py
import numpy as np

try:
    from pyevtk.hl import gridToVTK
except ImportError:
    ImportError('Package pyevtk not installed.')

try:
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk
except ImportError:
    ImportError('Package vtk not installed.')


def get_time_average_data_from_piv_case(hdf_input: Path or h5py.Group) -> Dict:
    """collects time-averaged data from a HDF PIV MULTI-PLANE and returns data as dictionary

    Parameters
    ----------
    hdf_input : Path or h5py.Group
        hdf filename or root group

    Returns
    --------
    data : Dict
    """

    def _collect(_h5, _data):
        _data['x'] = _h5['x'][()]  # vtk only accepts 3d data
        _data['y'] = _h5['y'][()]
        _data['z'] = _h5['z'][()]
        ta = _h5['timeAverages']
        for k in ta.keys():
            ds = ta[k]
            if ds.ndim == 4:
                for i in range(ds.shape[-1]):
                    _data[f'{ds.name}-{i}'] = ds[..., i].T
            else:
                _data[k] = ds[...].T
        return _data

    data = dict()
    if isinstance(hdf_input, h5py.Group):
        return _collect(hdf_input, data)

    with h5py.File(hdf_input, 'r') as h5:
        data = _collect(h5, data)
    return data


def result_3D_to_vtk(data3: Dict, target_filename: str = None):
    """
    Saves 3D interpolated data in VTK regular grid format. Preconditioning to
    fortran style is handled in core function. Either to file or back to mayavi.

    Parameters
    ----------
    data3 : dict
        Input full 3D data as specified from above.
    target_filename : Path, optional=None
        If filepath given data is written to file.

    Returns
    -------
    vtkData : vtkRectilinearGrid
        The vtk gridded data for use in mayavi.
    file : 'str'
        vtk file name if passed

    Notes
    -----
    Credits to M. Elfner (ITS, Karlsruhe Institute of Technology)

    """
    pointDataRG, (xr, yr, zr) = precondition_grid_data(data3)

    save_to_file = True
    if target_filename is None:
        save_to_file = False

    file = None
    if save_to_file:
        file = gridToVTK(target_filename.__str__(), xr, yr, zr, pointData=pointDataRG)

    vtkData = numpy_data_to_rectgrid(xr, yr, zr, pointDataRG)

    return vtkData, file


def precondition_grid_data(datadict, invalidKeys=['x', 'y', 'z', 'info', 'nodes', 'transformAx']):
    """
    Preconditions numpy data for rectilinear grid in vtk. Now the rect grid is
    way way faster in post. Since paraview sucks so hard, everything is turned
    to fortran before saving...

    Parameters
    ----------
    datadict : dict
        Input dict with 3d PIV data, X, Y, Z are needed specifying the grid.
    invalidKeys : TYPE, optional
        Keys to remove from dict since they will kill paraview. The default is
        ['x', 'y', 'z', 'info', 'nodes'].

    Returns
    -------
    datadict : dict
        Dict with core reshaped data.
    tuple
        Coordinate arrays

    """
    xr, yr, zr = np.unique(datadict.pop('x')), np.unique(datadict.pop('y')), np.unique(datadict.pop('z'))
    # remove some invalid keys
    for s in invalidKeys:
        try:
            datadict.pop(s)
        except KeyError:
            ...
    # convert and save
    for k, v in datadict.items():
        if v.ndim > 3:
            datadict[k] = tuple(np.asfortranarray(v[..., i]).ravel('F') for i in range(v.shape[-1]))
        else:
            datadict[k] = np.asfortranarray(v).ravel('F')

    return datadict, (xr, yr, zr)


def numpy_data_to_rectgrid(x, y, z, data):
    """
    Creates a rectilinear dataset from numpy data as used in standard cases.
    DATA MUST BE PRECONDITIONED WITH FUNCTION ABOVE!!

    Parameters
    ----------
    x, y, z : np.ndarray
        1D point arrays specifyfing nodes on each axis.
    data : dict
        Dict with scalar or vector point data.

    Raises
    ------
    RuntimeError
        If data input problems occur.

    Returns
    -------
    rg : vtkRectilinearGrid
        The grid built from the numpy dataset.
    """

    def _pack(array, name):
        valid = False
        if isinstance(array, np.ndarray):
            if array.ndim == 1:
                dV = numpy_to_vtk(array, deep=True, array_type=vtk.VTK_FLOAT)
                dV.SetName(name)
                valid = True

        elif isinstance(array, tuple):
            if len(array) == 3:
                dV = np.asfortranarray(np.array(array).T)
                dV = numpy_to_vtk(dV, deep=True, array_type=vtk.VTK_FLOAT)
                dV.SetName(name)
                valid = True

        if not valid:
            raise RuntimeError('Cant convert data for vtk RG')

        return dV

    # Initialize
    rg = vtk.vtkRectilinearGrid()

    rg.SetDimensions(len(x), len(y), len(z))
    # set nodes
    rg.SetXCoordinates(numpy_to_vtk(x, deep=1, array_type=vtk.VTK_FLOAT))
    rg.SetYCoordinates(numpy_to_vtk(y, deep=1, array_type=vtk.VTK_FLOAT))
    rg.SetZCoordinates(numpy_to_vtk(z, deep=1, array_type=vtk.VTK_FLOAT))

    # Add data
    if isinstance(data, np.ndarray):
        _ = rg.GetPointData().AddArray(_pack(data, 'dfield_1'))

    elif isinstance(data, dict):
        for k, v in data.items():
            # if isinstance(v, tuple): continue
            _ = rg.GetPointData().AddArray(_pack(v, k))

    else:
        raise RuntimeError('Unsupported data type!')

    return rg
