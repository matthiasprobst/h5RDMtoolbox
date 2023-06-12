"""plotting module
Matplotlib labels are manipulated to set the units representation correctly. See build_label_unit_str
"""

import matplotlib.projections as proj
import matplotlib.pyplot as plt
import re
# xarray does not allow to change the unit representation in axis labels. The following is a workaround:
import warnings

from . import config

__XARRAY_UNITS_PATTERN__ = r"(.*?)\[([^\[\]]*?)\]$"
__AV_UNIT_FORMATS__ = ('/', '()', '[]', '//', 'in')


def decode_label(label: str) -> (str, str):
    """Decodes the label into a name and a unit string. For this,
    the last occurrence of [<unit>] is searched. No opening or
    closing square brackets are allowed in the label.

    ..note: This function assumes that the units are written as [<unit>] at
        the end of the label. If this is not the case, the function will fail
        or return wrong results.

    Parameters
    ----------
    label: str
        label to be decoded, e.g. velocity [m/s]

    Returns
    -------
    name: str
        name of the label, e.g. velocity
    unit_string: str
        unit string, e.g. m/s
    """
    try:
        match = re.search(__XARRAY_UNITS_PATTERN__, label)
        return match.group(1), match.group(2)
    except RuntimeError as e:
        raise RuntimeError(f'Could not parse label {label} with pattern {__XARRAY_UNITS_PATTERN__}. Orig. err: {e}')


def build_label_unit_str(name: str, units: str,
                         units_format: str = None) -> str:
    """generates the label string from a name and a units based on the units format"""
    if units_format is None:
        units_format = config.xarray_unit_repr_in_plots
    units = units.replace("**", "^")
    if units_format == 'in':
        return f'{name} in ${units}$'
    if units_format == '/':
        return f'{name} / ${units}$'
    if units_format in ('[', ']', '[]'):
        return f'{name} [${units}$]'
    if units_format in ('(', ')', '()'):
        return f'{name} (${units}$)'


class XarrayLabelManipulation(plt.Axes):
    """Label manipulation axis class"""

    @staticmethod
    def _adjust_units_label(label, units_format=None):
        if units_format is None:
            units_format = config.xarray_unit_repr_in_plots

        if units_format not in __AV_UNIT_FORMATS__:
            raise ValueError(f'Unknown units format {units_format}.')

        if label:
            if not label[-1] == ']':
                return label.replace('**', '^')

            try:
                name, units_string = decode_label(label)
            except RuntimeError as e:
                warnings.warn(f'Could not change label due to {e}. Please open an issue for this and tell '
                              'the developers about it.', UserWarning)
                return label

            if units_format == '[':
                if units_string in ('', ' ', None, 'dimensionless'):
                    _raw_unit = '-'
                else:
                    _raw_unit = f"{units_string.replace('**', '^')}"

                return f"{name} [{_raw_unit.replace('**', '^')}]"

            if units_string[1:-1] in ('', ' ', 'dimensionless', None):
                return build_label_unit_str(name, '-', units_format)

            return build_label_unit_str(name, units_string, units_format)
        return label

    def set_xlabel(self, xlabel, *args, **kwargs):
        """set the (adjusted) xlabel"""
        super().set_xlabel(self._adjust_units_label(xlabel), *args, **kwargs)

    def set_ylabel(self, ylabel, *args, **kwargs):
        """set the (adjusted) ylabel"""
        super().set_ylabel(self._adjust_units_label(ylabel), *args, **kwargs)


# register the axis class
proj.register_projection(XarrayLabelManipulation)
