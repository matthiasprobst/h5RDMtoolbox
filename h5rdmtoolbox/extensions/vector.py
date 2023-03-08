import h5py

# noinspection PyUnresolvedReferences
from . import magnitude  # automatically make magnitude available
from .xr.dataset import HDFXrDataset
from ..wrapper.accessory import Accessor, register_special_dataset
from ..wrapper.core import Group, File


@register_special_dataset("Vector", Group)
@register_special_dataset("Vector", File)
class VectorDataset(Accessor):
    """A special dataset for vector data.
     The vector components are stored in the group as datasets."""

    def __init__(self, h5grp: h5py.Group):
        self._grp = h5grp

    def __call__(self, *args, **kwargs) -> HDFXrDataset:
        """Returns a xarray dataset with the vector components as data variables."""
        if len(args) and len(kwargs):
            raise ValueError('Either args or kwargs must be provided but not both')
        hdf_datasets = {}
        for arg in args:
            if isinstance(arg, str):
                ds = self._grp[arg]
            elif isinstance(arg, h5py.Dataset):
                ds = arg
            else:
                raise TypeError(f'Invalid type: {type(arg)}')
            hdf_datasets[ds.name.strip('/')] = ds

        for name, ds in kwargs.items():
            if not isinstance(ds, h5py.Dataset):
                raise TypeError(f'Invalid type: {type(ds)}')
            hdf_datasets[name.strip('/')] = ds

        return HDFXrDataset(**hdf_datasets)
