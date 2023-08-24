"""h5rdtoolbox repository"""
import atexit
import pathlib
# noinspection PyUnresolvedReferences
import pint_xarray
import shutil
import xarray as xr
from typing import Union

from h5rdmtoolbox._cfg import set_config, get_config, get_ureg

pint_xarray.unit_registry = get_ureg()

from . import conventions
from .conventions.core import Convention
from . import plotting
from . import wrapper
from ._user import UserDir
from ._version import __version__
from .database import file
from . import utils
from .wrapper.core import lower, Lower, File, Group, Dataset
from . import errors

from .wrapper.accessory import register_special_dataset

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'
__author_orcid__ = 'https://orcid.org/0000-0001-8729-0482'

logger = utils.create_tbx_logger('h5rdmtoolbox')

logger.setLevel(get_config()['init_logger_level'])

cv_h5py = conventions.Convention('h5py',
                                 contact=__author_orcid__,
                                 use_scale_offset=False)
cv_h5py.register()

cv_h5tbx = conventions.Convention('h5tbx',
                                  contact=__author_orcid__,
                                  use_scale_offset=True)
cv_h5tbx.register()

use = conventions.core.use

use(get_config()['default_convention'])


class Files:
    """Class to access multiple files at once"""

    def __new__(cls, *args, **kwargs):
        from .database import files
        kwargs['file_instance'] = File
        return files.Files(*args, **kwargs)


def dump(src: Union[str, File, pathlib.Path]) -> None:
    """Call h5.dump() on the provided HDF5 file

    Parameters
    ----------
    src : str, File, pathlib.Path
        the HDF5 file or filename to dump
    """
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dump()
    with File(src) as h5:
        return h5.dump()


def dumps(src: Union[str, File, pathlib.Path]):
    """Call h5.dumps() on the provided HDF5 file"""
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dumps()
    with File(src) as h5:
        return h5.dumps()


atexit_verbose = False


@atexit.register
def clean_temp_data(full: bool = False):
    """cleaning up the tmp directory"""
    from ._user import _user_root_dir

    failed_dirs = []
    failed_dirs_file = UserDir['tmp'] / 'failed.txt'
    if full:
        root_tmp = _user_root_dir / 'tmp'
        if root_tmp.exists():
            try:
                shutil.rmtree(root_tmp)
                root_tmp.mkdir(exist_ok=True, parents=True)
            except PermissionError as e:
                print(f'removing tmp folder "{root_tmp}" failed due to "{e}".')
        return

    for _tmp_session_dir in [UserDir['tmp'], ]:
        if atexit_verbose:
            print(f'cleaning up tmp directory "{_tmp_session_dir}"')
        if _tmp_session_dir.exists():
            try:
                if atexit_verbose:
                    print(f'try deleting tmp in session dir: {_tmp_session_dir}')
                shutil.rmtree(_tmp_session_dir)
            except PermissionError as e:
                if atexit_verbose:
                    print(f'[!] failed deleting tmp session dir: {_tmp_session_dir}')
                failed_dirs.append(UserDir['tmp'])
                if atexit_verbose:
                    print(f'removing tmp folder "{_tmp_session_dir}" failed due to "{e}". Best is you '
                          f'manually delete the directory.')
            finally:
                lines = []
                if failed_dirs_file.exists():
                    with open(failed_dirs_file, 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            try:
                                shutil.rmtree(line.strip())
                            except Exception:
                                if pathlib.Path(line).exists():
                                    failed_dirs.append(line)

                if lines or failed_dirs:
                    with open(failed_dirs_file, 'w') as f:
                        for fd in failed_dirs:
                            f.writelines(f'{fd}\n')
                else:
                    failed_dirs_file.unlink(missing_ok=True)
        else:
            logger.debug(f'No user tmp dir not found: {_tmp_session_dir}')


xr.set_options(display_expand_data=False)

__all__ = ('__version__', '__author__', '__author_orcid__', 'UserDir', 'use',
           'File', 'Files', 'Group', 'Dataset',
           'dump', 'dumps', 'cv_h5py', 'lower', 'Lower',
           'set_config', 'get_config', 'get_ureg',
           'Convention')
