"""module for external HDF5 objects"""""

import h5py

from .. import File


class ExternalLink(h5py.ExternalLink):
    """External Link wrapper class"""

    def __init__(self, filename, path):
        super().__init__(filename, path)
        self._file = None

    def __enter__(self):
        self._file = File(self.filename)
        return self._file[self.path]

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()
