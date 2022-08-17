"""h5rdtoolbox repository"""

import atexit
import pathlib
import shutil

from . import conventions
from . import tutorial
from ._user import user_data_dir, user_tmp_dir
from ._version import __version__
from .h5wrapper import H5File, H5Flow, H5PIV, open_wrapper
from .utils import generate_temporary_filename, generate_temporary_directory

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'
# from .convention.time import datetime_str

__all__ = ['__version__', '__author__', 'user_data_dir', 'conventions', 'H5File', 'H5Flow', 'H5PIV', 'open_wrapper',
           'generate_temporary_filename', 'generate_temporary_directory', 'tutorial']


def set_loglevel(level):
    """setting logging level of all modules"""
    from .x2hdf import set_loglevel as x2hdf_set_loglevel
    from .h5wrapper import set_loglevel as h5wrapper_set_loglevel
    from .h5database import set_loglevel as h5database_set_loglevel
    from .conventions import set_loglevel as conventions_set_loglevel
    x2hdf_set_loglevel(level)
    h5wrapper_set_loglevel(level)
    h5database_set_loglevel(level)
    conventions_set_loglevel(level)


def check():
    """Run file check"""
    import argparse
    parser = argparse.ArgumentParser(description='PIV uncertainty estimation with CNN')
    parser.add_argument("filename", help="Filename to run check on.",
                        type=str)
    # parser.add_argument('-l', '--layout',
    #                     type=bool,
    #                     nargs='?',
    #                     default=False,
    #                     help='Run layout check.')
    # parser.add_argument('-n', '--names',
    #                     type=bool,
    #                     nargs='?',
    #                     default=False,
    #                     help='Run name check.')
    parser.add_argument('-d', '--dump',
                        type=bool,
                        nargs='?',
                        default=False,
                        help='Dumps the content to screen.')

    args = parser.parse_args()

    if not args.layout and not args.names:
        with open_wrapper(args.filename) as h5:
            h5.check(silent=False)
            if args.dump is None:
                h5.sdump()


@atexit.register
def clean_temp_data():
    """cleaning up the tmp directory"""
    from ._user import _root_tmp_dir
    failed_dirs = []
    failed_dirs_file = _root_tmp_dir / 'failed.txt'
    if user_tmp_dir.exists():
        try:
            shutil.rmtree(user_tmp_dir)
        except RuntimeError as e:
            failed_dirs.append(user_tmp_dir)
            print(f'removing tmp folder "{user_tmp_dir}" failed due to "{e}". Best is you '
                  f'manually delete the directory.')
        finally:
            lines = []
            if failed_dirs_file.exists():
                with open(failed_dirs_file, 'r') as f:
                    lines = f.readlines()
                    for l in lines:
                        try:
                            shutil.rmtree(l)
                        except RuntimeError:
                            failed_dirs.append(l)

            if lines or failed_dirs:
                with open(failed_dirs_file, 'w') as f:
                    for fd in failed_dirs:
                        f.writelines(f'{fd}\n')
            else:
                failed_dirs_file.unlink(missing_ok=True)
