from pint import Unit

time_dimensionality = Unit('s').dimensionality
length_dimensionality = Unit('m').dimensionality

try:
    import vtk
except ImportError:
    ImportError('Package vtk not installed. Either install it '
                'separately or install the repository with pip install h5RDMtolbox [piv]')


def is_time(unit):
    """
    Returns true if unit is a time unit, e.g. 'ms' or 's'
    """
    if unit == 's':
        return True
    else:
        return unit.dimensionality == time_dimensionality


def is_length(unit):
    """
    Returns true if unit is a time unit, e.g. 'ms' or 's'
    """
    if unit == 'm':
        return True
    else:
        return unit.dimensionality == length_dimensionality
