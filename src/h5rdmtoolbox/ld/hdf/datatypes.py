import sys

import h5py
import numpy as np
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5

# Mapping HDF5 numpy datatypes to ontology types
HDF5_DATATYPE_MAP = {
    (np.float32, 'LE'): HDF5.H5T_IEEE_F32LE,
    (np.float32, 'BE'): HDF5.H5T_IEEE_F32BE,
    (np.float64, 'LE'): HDF5.H5T_IEEE_F64LE,
    (np.float64, 'BE'): HDF5.H5T_IEEE_F64BE,
    (np.int8, 'LE'): HDF5.H5T_INTEL_I8,
    (np.int8, 'BE'): HDF5.H5T_MIPS_I8,
    (np.int16, 'LE'): HDF5.H5T_INTEL_I16,
    (np.int16, 'BE'): HDF5.H5T_MIPS_I16,
    (np.int32, 'LE'): HDF5.H5T_INTEL_I32,
    (np.int32, 'BE'): HDF5.H5T_MIPS_I32,
    (np.int64, 'LE'): HDF5.H5T_INTEL_I64,
    (np.int64, 'BE'): HDF5.H5T_MIPS_I64,
    (np.uint8, 'LE'): HDF5.H5T_INTEL_U8,
    (np.uint8, 'BE'): HDF5.H5T_MIPS_U8,
    (np.uint16, 'LE'): HDF5.H5T_INTEL_U16,
    (np.uint16, 'BE'): HDF5.H5T_MIPS_U16,
    (np.uint32, 'LE'): HDF5.H5T_INTEL_U32,
    (np.uint32, 'BE'): HDF5.H5T_MIPS_U32,
    (np.uint64, 'LE'): HDF5.H5T_INTEL_U64,
    (np.uint64, 'BE'): HDF5.H5T_MIPS_U64,
}
def _get_endianness(dtype):
    """Returns 'LE' for little-endian and 'BE' for big-endian."""
    if dtype.byteorder == '<' or dtype.byteorder == '|':  # Little-endian or native
        return 'LE'
    elif dtype.byteorder == '>':  # Big-endian
        return 'BE'
    return 'LE' if sys.byteorder == 'little' else 'BE'


def get_datatype(dataset: h5py.Dataset) -> rdflib.URIRef:
    """Maps an HDF5 dataset to its ontology-defined datatype."""
    dtype = dataset.dtype
    np_type = np.dtype(dtype).type  # Get numpy type (e.g., np.float32)

    endianness = _get_endianness(dtype)

    return HDF5_DATATYPE_MAP.get((np_type, endianness), None)
