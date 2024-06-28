"""Extension to compute magnitude of xarray datasets"""
import h5py
import numpy as np
import xarray as xr
from typing import Dict, Optional

from h5rdmtoolbox.protocols import H5TbxDataset
from h5rdmtoolbox.wrapper.accessor import Accessor, register_accessor


class MagnitudeInterface:
    def __init__(self,
                 datasets: Dict[str, H5TbxDataset],
                 name: Optional[str] = None,
                 keep_attrs: bool = False):
        self.datasets = datasets
        self.name = name
        self.keep_attrs = keep_attrs

    def _compute_magnitude(self, datasets):
        assert len(datasets) > 1, 'At least two datasets are required to compute magnitude'
        keys = list(datasets.keys())
        mag2 = datasets[keys[0]].pint.quantify() ** 2
        with xr.set_options(keep_attrs=self.keep_attrs):
            for key in keys[1:]:
                mag2 += datasets[key].pint.quantify() ** 2

        mag = np.sqrt(mag2).pint.dequantify()
        if self.name is None:
            mag.name = 'magnitude_of_' + '_and_'.join(k.replace(' ', '_') for k in keys)
        else:
            mag.name = self.name
        return mag

    def __getitem__(self, *args, **kwargs):
        return self._compute_magnitude(
            {k: v.__getitem__(*args, **kwargs) for k, v in self.datasets.items()}
        )

    def isel(self, **indexers):
        return self._compute_magnitude(
            {k: v.isel(**indexers) for k, v in self.datasets.items()}
        )

    def sel(self, method=None, **coords):
        return self._compute_magnitude(
            {k: v.sel(method=method, **coords) for k, v in self.datasets.items()}
        )


@register_accessor("Magnitude", "Group")
@register_accessor("Magnitude", "File")
class Magnitude(Accessor):
    def __call__(self, *datasets, name: Optional[str] = None, keep_attrs: bool = False) -> MagnitudeInterface:
        if len(datasets) < 2:
            raise ValueError('Please provide at least two datasets to compute magnitude')
        hdf_datasets = {}
        for dataset in datasets:
            if isinstance(dataset, str):
                ds = self._obj[dataset]
            elif isinstance(dataset, h5py.Dataset):
                ds = dataset
            else:
                raise TypeError(f'Invalid type: {type(dataset)}')
            hdf_datasets[ds.name.strip('/')] = ds

        return MagnitudeInterface(hdf_datasets, name=name, keep_attrs=keep_attrs)
