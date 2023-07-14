import h5py
import pathlib
from typing import Dict, Union

from .._logger import logger


def update_datasets(group_or_filename: Union[h5py.Group, str, pathlib.Path],
                    translation_dict: Dict,
                    rec: bool = True) -> None:
    """Walk through file and assign standard names to datasets with names indicated in
    the dictionary `translation_dict`

    Parameters
    ----------
    group_or_filename: Union[h5py.Group, str, pathlib.Path]
        The source in which to search for datasets and assign standard names to.
        If a string or pathlib.Path is passed, it is assumed to be an HDF5 filename.
    translation_dict: Dict
        Dictionary with keys being the dataset names and values the standard names
    rec: bool
        If True, recursively search for datasets

    Returns
    -------
    None

    Examples
    --------
    >>> # Assign "air_temperature" to all datasets with name "temperature":
    >>> translation_dict = {'temperature': 'air_temperature'}
    >>> update_datasets('myfile.hdf', translation_dict)
    """
    if isinstance(group_or_filename, (str, pathlib.Path)):
        with h5py.File(group_or_filename, 'r+') as h5:
            return update_datasets(h5['/'], translation_dict, rec=rec)

    def _assign(ds, sn):
        ds.attrs['standard_name'] = sn
        logger.debug(f'Added standard name "{sn}" to dataset "{ds.name}"')

    def sn_update(name: str, node):
        """function called when visiting HDF objects"""
        if isinstance(node, h5py.Dataset):
            if name in translation_dict:
                sn = translation_dict[name.strip('/')]
            elif name.rsplit('/', 1)[-1] in translation_dict:
                sn = translation_dict[name.rsplit('/', 1)[-1]]
            else:
                return
            _assign(node, sn)

    h5grp = group_or_filename
    if rec:
        return h5grp.visititems(sn_update)
    for key, obj in h5grp.items():
        sn_update(key, obj)
