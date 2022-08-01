import h5py
import numpy as np
import xarray as xr

__version__ = '0.1.0'


@xr.register_dataarray_accessor("hdf")
class HDFArrayAccessor:
    """Accessor class that allows to write a Data Array to an HDF5 group"""

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def to_group(self, h5group: h5py.Group, name=None, overwrite: bool = False, **kwargs) -> h5py.Dataset:
        """Saves the xarray DataArray in a group.
        Parameters
        ----------
        h5group: h5py.Group
            HDF5 group to write dataset into
        name: str, optional=None
            Name of hdf dataset. overwrites name of xr.DataArray
        overwrite: bool, optional=False
            Whether to overwrite an existing dataset with that name
        """
        h5group = h5py.Group(h5group.id)
        if not self._obj.name and name is None:
            raise AttributeError(f'Data Array has no name and no name is passed as function parameter.')
        if self._obj.name and name is None:
            name = self._obj.name
        if name in h5group and overwrite:
            del h5group[name]
        elif name in h5group and not overwrite:
            raise ValueError(f'A dataset with that name already exists and overwrite is set to false.')

        ds_attrs = kwargs.pop('attrs', {})
        ds_attrs.update(self._obj.attrs)

        for coord in self._obj.coords:
            if coord in h5group:  # coordinate already exists:
                _raise = False
                if h5group[coord].ndim == 0:
                    if float(h5group[coord][()].values) != float(self._obj.coords[coord].values[()]):
                        _raise = True
                else:
                    if not np.array_equal(h5group[coord][()].values, self._obj.coords[coord].values):
                        _raise = True
                if _raise:
                    raise ValueError(f'The xarray coordinate "{coord}" exists already '
                                     f'in the HDF group "{h5group.name}" with that name but with '
                                     'different values. \nCannot create the dataset '
                                     f'"{name}". Either delete the existing coordinate dataset '
                                     'or write the dataset to a different group.')

        attach_scales = []
        coordinates_0dim = []

        for coord in self._obj.coords:
            if coord not in h5group:
                cds = h5group.create_dataset(coord, data=self._obj.coords[coord].values,
                                             attrs=self._obj.coords[coord].attrs,
                                             **kwargs)
                cds.make_scale()

            if 'REFERENCE_LIST' not in h5group[coord].attrs:
                h5group[coord].make_scale()

            if self._obj.coords[coord].ndim == 0:
                coordinates_0dim.append(coord)  # will be written to attribute "COORDINATES"
            else:
                attach_scales.append(coord)

        dset = h5group.create_dataset(name, data=self._obj.data)
        for k, v in ds_attrs.items():
            dset.attrs[k] = v

        # TODO check that there are "intermediate" coords like ix(x), iy(y)
        for i, s in enumerate(self._obj.dims):
            if s in self._obj.coords:
                dset.dims[i].attach_scale(h5group[s])

        if coordinates_0dim:
            dset.attrs['COORDINATES'] = coordinates_0dim
        return dset
