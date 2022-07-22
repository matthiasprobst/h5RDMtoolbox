import logging
import os
import pathlib
import shutil
import time
from os import walk

import h5py
import pandas as pd

from h5rdmtoolbox.h5wrapper import H5File
from . import config
from ..utils import touch_tmp_hdf5_file

logger = logging.getLogger(__package__)


def unique_file_list(list1):
    # initialize a null list
    unique_list = []

    # traverse for all elements
    for x in list1:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    return unique_list


def find_files(rootdir, ext, ignore_if_filename_contains=None):
    """
    Parameters
    ----------
    rootdir: str
        Root folder from which on files are searched
    ext : str
        File extension to search for. Include the dot!
    ignore_if_filename_contains : str, optional=None
        If not None and the passed string is contained in the filename,
        it will not add although extension matches.
    """
    found = list()
    if ignore_if_filename_contains is None:
        for root, directories, filenames in walk(rootdir):
            for filename in filenames:
                if filename.endswith(ext):
                    found.append(os.path.join(root, filename))
    else:
        for root, directories, filenames in walk(rootdir):
            for filename in filenames:
                if filename.endswith(ext):
                    if ignore_if_filename_contains not in os.path.basename(filename):
                        found.append(os.path.join(root, filename))
    return found


def build_repo_toc(repo_dir='', toc_filename=None, wrapperpy_class=None, rec=True):
    """
    builds a table-of-content-file in directory repo_dir.
    Name of file can be controlled via toc_name (without extension!)
    File extension is defined via config['toc_ext']

    rec: bool
        recursive search for hdf files in repo_dir
    """
    repo_dir = pathlib.Path(repo_dir).absolute()
    repo_stem = repo_dir.stem  # = os.path.abspath(repo_dir).split(os.sep)[-1]
    if toc_filename is None:
        toc_filename = repo_dir.joinpath(f'{repo_stem}{config["toc_ext"]}')

    nadded = 0
    if rec:
        all_hdf_files = [f for f in sorted(repo_dir.rglob(f'*{config["hdf5_ext"]}')) if
                         config['toc_ext'] not in f.name]
    else:
        all_hdf_files = [f for f in sorted(repo_dir.glob(f'*{config["hdf5_ext"]}')) if
                         config['toc_ext'] not in f.name]
    ntotal = len(all_hdf_files)

    with h5py.File(toc_filename, 'w') as h5:
        for i, path in enumerate(all_hdf_files):
            if os.path.abspath(path) != os.path.abspath(toc_filename):
                try:
                    if wrapperpy_class:
                        h5[f'e{i:04}'] = h5py.ExternalLink(os.path.abspath(path), '/')
                        nadded += 1
                        # wc_instance = wrapperpy_class(os.path.abspath(path), mode='r')
                        # verification_rate = wc_instance.layout_inspection(silent=True)
                        # if verification_rate == 100.00:
                        #     nadded += 1
                        #     logger.debug(f'adding {os.path.abspath(path)}')
                        #     h5[f'e{i:04}'] = h5py.ExternalLink(os.path.abspath(path), '/')
                        # else:
                        #     accumulate_fail_verification_rate += verification_rate
                        #     logger.debug(f'skipping {os.path.abspath(path)}. Verification rate: {verification_rate}')
                    else:
                        nadded += 1
                        logger.debug(f'adding {os.path.abspath(path)}')
                        h5[f'e{i:04}'] = h5py.ExternalLink(os.path.abspath(path), '/')
                except RuntimeError as e:
                    logger.error(f'Error while scanning files: {e}')
            else:
                ntotal -= 1  # table of content was included in total count, remove now

    return toc_filename


def get_external_filenames_from_h5_file(h5filename):
    with h5py.File(h5filename, 'r') as h5:
        filenames = list()
        for k in h5.keys():
            filenames.append(h5[k].file.filename)
        return filenames


class SingleResult:
    _obj = None

    def __init__(self, filename, wrapperpy_class=None):
        self.filename = filename
        if wrapperpy_class is None:
            self.wrapperpy_class = H5File
        else:
            self.wrapperpy_class = wrapperpy_class

    def __enter__(self):
        self._obj = self.wrapperpy_class(self.filename, mode='r')
        return self._obj

    def __exit__(self, *args):
        self._obj.close()

    def _repr_html_(self) -> None:
        if self.filename:
            with self.wrapperpy_class(self.filename, mode='r') as h5:
                h5.dump()


