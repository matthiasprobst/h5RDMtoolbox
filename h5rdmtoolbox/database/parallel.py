import multiprocessing as mp
import numpy as np
import pathlib
from itertools import chain
from typing import List

from . import lazy
from . import logger

CPU_COUNT = mp.cpu_count()


def _unpack_essential_info(lazy_obj):
    if isinstance(lazy_obj, list):
        return [_unpack_essential_info(obj) for obj in lazy_obj]
    return (lazy_obj.filename, lazy_obj.name)


def _procfind(filenames: List[pathlib.Path], flt, objfilter, rec, ignore_attribute_error):
    """find-caller for a process"""
    if len(filenames) > 1:
        from h5rdmtoolbox.database import Files
        with Files(filenames) as files:
            res = files.find(flt=flt,
                             objfilter=objfilter,
                             rec=rec,
                             ignore_attribute_error=ignore_attribute_error)
        return [_unpack_essential_info(r) for r in res]
    from h5rdmtoolbox.database import File
    return [_unpack_essential_info(r) for r in File(filenames[0]).find(flt=flt,
                                                                       objfilter=objfilter,
                                                                       rec=rec,
                                                                       ignore_attribute_error=ignore_attribute_error)]


def find(filenames, flt, objfilter, rec, ignore_attribute_error, nproc):
    """Call find() on multiple files in parallel"""
    n_filenames = len(filenames)
    if nproc is None:
        nproc = CPU_COUNT
    nproc = min(nproc, CPU_COUNT, n_filenames)
    logger.debug(f'Using {nproc} processes for parallel-find')
    chunk_size = int(np.ceil(n_filenames / nproc))

    chunks = []
    for i in range(nproc):
        chunks.append(filenames[i * chunk_size:chunk_size * (i + 1)])

    chunks = [c for c in chunks if c != []]
    logger.debug(f'chunks: {chunks}')

    with mp.Pool(processes=nproc) as pool:
        results = [pool.apply_async(_procfind, args=(chunk, flt, objfilter, rec, ignore_attribute_error)) for
                   chunk in
                   chunks]
        lazy_objects = [result.get() for result in results]
    return [lazy.lazy(lobj) for lobj in list(chain.from_iterable(lazy_objects))]
