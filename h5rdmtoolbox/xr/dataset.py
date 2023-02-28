import xarray as xr


class HDFXrDataset:
    """HDF interface to a Xr.Dataset which is returned on demand when sliced"""

    def __init__(self, **datasets):
        self._datasets = dict(datasets)
        shapes = [d.shape for d in self._datasets.values()]
        if not all([shapes[0] == s for s in shapes[1:]]):
            raise ValueError('Datasets must have equal shapes!')

        self._data_vars = list(self._datasets.keys())
        self._shape = self._datasets[self._data_vars[0]].shape

    def __getitem__(self, item) -> xr.DataArray:
        return xr.merge([da.__getitem__(item) for da in self._datasets.values()])

    def __repr__(self):
        return f'<HDF-XrDataset (shape {self.shape} data_vars: {self.data_vars})>'

    @property
    def data_vars(self):
        return self._data_vars

    @property
    def shape(self):
        return self._shape
