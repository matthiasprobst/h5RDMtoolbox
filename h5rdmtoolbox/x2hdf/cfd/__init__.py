import pathlib
from typing import Union, Dict

import h5py

from .ansys.cfx import CFXCase
from ...conventions.translations import from_yaml, translate_standard_names


def cfx2hdf(cfx_filename: pathlib.Path,
            snt: Union[pathlib.Path, Dict, None] = None,
            verbose: bool = False) -> pathlib.Path:
    """Convert a CFX case into a HDF. This includes only meta data, monitor and user point data
    and no solution field data!

    Parameters
    ----------
    cfx_filename: pathlib.Path
        The filename of the CFX case
    snt: pathlib.Path | Dict | None, optional=None
        Standard Name Translation Dictionary
    verbose: bool, optional=False
        Additional output

    Returns
    -------
    cfx_filename: pathlib.Path
        The generated HDF5 filename of the CFX case
    """
    cfx_case = CFXCase(cfx_filename)
    hdf_filename = cfx_case.hdf.generate(True)
    if snt:
        if isinstance(snt, Dict):
            sntdict = snt
        elif isinstance(snt, (str, pathlib.Path)):
            sntdict = from_yaml(snt)
        else:
            sntdict = snt
        if sntdict:
            with h5py.File(hdf_filename, 'r+') as h5:
                translate_standard_names(h5, sntdict, verbose)
    return hdf_filename
