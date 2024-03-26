"""scatter hist accessor

Plots scatter plot with histograms at sides similar to
https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/scatter_hist.html
where most code is taken from
"""

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from typing import Tuple, Union

from ..plotting import build_label_unit_str


def scatter_hist(x, y, binwidth: Union[float, Tuple[float, float]] = 1.0, **kwargs):
    """Code taken from https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/scatter_hist.html"""
    # definitions for the axes
    left, width = 0.1, 0.65
    bottom, height = 0.1, 0.65
    spacing = 0.005
    density = kwargs.pop('density', True)
    color = kwargs.pop('color', 'k')

    rect_scatter = [left, bottom, width, height]
    rect_histx = [left, bottom + height + spacing, width, 0.2]
    rect_histy = [left + width + spacing, bottom, 0.2, height]

    # start with a rectangular Figure
    plt.figure(figsize=(8, 8))

    ax_scatter = plt.axes(rect_scatter)
    ax_scatter.tick_params(direction='in', top=True, right=True)
    ax_histx = plt.axes(rect_histx)
    ax_histx.tick_params(direction='in', labelbottom=False)
    ax_histy = plt.axes(rect_histy)
    ax_histy.tick_params(direction='in', labelleft=False)

    # the scatter plot:
    ax_scatter.scatter(x, y, color=color, **kwargs)

    # now determine nice limits by hand:
    lim = np.ceil(np.abs([x, y]).max() / binwidth) * binwidth
    ax_scatter.set_xlim((-lim, lim))
    ax_scatter.set_ylim((-lim, lim))

    if isinstance(binwidth, (int, float)):
        xbins = ybins = np.arange(-lim, lim + binwidth, binwidth)
    else:
        xbins = np.arange(-lim, lim + binwidth[0], binwidth[0])
        ybins = np.arange(-lim, lim + binwidth[1], binwidth[1])
    ax_histx.hist(x, bins=xbins, color=color, density=density)
    ax_histy.hist(y, bins=ybins, orientation='horizontal', color=color, density=density)

    # ax_histx.set_xlim(ax_scatter.get_xlim())
    # ax_histy.set_ylim(ax_scatter.get_ylim())
    if density:
        ax_histx.set_ylim([0, 1])
        ax_histy.set_xlim([0, 1])
    else:
        ax_histx.set_ylim([0, None])
        ax_histy.set_xlim([0, None])

    return ax_scatter, ax_histx, ax_histy


@xr.register_dataset_accessor("scatterhist")
class ScatterHist:
    """Scatter-histogram-plot for xr.Dataset objects

    Example:
    --------
    ds = xr.Dataset( ... )
    ds.scatterhist('x', 'y', marker='+', color='k')
    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def __call__(self, x: str, y: str, **kwargs):
        ds_x = self._obj[x]
        ds_y = self._obj[y]
        ax_scatter, ax_histx, ax_histy = scatter_hist(ds_x.values.ravel(), ds_y.values.ravel(), **kwargs)

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
