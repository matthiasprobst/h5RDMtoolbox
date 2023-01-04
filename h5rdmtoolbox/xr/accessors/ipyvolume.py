import matplotlib.cm
import numpy as np
import warnings
import xarray as xr

import ipyvolume as ipv


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

    def plot(self, figure=None, cmap='viridis', wireframe: bool = False, surface: bool = True):
        """Surface and wireframe plot"""
        _cmap = matplotlib.cm.get_cmap(cmap)
        if figure is None:
            fig = ipv.figure()
        else:
            fig = figure
        xx, yy = self.xx, self.yy
        assert xx.shape == self._obj.values.shape
        if surface:
            surface = ipv.plot_surface(yy, xx, self._obj.values, color="red")
            colors = _cmap(self._obj.values)
            surface.color = colors.ravel()
            surface.color_map = cmap
        if wireframe:
            wireframe = ipv.plot_wireframe(yy, xx, self._obj.values, color="red")
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

    def quiver(self, x, y, z, u: str, v: str, w: str, figure=None, cmap='viridis'):
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
        colors = _cmap(abs_val)
        vectors.color = colors.ravel()
        vectors.color_map = cmap
        return ipv
