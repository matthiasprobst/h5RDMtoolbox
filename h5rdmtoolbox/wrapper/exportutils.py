"""
export utilities
"""
import os.path
import pathlib
from typing import Union

import h5py
import numpy as np
import pandas as pd

IGNORE_ATTRS = ('REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST')


def attribute_to_txt(attrs, filename, mode: str = 'w'):
    if len(attrs) > 0:
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True)
        with open(filename, mode) as f:
            for k, v in attrs.items():
                if k not in IGNORE_ATTRS and not k.startswith('__'):
                    f.write(f'{k}: {v}\n')


def dataset_to_txt(ds: h5py.Dataset, filename: Union[None, str, pathlib.Path] = None,
                   overwrite: bool = False):
    """Write a HDF5 dataset to a txt-file"""
    if filename is None:
        filename = pathlib.Path.cwd() / os.path.basename(ds.name)
    else:
        filename = pathlib.Path(filename)
    if filename.exists():
        if overwrite is False:
            raise FileExistsError(f'File {filename} exists and overwrite is set to False.')
    if not filename.parent.exists():
        filename.parent.mkdir(parents=True)
    print(f'ds: {filename}')
    dsbasename = f'{os.path.basename(ds.name)} [{ds.attrs["units"]}]'
    with open(filename, 'w') as f:
        f.write(f'# h5type: dataset')
        f.write(f'\n# filename: {ds.file.filename}')
        f.write(f'\n# name: {ds.name}')
        f.write(f'\n# shape: {ds.shape}')
        f.write(f'\n# attributes:')
        for ak, av in ds.attrs.items():
            if ak not in IGNORE_ATTRS:
                if isinstance(av, (int, float, str)):
                    f.write(f'\n# {ak}:{av}')
        f.write(f'\n#----:\n')
    if ds.ndim < 1:
        pd.DataFrame({dsbasename: ds.values[()].ravel()}).to_csv(filename, header=dsbasename, index=False, mode='a')
    else:
        if len(ds.dims) > 0:
            coords = {}
            data = {}
            for dim in ds.dims:
                for idim in range(len(dim)):
                    dim_ds = dim[idim]
                    dimname = os.path.basename(dim_ds.name)
                    dimname += f' [{dim_ds.attrs["units"]}]'
                    dimdata = dim[idim]
                    if dimdata.ndim != 1:
                        raise ValueError(f'At this stage I can only handle 1D data')
                    coords[dimname] = dimdata
            if ds.ndim > 1:
                grid_coords = np.meshgrid(*[c[()] for c in coords.values()])
                for k, gc in zip(coords.keys(), grid_coords):
                    data[k] = gc.ravel()
            else:
                for k, v in coords.items():
                    data[k] = v
            data[dsbasename] = ds.values[()].ravel()
            pd.DataFrame(data).to_csv(filename, header=dsbasename, index=False, mode='a')
        else:
            pd.DataFrame({dsbasename: ds.values[()].flatten()}).to_csv(filename, header=dsbasename,
                                                                       index=False, mode='a')


def _visitor(name, node):
    if isinstance(node, h5py.Group):
        hdf_to_txt(node, recursive=False)


class _Visitor:
    def __init__(self, rootfolder: pathlib.Path, recursive: bool,
                 overwrite: bool):
        self.rootfolder = rootfolder
        self.recursive = recursive
        self.overwrite = overwrite

        if self.rootfolder is None:
            self.rootfolder = pathlib.Path.cwd()

    def __call__(self, name, obj):
        if isinstance(obj, h5py.Group):
            target_directory = self.rootfolder / pathlib.Path(obj.file.filename).name / obj.name[1:]
        else:
            target_directory = self.rootfolder / pathlib.Path(obj.file.filename).name / obj.parent.name[1:]

        print(target_directory)

        if not target_directory.exists():
            target_directory.mkdir(parents=True)
        attribute_to_txt(obj.attrs, target_directory / 'attributes.txt', mode='w')

        if isinstance(obj, h5py.Dataset):
            if 'CLASS' not in obj.attrs.keys():
                dataset_to_txt(obj,
                               filename=target_directory / f'{os.path.basename(obj.name)}.txt',
                               overwrite=self.overwrite)
        # for obj in obj.values():
        #     if isinstance(obj, h5py.Group):
        #         grp_folder = target_directory / obj.name[1:]
        #         if not grp_folder.exists():
        #             grp_folder.mkdir(parents=True)
        #         attribute_to_txt(obj.attrs, grp_folder / 'attributes.txt', mode='w')
        # for obj in obj.values():
        #     if obj.parent.name != '/':
        #         target_directory / obj.parent.name
        #     if isinstance(obj, h5py.Dataset):
        #         if 'CLASS' not in obj.attrs.keys():
        #             dataset_to_txt(obj,
        #                            filename=target_directory / f'{os.path.basename(obj.name)}.txt',
        #                            overwrite=self.overwrite)

def grp_to_txt(h5: h5py.Group, recursive: bool = True, target_directory: Union[str, pathlib.Path] = None,
               overwrite: bool = False):
    """Export a group (recursively) to text files organized in folders"""
    if not isinstance(h5, h5py.Group):
        raise TypeError(f'Expected type h5py.Group but got {type(h5)}')
    if target_directory is None:
        target_directory = pathlib.Path.cwd()
    target_directory = pathlib.Path(target_directory)

    filename = pathlib.Path(h5.file.filename)

    target_directory = target_directory / filename.name / h5.name[1:]
    print(target_directory)

    if not target_directory.exists():
        target_directory.mkdir(parents=True)

    attribute_to_txt(h5.attrs, target_directory / 'attributes.txt', mode='w')
    for obj in h5.values():
        if isinstance(obj, h5py.Group):
            grp_folder = target_directory / obj.name[1:]
            if not grp_folder.exists():
                grp_folder.mkdir(parents=True)
            attribute_to_txt(obj.attrs, grp_folder / 'attributes.txt', mode='w')
    for obj in h5.values():
        if obj.parent.name != '/':
            target_directory / obj.parent.name
        if isinstance(obj, h5py.Dataset):
            if 'CLASS' not in obj.attrs.keys():
                dataset_to_txt(obj,
                               filename=target_directory / f'{os.path.basename(obj.name)}.txt',
                               overwrite=overwrite)


def hdf_to_txt(h5: h5py.Group, recursive: bool = True, target_directory: Union[str, pathlib.Path] = None,
               overwrite: bool = False):
    """Export a group (recursively) to text files organized in folders"""
    if target_directory is None:
        target_directory = pathlib.Path.cwd()
    # target_directory = pathlib.Path(target_directory) / pathlib.Path(h5.file.filename).name

    visitor = _Visitor(target_directory, recursive, overwrite)
    h5.visititems(visitor)
    # for obj in h5.values():
    #     if isinstance(obj, h5py.Dataset):
    #         if 'CLASS' not in obj.attrs.keys():
    #             dataset_to_txt(obj,
    #                            filename=target_directory / obj.name[1:],
    #                            overwrite=overwrite)
    #     else:
    #         if recursive:
    #             grp_to_txt(obj, recursive=recursive, overwrite=overwrite)
