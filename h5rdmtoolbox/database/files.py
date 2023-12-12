# import h5py
# import pathlib
# from itertools import chain
# from typing import List, Union, Dict
#
#
# class Files:
#     """File-like interface for multiple HDF Files"""
#
#     def __init__(self, filenames: List[Union[str, pathlib.Path]], file_instance=None):
#         """
#         Parameters
#         ----------
#         filenames: List[Union[str, pathlib.Path]]
#             A list of hdf5 filenames or path to a directory containing hdf files.
#         file_instance: h5py.File
#             The HDF5 file instance
#         """
#         self._opened_files = {}
#
#         if file_instance is None:
#             from .. import File as h5tbxFile
#             file_instance = h5tbxFile
#
#         if isinstance(filenames, (str, pathlib.Path)):
#             filenames = (filenames,)
#
#         self._list_of_filenames = [pathlib.Path(f) for f in filenames]
#         for fname in self._list_of_filenames:
#             if fname.is_dir():
#                 raise ValueError(f'Expecting filenames not directory names but "{fname}" is.')
#
#         self._file_instance = file_instance
#
#     def __getitem__(self, item) -> Union[h5py.Group, List[h5py.Group]]:
#         """If integer, returns item-th root-group. If item is string,
#         a list of objects of that item is returned"""
#         if isinstance(item, int):
#             filename = self.filenames[item]
#             return self._opened_files.get(str(filename), filename)
#
#         if isinstance(item, (tuple, list)):
#             return [self.__getitem__(i) for i in item]
#
#         ret = []
#         for filename in self.filenames:
#             h5 = self._opened_files.get(str(filename), None)
#             if h5:
#                 ret.append(h5[item])
#             else:
#                 with self._file_instance(filename) as h5:
#                     ret.append(h5[item])
#         return ret
#
#     def __enter__(self):
#         for filename in self._list_of_filenames:
#             try:
#                 h5file = self._file_instance(filename, mode='r')
#                 self._opened_files[str(filename)] = h5file
#             except RuntimeError as e:
#                 print(f'RuntimeError: {e}')
#                 for h5file in self._opened_files.values():
#                     h5file.close()
#                 self._opened_files = {}
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._opened_files = {}
#         self.close()
#
#     def __len__(self):
#         return len(self._list_of_filenames)
#
#     def __repr__(self):
#         return f'<{self.__class__.__name__} ({self.__len__()} files)>'
#
#     def __str__(self):
#         return f'<{self.__class__.__name__} ({self.__len__()} files)>'
#
#     @property
#     def filenames(self) -> List[pathlib.Path]:
#         """Return list of filenames"""
#         return self._list_of_filenames
#
#     def find_one(self, flt: Union[Dict, str],
#                  objfilter=None,
#                  rec: bool = True,
#                  ignore_attribute_error: bool = False) -> Union[h5py.Group, h5py.Dataset, None]:
#         """See find_one() in h5file.py
#
#         per_file: bool=True
#             Applies `find_one` to each file. If False, finds the first occurrence in
#             any of the files.
#         """
#         for v in self._opened_files.values():
#             found = v.find_one(flt, objfilter=objfilter, rec=rec,
#                                ignore_attribute_error=ignore_attribute_error)
#             if found:
#                 return found
#
#     def find_one_per_file(self, flt: Union[Dict, str],
#                           objfilter=None,
#                           rec: bool = True,
#                           ignore_attribute_error: bool = False) -> Union[List[Union[h5py.Group, h5py.Dataset]], None]:
#         """Applies `find_one` to each file. If False, finds the first occurrence in
#         any of the files.
#
#         See find_one() in h5file.py
#
#         TODO: This can be parallelized!
#         """
#         founds = []
#         for v in self._opened_files.values():
#             found = v.find_one(flt, objfilter=objfilter, rec=rec,
#                                ignore_attribute_error=ignore_attribute_error)
#             if found:
#                 founds.append(found)
#         return founds
#
#     def find(self, flt: Union[Dict, str], objfilter=None,
#              rec: bool = True, ignore_attribute_error: bool = False):
#         """See find() in h5file.py"""
#         found = []
#         for filename in self._list_of_filenames:
#             opened_file = self._opened_files.get(str(filename), None)
#             if opened_file:
#                 found.append(opened_file.find(flt, objfilter=objfilter, rec=rec,
#                                               ignore_attribute_error=ignore_attribute_error))
#             else:
#                 from .file import File
#                 found.append(File(filename, mode='r').find(flt, objfilter=objfilter, rec=rec,
#                                                            ignore_attribute_error=ignore_attribute_error))
#         return list(chain.from_iterable(found))
#
#     def close(self):
#         """Close all opened files"""
#         for h5file in self._opened_files.values():
#             h5file.close()
#
#     def __del__(self):
#         self.close()
#
