import pathlib

import h5rdmtoolbox as h5tbx
from .filedb import FileDB, FilesDB
from .objdb import ObjDB


def find(source, *args, **kwargs):
    if isinstance(source, (str, pathlib.Path)):
        with h5tbx.File(source, mode='r') as h5:
            return find(h5, *args, **kwargs)
    elif isinstance(source, (list, tuple)):
        raise NotImplementedError('find does not support multiple sources')
    else:
        return ObjDB(source).find(*args, **kwargs)


__all__ = ['ObjDB', 'FileDB', 'FilesDB', 'find']
