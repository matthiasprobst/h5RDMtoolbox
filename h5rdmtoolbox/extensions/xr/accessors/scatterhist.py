"""scatter hist accessor

Plots scatter plot with histograms at sides similar to
https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/scatter_hist.html
where most code is taken from
"""

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from ....plotting import build_label_unit_str


@xr.register_dataarray_accessor("scatterhist")
class ScatterHist:
    """Scatter-histogram-plot for xr.DataArrays

    Example:
    --------
    da = xr.DataArray( ... )
    da[:].scatterhist(marker='+', color='k')
    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def __call__(self, *args, **kwargs):
        self.plot(*args, **kwargs)

    def plot(self, **kwargs):
        """Plot a scatter histogram.
        Code taken from https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/scatter_hist.html"""
        ds_x = self._obj[list(self._obj.coords.variables.keys())[kwargs.get('axis', 0)]]
        ds_y = self._obj
        x = ds_x.values
        y = ds_y.data

        # definitions for the axes
        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        spacing = 0.005

        rect_scatter = [left, bottom, width, height]
        rect_histx = [left, bottom + height + spacing, width, 0.2]
        rect_histy = [left + width + spacing, bottom, 0.2, height]

        # start with a rectangular Figure
        fig = kwargs.get('fig', plt.figure(figsize=kwargs.get('figsize', (8, 8))))

        ax_scatter = plt.axes(rect_scatter)
        ax_scatter.tick_params(direction='in', top=True, right=True)
        ax_histx = plt.axes(rect_histx)
        ax_histx.tick_params(direction='in', labelbottom=False)
        ax_histy = plt.axes(rect_histy)
        ax_histy.tick_params(direction='in', labelleft=False)

        # the scatter plot:
        ax_scatter.scatter(x, y,
                           marker=kwargs.pop('marker', None),
                           s=kwargs.pop('s', None),
                           color=kwargs.get('color', 'k'))

        # now determine nice limits by hand:
        bins = kwargs.get('bins', 10)
        xmean = np.nanmean(x)
        dx = np.nanmax(x) - np.nanmin(x)
        xbinwidth = dx / bins
        _xlim = (xmean - dx / 2, xmean + dx / 2)
        ymean = np.nanmean(y)
        dy = np.nanmax(y) - np.nanmin(y)
        ybinwidth = dy / bins
        _ylim = (ymean - dy / 2, ymean + dy / 2)
        ax_scatter.set_xlim(kwargs.get('xlim', _xlim))
        ax_scatter.set_ylim(kwargs.get('ylim', _ylim))

        xunits = ds_x.attrs.get('units', None)
        if 'standard_name' in ds_x.attrs:
            xname = ds_x.standard_name
        elif 'long_name' in ds_x.attrs:
            xname = ds_x.long_name
            ax_scatter.set_xlabel(ds_x.long_name)
        else:
            xname = ds_x.name
        if xunits:
            ax_scatter.set_xlabel(build_label_unit_str(xname, xunits))
        else:
            ax_scatter.set_xlabel(xname)

        yunits = ds_y.attrs.get('units', None)
        if 'standard_name' in ds_y.attrs:
            yname = ds_y.standard_name
        elif 'long_name' in ds_y.attrs:
            yname = ds_y.long_name
            ax_scatter.set_ylabel(ds_y.long_name)
        else:
            yname = ds_y.name
        if yunits:
            ax_scatter.set_ylabel(build_label_unit_str(yname, yunits))
        else:
            ax_scatter.set_ylabel(yname)

        xbins = np.arange(_xlim[0], _xlim[1], xbinwidth)
        ybins = np.arange(_ylim[0], _ylim[1], ybinwidth)
        ax_histx.hist(x, bins=kwargs.get('xbins', xbins),
                      color=kwargs.get('color', 'k'))
        ax_histy.hist(y, bins=kwargs.get('ybins', ybins), orientation='horizontal',
                      color=kwargs.get('color', 'k'))

        ax_histx.set_xlim(ax_scatter.get_xlim())
        ax_histy.set_ylim(ax_scatter.get_ylim())

        return fig
