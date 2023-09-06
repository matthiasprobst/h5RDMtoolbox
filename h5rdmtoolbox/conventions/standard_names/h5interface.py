import numpy as np
import pathlib
import xarray as xr
from typing import Dict

import h5rdmtoolbox as h5tbx


class StandardCoordinate:
    """Collection of 1D coordinates"""

    def __init__(self, name, component_names, parent):
        self._parent = parent
        self.name = name
        self.tensor_names = [c.split('_', 1) for c in component_names]
        self.components = {c: getattr(parent, c) for c in component_names}
        self.component_names = sorted(list(self.components.keys()))
        for component in component_names:
            c, _ = component.split('_', 1)
            setattr(self, c.strip('/'), self.components[component])

    def __iter__(self):
        return iter(self.components.values())

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.components[self.component_names[item]]
        return self.components[item]

    def __len__(self):
        return len(self.components)

    def __repr__(self):
        comps = ', '.join(f'"{k}"' for k in self.component_names)
        return f'<{self.__class__.__name__} "{self.name}" n={len(self.components)} components: {comps}>'

    @property
    def shape(self) -> Dict:
        """Return the shape of the coordinate"""
        return {c.basename: c.shape[0] for c in self}


class StandardTensor(StandardCoordinate):

    def get(self, *component_names):
        if len(component_names) == 1:
            if len(component_names[0]) == 1:
                raise ValueError(f'Not enough components given: {component_names}')
            component_names = [c for c in component_names[0]]
        return StandardTensor('velocity', [f'{c}_{self.name}' for c in component_names], self._parent)

    @property
    def ndim(self):
        """Return the dimension of the tensor"""
        return self[0].ndim

    def magnitude(self):
        """Compute the magnitude of the tensor"""
        square = self.components[self.component_names[0]][()].pint.quantify() ** 2
        for c in self.component_names[1:]:
            square += self.components[c][()].pint.quantify() ** 2
        mag = np.sqrt(square).pint.dequantify()

        mag.attrs['standard_name'] = f'magnitude_of_{self.name}'
        return mag

    @property
    def plot(self):
        """Plot the magnitude of the tensor"""
        return HDF5StandardNameInterfacePlotter(self)

    def get_xrdataset(self, create_coords_if_missing: bool = False) -> xr.Dataset:
        """Return a dataset with the components of the tensor as variables"""
        ds = xr.Dataset({n: self[c][()] for n, c in zip(self.component_names, self.components)})
        if not create_coords_if_missing:
            return ds

        if all(len(c.coords()) == 0 for c in self.components.values()):
            for i in range(len(self.components)):
                ds = ds.assign_coords({f'dim_{i}': range(self.components[self.component_names[i]].shape[i])})
        return ds


class HDF5StandardNameInterface:
    """High level interface to HDF5 files following conventions which use
    the standard_name attribute"""

    def __init__(self, standard_dict):

        for k, ds in standard_dict.items():
            if ds.ndim == 0:
                setattr(self, k, ds[()])
            else:
                setattr(self, k, ds)

        standard_names = list(standard_dict.keys())

        for k, ds in standard_dict.items():
            if ds.ndim == 0:
                setattr(self, k, ds[()])
            else:
                setattr(self, k, ds)

        # standard_names = {n: g for g, n in [k.rsplit('/', 1) for k in standard_names]}
        # for k, v in standard_names.items():
        #     if v == '':
        #         standard_names[k] = '/'

        # unique_groups = set(standard_names)
        # groups = {g: [] for g in unique_groups}
        # for k, v in standard_names.items():
        #     groups[v].append(k)

        # identify tensors based on components:
        components = ('x', 'y', 'z')
        tensors_candidates = {}
        import re
        for k, v in standard_dict.items():
            for c in components:
                if re.match(f'^{c}_.*$', k):
                    _, base_quantity = k.split('_', 1)
                    if base_quantity not in tensors_candidates:
                        tensors_candidates[base_quantity] = [k]
                    else:
                        tensors_candidates[base_quantity].append(k)

        self.tensors = []
        self.coords = []
        for k, v in tensors_candidates.items():
            if len(v) > 1:
                if all(standard_dict[c].shape == standard_dict[v[0]].shape for c in v[1:]):
                    vec = StandardTensor(k, v, self)
                    self.tensors.append(vec)
                    setattr(self, k, vec)
                else:
                    coord = StandardCoordinate(k, v, self)
                    self.coords.append(coord)
                    setattr(self, k, coord)
        self.standard_names = standard_names
        self.standard_dict = standard_dict

    @classmethod
    def from_hdf(cls, hdf_filename, group='/'):
        """search withing a group. Note, that duplicate standard names are not considered"""
        from ...database.lazy import lazy
        hdf_filename = pathlib.Path(hdf_filename)
        standard_datasets = {}
        with h5tbx.File(hdf_filename) as h5:
            std_ds = h5[group].find({'standard_name': {'$regex': '.*'}}, rec=False, objfilter='$dataset')
            for ds in std_ds:
                if ds.attrs['standard_name'] not in standard_datasets:
                    standard_datasets[ds.attrs['standard_name']] = lazy(ds)

        #     standard_names = [ds.attrs.raw['standard_name']: ds.parent.name for ds in
        #                       h5[group].find({'standard_name': {'$regex': '.*'}}, rec=False)]
        # standard_datasets = {v + k: h5tbx.database.File(hdf_filename).find_one({'standard_name': k}) for k, v in
        #                      standard_names.items()}
        return cls(standard_datasets)

    def __repr__(self):
        vec_names = '\n  - '.join(v.name for v in self.tensors)
        return f'<{self.__class__.__name__}\n > tensors:\n  - {vec_names}\n > others: ...>'


class HDF5StandardNameInterfacePlotter:
    """Plotting interface for Tensor objects"""

    def __init__(self, tensor):
        self._tensor = tensor

    def __call__(self, *args, **kwargs):
        """Call xarray plot method on the magnitude of the tensor"""
        return self._tensor.magnitude().plot(*args, **kwargs)

    def contourf(self, *args, **kwargs):
        """Call xarray contourf method on the magnitude of the tensor"""
        return self._tensor.magnitude().plot.contourf(*args, **kwargs)

    def quiver(self, **kwargs):
        """Call xarray quiver method on the tensor"""
        ds = self._tensor.get_xrdataset(create_coords_if_missing=True)
        return ds.plot.quiver(*list(ds.coords), *list(ds.data_vars), **kwargs)
