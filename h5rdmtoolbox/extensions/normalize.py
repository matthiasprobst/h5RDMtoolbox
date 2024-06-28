"""Extension to compute normalized xarray datasets and arrays"""
import xarray as xr
from typing import Union, Dict

from h5rdmtoolbox import get_ureg
from h5rdmtoolbox.protocols import H5TbxDataset
from h5rdmtoolbox.wrapper.accessor import Accessor, register_accessor

NORM_DELIMITER = '/'


class NormalizationInterface:

    def __init__(self,
                 dataset: H5TbxDataset,
                 norm_data: Dict[str, Union[float, str]],
                 name: bool = False):
        self.dataset = dataset
        self._coord_names = list(dataset.coords)
        self.norm_data: Dict = norm_data
        self.cnorm_data: Dict = {}
        self.cnorm_name: Dict = {}
        self.name = name

    def __getattr__(self, item: str):
        if item in self._coord_names:
            return CoordNormalizationInterface(item, self)
        return super().__getattribute__(item)

    def _normalize(self, data: xr.DataArray) -> xr.DataArray:
        assert isinstance(data, xr.DataArray)
        quantified_data = data.pint.quantify(unit_registry=get_ureg())
        new_name = self.dataset.basename
        for k, v in self.norm_data.items():
            new_name += f'{NORM_DELIMITER}{k}'
            if isinstance(v, str):
                q = get_ureg().Quantity(v)
                quantified_data = quantified_data / q
            elif isinstance(v, (int, float)):
                quantified_data = quantified_data / v
            else:
                raise TypeError(f'Normalization must be either a string or a number, not {type(v)}.')

        ret = quantified_data.pint.dequantify()
        if self.name:
            ret.name = self.name
        else:
            ret.name = new_name

        # normalize coordinates:
        for coord_name, norm_dict in self.cnorm_data.items():
            new_cname = coord_name
            quantified_coord_data = quantified_data.coords[coord_name].pint.quantify(unit_registry=get_ureg())
            for k, v in norm_dict.items():
                new_cname += f'{NORM_DELIMITER}{k}'
                if isinstance(v, str):
                    q = get_ureg().Quantity(v)
                    quantified_coord_data = quantified_coord_data / q
                elif isinstance(v, (int, float)):
                    quantified_coord_data = quantified_coord_data / v
                else:
                    raise TypeError(f'Normalization must be either a string or a number, not {type(v)}.')

            ret.coords[coord_name] = quantified_coord_data.pint.dequantify()
            ret = ret.rename({coord_name: self.cnorm_name.get(coord_name, new_cname)})

        return ret

    def sel(self, method=None, **coords) -> xr.DataArray:
        return self._normalize(self.dataset.sel(method=method, **coords))

    def isel(self, **indexers) -> xr.DataArray:
        return self._normalize(self.dataset.isel(**indexers))

    def __getitem__(self, *args, **kwargs):
        return self._normalize(self.dataset.__getitem__(*args, **kwargs))


class CoordNormalizationInterface:
    def __init__(self, name: str, ni: NormalizationInterface):
        self._ni = ni
        self._name = name

    def __call__(self,
                 name=None,
                 **norm_data: Dict[str, Union[float, str]]) -> NormalizationInterface:
        self._ni.cnorm_data[self._name] = norm_data
        if name is not None:
            self._ni.cnorm_name[self._name] = name
        return self._ni


@register_accessor("normalize", "Dataset")
class ToUnitsAccessor(Accessor):
    """Accessor to await selected data to be converted to a new units"""

    def __call__(self,
                 name=None,
                 **norm_data: Dict[str, Union[float, str]]) -> NormalizationInterface:
        assert len(norm_data) > 0, "No normalization data given!"
        return NormalizationInterface(self._obj,
                                      norm_data=norm_data,
                                      name=name)