class H5repo:

    def __len__(self):
        """number of found files"""
        return len(self.filenames)

    def __init__(self, toc, wrapperpy_class=None, rec=True, **kwargs):
        """
        toc : Path
            Path to existing toc-file or folder with hdf files. If folder, a toc
            file is generated, searching recursively for all files with given extension
            provided by parameter ext
        wrapperpy_class : h5wrapper class, optional=None
            A h5wrapper class can be passed. Used when generating the toc file.
        rec: bool, optional=True
            Recursive search from initial folder
        ext : str, optional='.hdf'
            HDF extension to look for in data repository folder structure

        """
        self.elapsed_time = -1  # no search: -1 s
        self.wrapperpy_class = wrapperpy_class

        toc = pathlib.Path(toc)
        if toc.is_dir():
            toc_filename = kwargs.get('toc_filename', None)
            self.toc_filename = build_repo_toc(toc, toc_filename=toc_filename,
                                               wrapperpy_class=wrapperpy_class, rec=rec)
        elif toc.is_file():
            self.toc_filename = toc
        else:
            raise FileExistsError(f'The toc file provided neither exists nor is a folder to build a '
                                  f'toc file from: {toc}')

        # external filenames stored in toc hdf file of this repo class:
        self.filenames = get_external_filenames_from_h5_file(self.toc_filename)

    def __getitem__(self, key):
        if isinstance(key, int):
            return SingleResult(self.filenames[key], wrapperpy_class=self.wrapperpy_class)
        elif isinstance(key, slice):
            return [SingleResult(self.filenames[key], wrapperpy_class=self.wrapperpy_class) for key in
                    range(len(self.filenames))]

    def __repr__(self):
        elapsed_time_ms = int(self.elapsed_time * 1000)
        return f'{self.__class__.__name__} with {len(self.filenames)} result. Filter time: {elapsed_time_ms} ms'

    def _repr_html_(self):
        from IPython.display import display
        data = dict()
        data['File name'] = [os.path.basename(fname) for fname in self.filenames]
        data['Folder path'] = [os.path.dirname(fname) for fname in self.filenames]
        df = pd.DataFrame(data)
        pd.set_option('display.max_colwidth', None)
        return display(df)

    def filter(self, *args):
        """An and filter. Runs through all files of the TOC-HDF file and checks the filter request.
        If a file cannot be found it is deleted from the TOC file"""

        # init a new toc file:
        new_toc_filename = touch_tmp_hdf5_file()
        st = time.perf_counter()

        # run through the current toc file and apply filter requests:
        with h5py.File(self.toc_filename, 'r') as h5:
            filenames = []  # list of HDF files that satisfy the filter criteria
            for d in list(h5.keys()):
                try:
                    _filename = h5[d].file.filename
                    logger.debug(f'Exploring {h5[d].file.filename} for filter request')
                except Exception as e:
                    logger.warning(f'Could not open a file in the reo. '
                                   f'It might be that it was deleted in the meantime: {e}')
                    logger.info(f'Deleting entry with name {d}')
                    del h5[d]
                    continue

                # name of external file:
                lookup_filename = h5[d].file.filename

                # perform all search() methods on that file:
                count_success = 0
                n_success_goal = len(args)
                with h5py.File(lookup_filename, 'r') as q5:
                    for arg in args:
                        if arg.search(q5):  # if search return True, thus was successful (otherwise None is returned)
                            count_success += 1

                if n_success_goal == count_success:
                    filenames.append(lookup_filename)

        dt = time.perf_counter() - st  # in seconds

        with h5py.File(new_toc_filename, 'r+') as h5:
            h5.attrs['elapsed_time'] = dt
            for i, fpath in enumerate(filenames):
                h5[f'q{i:04}'] = h5py.ExternalLink(fpath, '/')

        new_cls = H5repo(new_toc_filename, wrapperpy_class=self.wrapperpy_class)

        new_cls.elapsed_time = dt

        return new_cls

    def preview(self, name, grp, h5type='attribute'):
        """
        returns unique list of value according to name and group.
        currently only for attribute data
        """
        # TODO: name allow should be enough when using kwrds!
        with h5py.File(self.toc_filename, 'r') as h5:
            if h5type == 'attribute':
                attrlist = list()
                for k in h5.keys():
                    v = h5[k][grp].attrs[name]
                    if v not in attrlist:
                        attrlist.append(v)
                res_list = attrlist
            else:
                ds_list = list()
                for k in h5.keys():
                    if h5[k][grp][name].ndim == 0:
                        v = h5[k][grp][name][()]
                    else:
                        v = h5[k][grp][name][:]
                    if v not in ds_list:
                        ds_list.append(v)
                res_list = ds_list
        return res_list

    def sdump(self):
        with h5py.File(self.toc_filename, 'r') as h5:
            grps = list(h5.keys())
            col1 = 'H5GrpName'
            print(f'{col1:10s}\tRelpath (relative to {os.path.abspath(os.path.dirname(self.toc_filename))})')
            for grp in grps:
                print(f'{grp:10s}\t'
                      f'{os.path.relpath(h5[grp].file.filename, os.path.abspath(os.path.dirname(self.toc_filename)))})')

    def list_attribute_values(self, name, group):
        attr_values = []
        with h5py.File(self.toc_filename, 'r') as h5:
            for d in list(h5.keys()):
                attr_value = h5[d][group].attrs.get(name)
                if attr_value is not None:
                    attr_values.append(attr_value)
        return list(dict.fromkeys(attr_values))

    def save_as(self, filename, overwrite=False):
        """saves the toc file at filename"""
        _filename = pathlib.Path(filename)
        if _filename.is_file():
            if overwrite:
                os.remove(_filename)
                src = self.toc_filename
                shutil.move(src, _filename)
                return H5repo(_filename, wrapperpy_class=self.wrapperpy_class)
            else:
                logger.info(f"Note: File was not copied to new location {_filename} "
                            f"as the file already exists with this name "
                            "and overwriting was disabled")
                return None

        src = self.toc_filename

        shutil.copy(src, _filename)
        logger.debug(f'File was moved from {src} to {_filename}.')
        return H5repo(_filename, wrapperpy_class=self.wrapperpy_class)


class H5drepo:

    def __init__(self, tocdomain, endpoint, wrapperpy_class=None):
        self.endpoint = endpoint
        self.wrapperpy_class = wrapperpy_class
        self.tocdomain = tocdomain

    def filter(self):
        raise NotImplementedError('Remote database access not implemented yet')
