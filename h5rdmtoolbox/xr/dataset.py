import xarray as xr


class HDFXrDataset:
    """HDF interface to a Xr.Dataset which is returned on demand when sliced"""

    def __init__(self, *datasets):
        self._datasets = datasets

    def __getitem__(self, item) -> xr.DataArray:
        return xr.merge([da.__getitem__(item) for da in self._datasets])
