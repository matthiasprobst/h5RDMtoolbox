import h5py
import xarray as xr
from typing import List, Tuple

# noinspection PyUnresolvedReferences
from . import magnitude  # automatically make magnitude available
from ..wrapper.accessory import Accessory, register_special_dataset
from ..wrapper.core import Group, File


class HDFXrDataset:
    """HDF interface to a Xr.Dataset which is returned on demand when sliced"""

    def __init__(self, **datasets):
        self._datasets = dict(datasets)
        shapes = [d.shape for d in self._datasets.values()]
        if not all([shapes[0] == s for s in shapes[1:]]):
            raise ValueError('Datasets must have equal shapes!')

        self._data_vars = list(self._datasets.keys())
        self._shape = self._datasets[self._data_vars[0]].shape

    def __getitem__(self, item) -> xr.Dataset:
        return xr.merge([da.__getitem__(item).rename(k) for k, da in self._datasets.items()])

    def __repr__(self):
        return f'<HDF-XrDataset (shape {self.shape} data_vars: {self.data_vars})>'

    @property
    def data_vars(self) -> List[str]:
        """List of data variables in the dataset"""
        return self._data_vars

    @property
    def shape(self) -> Tuple[int]:
        """Shape of the dataset (taken from the first dataset)"""
        return self._shape


@register_special_dataset("Vector", Group)
@register_special_dataset("Vector", File)
class VectorDataset(Accessory):
    """A special dataset for vector data.
     The vector components are stored in the group as datasets."""

    def __call__(self, *args, **kwargs) -> HDFXrDataset:
        """Returns a xarray dataset with the vector components as data variables.

        Either dataset names or datasets can be provided as arguments or keyword arguments.
        For the latter, the keys are used for the dataset names in the resulting xarray-dataset.

        Examples
        --------
        >>> import h5rdmtoolbox as h5tbx
        >>> import numpy as np
        >>> from h5rdmtoolbox.extensions import vector

        >>> with h5tbx.File() as h5:
        ...     h5.create_dataset('u', data=np.random.rand(21, 10)))
        ...     h5.create_dataset('v', data=np.random.rand(21, 10))
        ...     h5.create_dataset('w', data=np.random.rand(21, 10))
        ...     h5.Vector(uvel='u', vvel='v', wvel='w')
        """
        if len(args) and len(kwargs):
            raise ValueError('Either args or kwargs must be provided but not both')
        hdf_datasets = {}
        for arg in args:
            if isinstance(arg, str):
                ds = self._obj[arg]
            elif isinstance(arg, h5py.Dataset):
                ds = arg
            else:
                raise TypeError(f'Invalid type: {type(arg)}')
            hdf_datasets[ds.name.strip('/')] = ds

        for name, ds in kwargs.items():
            if isinstance(ds, str):
                ds = self._obj[ds]
            elif not isinstance(ds, h5py.Dataset):
                raise TypeError(f'Invalid type: {type(ds)}')
            hdf_datasets[name.strip('/')] = ds

        return HDFXrDataset(**hdf_datasets)
