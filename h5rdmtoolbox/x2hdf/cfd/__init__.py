import pathlib
from typing import Union, Dict

import h5py

from .ansys.cfx import CFXCase
from ...conventions import StandardNameTable, StandardNameTableTranslation

def cfx2hdf(cfx_filename: pathlib.Path,
            sntt: Union[pathlib.Path, StandardNameTableTranslation, None] = None,
            verbose: bool = False) -> pathlib.Path:
    """Convert a CFX case into a HDF. This includes only meta data, monitor and user point data
    and no solution field data!

    Parameters
    ----------
    cfx_filename: pathlib.Path
        The filename of the CFX case
    sntt: pathlib.Path | Dict | None, optional=None
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
    if sntt:
        if isinstance(sntt, StandardNameTableTranslation):
            sntt = sntt
        elif isinstance(sntt, (str, pathlib.Path)):
            sntt = StandardNameTableTranslation.from_yaml(sntt)
        else:
            sntt = sntt
        if sntt:
            with h5py.File(hdf_filename, 'r+') as h5:
                sntt.translate_group(h5, verbose)
    return hdf_filename
