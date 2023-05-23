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
                ds = self._grp[arg]
            elif isinstance(arg, h5py.Dataset):
                ds = arg
            else:
                raise TypeError(f'Invalid type: {type(arg)}')
            hdf_datasets[ds.name.strip('/')] = ds

        for name, ds in kwargs.items():
            if isinstance(ds, str):
                ds = self._grp[ds]
            elif not isinstance(ds, h5py.Dataset):
                raise TypeError(f'Invalid type: {type(ds)}')
            hdf_datasets[name.strip('/')] = ds

        return HDFXrDataset(**hdf_datasets)
