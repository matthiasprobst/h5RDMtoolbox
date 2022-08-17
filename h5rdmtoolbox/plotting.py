# xarray does not allow to change the unit representation in axis labels. The following is a work around:
import matplotlib.projections as proj
import matplotlib.pyplot as plt

from .. import config


class XarrayLabelManipulation(plt.Axes):
    def _adjust_units_label(self, label, units_format=config.xarray_unit_repr_in_plots):
        # other formats: '(', '[', '/', 'in'
        if label:
            if not label[-1] == ']':
                return label
            if units_format == '[':
                return label
            idx0 = label.rfind('[', 1)
            units_string = label[idx0:]
            if units_format == 'in':
                return label.replace(units_string, f' in {units_string[1:-1]}')
            if units_format == '/':
                return label.replace(units_string, f' / {units_string[1:-1]}')
            if units_format == '(in)':
                return label.replace(units_string, f' ({units_string[1:-1]})')

    def set_xlabel(self, xlabel, *args, **kwargs):
        super().set_xlabel(self._adjust_units_label(xlabel), *args, **kwargs)

    def set_ylabel(self, ylabel, *args, **kwargs):
        super().set_ylabel(self._adjust_units_label(ylabel), *args, **kwargs)


proj.register_projection(XarrayLabelManipulation)
