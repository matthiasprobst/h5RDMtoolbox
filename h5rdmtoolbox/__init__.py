"""h5rdtoolbox repository"""

import atexit
import shutil

from . import conventions
from ._user import user_data_dir, user_tmp_dir
from ._version import __version__
from .h5wrapper import H5File, H5Flow, H5PIV, open_wrapper
from .utils import generate_temporary_filename, generate_temporary_directory

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'


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


def _cli():
    """command line interface function"""
    import argparse

    parser = argparse.ArgumentParser(description='Main h5rdmtoolbox command line interface.')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-D', '--documentation', type=bool, nargs='?', default=False,
                        help='Opens the documentation in the browser')
    args = parser.parse_args()

    if not args.documentation:
        import webbrowser
        webbrowser.open('https://matthiasprobst.github.io/h5RDMtoolbox/')


def check():
    """Run file check"""
    import argparse
    parser = argparse.ArgumentParser(description=f'h5rdmtoolbox ({__version__})\nLayout check of an HDF5')
    parser.add_argument("filename", help="Filename to run check on.",
                        type=str)

    parser.add_argument('-l', '--layout',
                        type=bool,
                        nargs='?',
                        default=False,
                        help='Run layout check.')
    parser.add_argument('-n', '--names',
                        type=bool,
                        nargs='?',
                        default=False,
                        help='Run name check.')
    # parser.add_argument('-f', '--file',
    #                     type=str,
    #                     required=False,
    #                     default=None,
    #                     help='HDF5 file name.')
    parser.add_argument('-d', '--dump',
                        action='store_true',
                        default=False,
                        help='Dumps the content to screen.')

    args = parser.parse_args()
    print(args)
    if not args.layout and not args.names:
        with open_wrapper(args.filename) as h5:
            if args.dump:
                h5.sdump()
            else:
                h5.check(silent=False)


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


from . import tutorial

__all__ = ['tutorial', '__version__', '__author__', 'user_data_dir', 'conventions', 'H5File', 'H5Flow', 'H5PIV',
           'open_wrapper',
           'generate_temporary_filename', 'generate_temporary_directory']
