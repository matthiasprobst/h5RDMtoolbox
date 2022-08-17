import pathlib

from .ansys.cfx import CFXCase


def cfx2hdf(cfx_filename: pathlib.Path):
    cfx_case = CFXCase(cfx_filename)
    return cfx_case.hdf.generate(True)
