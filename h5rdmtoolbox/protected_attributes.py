"""protected attributes are used in HDF or xarray attributes and have a special meaning.
Those are always uppercase!"""

HDF_SRC_FILENAME = 'HDF_SRC_FILENAME'
COORDINATES = 'COORDINATES'

h5py = ('CLASS', 'NAME', 'DIMENSION_LIST', 'REFERENCE_LIST')

h5rdmtoolbox = tuple([*h5py, HDF_SRC_FILENAME, COORDINATES])
