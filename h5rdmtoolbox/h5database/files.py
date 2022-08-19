import pathlib

from ..h5wrapper import open_wrapper


class H5Files:
    """H5File-like interface for multiple HDF Files"""

    def __init__(self, *filenames, h5wrapper=None):
        self._list_of_filenames = [pathlib.Path(f) for f in filenames]
        self._opened_files = {}
        self._h5wrapper = h5wrapper

    def __getitem__(self, item):
        return self._opened_files[item]

    def __enter__(self):
        for filename in self._list_of_filenames:
            try:
                if self._h5wrapper is None:
                    h5file = open_wrapper(filename, mode='r')
                else:
                    h5file = self._h5wrapper(filename, mode='r')
                self._opened_files[filename.stem] = h5file
            except RuntimeError:
                for h5file in self._opened_files.values():
                    h5file.close()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def keys(self):
        """Return all opened filename stems"""
        return self._opened_files.keys()

    def close(self):
        """Close all opened files"""
        for h5file in self._opened_files.values():
            h5file.close()
