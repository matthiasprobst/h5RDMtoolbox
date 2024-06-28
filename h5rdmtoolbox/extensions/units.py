import xarray as xr
from typing import Optional

from h5rdmtoolbox import get_ureg
from h5rdmtoolbox.protocols import H5TbxDataset
from h5rdmtoolbox.wrapper.accessor import Accessor, register_accessor


class ToUnitsInterface:
    def __init__(self,
                 dataset: H5TbxDataset,
                 dataset_unit: Optional[str] = None,
                 **coord_units):
        self.dataset = dataset
        self.dataset_unit = dataset_unit
        self.coord_units = coord_units

    def _convert_units(self, data: xr.DataArray):
        assert isinstance(data, xr.DataArray)
        assert 'units' in data.attrs, 'No units attribute found in the dataset'
        for c, cn in self.coord_units.items():
            assert 'units' in data.coords[c].attrs, f'No units attribute found in the coordinate {c}'
            data.coords[c] = data.coords[c].pint.quantify(unit_registry=get_ureg()).pint.to(
                self.coord_units[c]).pint.dequantify()
        # convert units
        if self.dataset_unit is None:
            return data
        return data.pint.quantify(unit_registry=get_ureg()).pint.to(self.dataset_unit).pint.dequantify()

    def sel(self, method=None, **coords) -> xr.DataArray:
        return self._convert_units(self.dataset.sel(method=method, **coords))

    def isel(self, **indexers) -> xr.DataArray:
        return self._convert_units(self.dataset.isel(**indexers))

    def __getitem__(self, *args, **kwargs):
        return self._convert_units(self.dataset.__getitem__(*args, **kwargs))


@register_accessor("to_units", "Dataset")
class ToUnitsAccessor(Accessor):
    """Accessor to await selected data to be converted to a new units"""

    def __call__(self, dataset_unit: Optional[str] = None, **coord_units) -> ToUnitsInterface:
        return ToUnitsInterface(self._obj, dataset_unit=dataset_unit, **coord_units)
