import ipyvolume as ipv
import matplotlib.cm
import matplotlib.pyplot as plt
import numpy as np
import warnings
import xarray as xr
from matplotlib.colors import BoundaryNorm, Normalize


def _color_from_values(arr, cmap="jet", levels=None, vmin=None, vmax=None,
                       alpha=1):
    if vmin is None:
        vmin = np.nanmin(arr)
    if vmax is None:
        vmax = np.nanmax(arr)

    if isinstance(levels, int):
        boundaries = np.linspace(vmin, vmax, levels + 1)
    elif isinstance(levels, np.ndarray):
        boundaries = levels
    elif levels is None:
        # make continuous colors (contourf)
        norm = Normalize(vmin, vmax)
    else:
        raise TypeError(f'levels has wrong type: {type(levels)}. Must be int or np.ndarray.')
    cmap = plt.get_cmap(cmap)

    if levels is not None:
        norm = BoundaryNorm(boundaries, ncolors=256, clip=True)

    colormap = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    colors = colormap.to_rgba(arr)

    nan_flag = np.isnan(arr)
    colors[nan_flag, -1] = 0.
    if alpha != 1.:
        colors[~nan_flag, -1] = alpha
    return colors


@xr.register_dataarray_accessor('ipyvolume')
class Ipyvolume_DataArray_Accessor:
    def __init__(self, xarray_obj):
        warnings.warn('The ipyvolume accessor is highly experimental at this stage!', UserWarning)
        self._obj = xarray_obj
        self._xx = None
        self._yy = None
        self._zz = None

    def _build_meshgrid(self):
        if self._obj.ndim == 2:
            self._xx, self._yy = np.meshgrid(self._obj.x, self._obj.y)
        elif self._obj.ndim == 3:
            self._xx, self._yy = np.meshgrid(self._obj.x, self._obj.x, self._obj.z)
        else:
            raise ValueError('Cannot handle higher dimensions than 3')

    @property
    def xx(self):
        if self._xx is None:
            self._build_meshgrid()
        return self._xx

    @property
    def yy(self):
        if self._yy is None:
            self._build_meshgrid()
        return self._yy

    @property
    def zz(self):
        if self._zz is None:
            self._build_meshgrid()
        return self._zz

    def plot(self, figure=None, z='values', cmap='viridis',
             wireframe: bool = False, surface: bool = True,
             color=None, vmin=None, vmax=None, levels=None,
             alpha=1.0):
        """Surface and wireframe plot"""
        if figure is None:
            fig = ipv.figure()
        else:
            fig = figure
        xx, yy = self.xx, self.yy
        assert xx.shape == self._obj.values.shape

        if z == 'values':
            zval = self._obj.values
        else:
            if self._obj[z].ndim == 0:
                zval = np.ones_like(xx) * self._obj[z].values
            else:
                zval = self._obj[z].values

        if color is None:
            if z != 'values':
                color = _color_from_values(arr=self._obj.values, cmap=cmap, vmin=vmin, vmax=vmax, levels=levels,
                                           alpha=alpha)
            else:
                color = _color_from_values(arr=zval, cmap=cmap, vmin=vmin, vmax=vmax, levels=levels, alpha=alpha)
        else:
            color = color
        if surface:
            surface = ipv.plot_surface(xx, yy, zval, color=color)
            surface.color_map = cmap
            surface.material.transparent = True
            surface.material.shade = True
        if wireframe:
            wireframe = ipv.plot_wireframe(xx, yy, zval, color=color)
            wireframe.color_map = cmap
        return ipv


@xr.register_dataset_accessor('ipyvolume')
class Ipyvolume_Dataset_Accessor:
    def __init__(self, xarray_obj):
        warnings.warn('The ipyvolume accessor is highly experimental at this stage!', UserWarning)
        self._obj = xarray_obj
        self._xx = None
        self._yy = None
        self._zz = None

    def _build_meshgrid(self):
        if self._obj.ndim == 2:
            self._xx, self._yy = np.meshgrid(self._obj.x, self._obj.y)
        elif self._obj.ndim == 3:
            self._xx, self._yy = np.meshgrid(self._obj.x, self._obj.x, self._obj.z)
        else:
            raise ValueError('Cannot handle higher dimensions than 3')

    @property
    def xx(self):
        if self._xx is None:
            self._build_meshgrid()
        return self._xx

    @property
    def yy(self):
        if self._yy is None:
            self._build_meshgrid()
        return self._yy

    @property
    def zz(self):
        if self._zz is None:
            self._build_meshgrid()
        return self._zz

    def quiver(self, x, y, z, u: str, v: str, w: str, figure=None, cmap='viridis',
               vmin=None, vmax=None, levels=None, alpha=1.0):
        _cmap = matplotlib.cm.get_cmap(cmap)
        ndim = self._obj.data_vars[list(self._obj.data_vars.keys())[0]].ndim
        if ndim != 3:
            raise ValueError(f'Quiver only works for 3D data but is {ndim}D')

        if figure is None:
            fig = ipv.figure()
        else:
            fig = figure
        xx, yy, zz = np.meshgrid(self._obj[x], self._obj[y], self._obj[z])
        _u, _v, _w = self._obj[u].values.ravel(), self._obj[v].values.ravel(), self._obj[w].values.ravel()
        vectors = ipv.quiver(xx.ravel(), yy.ravel(), zz.ravel(),
                             _u, _v, _w)
        abs_val = np.sqrt(np.square(_u) + np.square(_v) + np.square(_w))
        vectors.color = _color_from_values(arr=abs_val, cmap=cmap, vmin=vmin, vmax=vmax, levels=levels,
                                           alpha=alpha).ravel()
        vectors.color_map = cmap
        return ipv
