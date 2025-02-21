import h5py
import numpy as np
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
#
# def get_hdf5_atomic_type_class(dataset):
#     """Returns the HDF5 type class of a given dataset."""
#     type_class = dataset.dtype
#
#     if type_class.kind == 'i':  # Integer
#         return HDF5.H5T_INTEGER
#     elif type_class.kind == 'f':  # Float
#         return HDF5.H5T_FLOAT
#     elif type_class.kind == 'S' or type_class.kind == 'O':  # String
#         return HDF5.H5T_STRING
#     elif type_class.kind == 'b':  # Bitfield (bool in NumPy)
#         return HDF5.H5T_BITFIELD
#     elif type_class.kind == 'u':  # Unsigned Integer
#         return HDF5.H5T_INTEGER
#     elif h5py.check_vlen_dtype(dataset.dtype):  # Variable-length
#         return HDF5.H5T_VLEN
#     return

def _get_endianness(dtype):
    """Returns 'LE' for little-endian and 'BE' for big-endian."""
    if dtype.byteorder == '<' or dtype.byteorder == '|':  # Little-endian or native
        return 'LE'
    elif dtype.byteorder == '>':  # Big-endian
        return 'BE'
    return 'LE'  # Default to little-endian if unknown


def get_datatype(dataset: h5py.Dataset):
    """Maps an HDF5 dataset to its ontology-defined datatype."""
    dtype = dataset.dtype
    np_type = np.dtype(dtype).type  # Get numpy type (e.g., np.float32)

    endianness = _get_endianness(dtype)

    ontology_type = HDF5_DATATYPE_MAP.get((np_type, endianness), None)
    return ontology_type