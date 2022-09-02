"""h5rdtoolbox repository"""

import atexit
import shutil

from . import conventions
from ._user import user_dirs
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

    parser.add_argument('-l', '--layout-file',
                        type=str,
                        required=False,
                        default=None,
                        help='Layout file name or registered name.')
    parser.add_argument('-n', '--names',
                        type=str,
                        nargs='?',
                        default=None,
                        help='Run standard name check on all datasets in the file.')
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        default=None,
                        help='Filename to run check on.')
    parser.add_argument('-d', '--dump',
                        action='store_true',
                        default=False,
                        help='Dumps the content to screen.')
    parser.add_argument('-list', '--list-registered',
                        type=str,
                        required=False,
                        default=None,
                        help='List registered files. Either pass "layout" or "names" or "standard_names".')

    args = parser.parse_args()

    if args.list_registered:
        if args.list_registered.lower() in ('layout', 'layouts'):
            from .conventions.layout import H5Layout
            H5Layout.print_registered()
        if args.list_registered.lower() in ('names', 'name', 'standard_names', 'standard_name'):
            from .conventions.identifier import StandardizedNameTable
            StandardizedNameTable.print_registered()
        return

    import pathlib
    if args.layout_file:
        from .conventions.layout import H5Layout

        layout_filename = pathlib.Path(args.layout_file)
        if layout_filename.exists():
            layout = H5Layout(args.layout_file)
        else:
            layout = H5Layout.load_registered(args.layout_file)

        with open_wrapper(args.file) as h5:
            layout.check(h5, recursive=True, silent=False)
    if args.names:
        print(args.names)
        from .conventions.identifier import StandardizedNameTable

        snt_filename = pathlib.Path(args.names)
        if snt_filename.exists():
            snt = StandardizedNameTable(args.names)
        else:
            snt = StandardizedNameTable.load_registered(args.names)
        snt.check_file(args.file, recursive=True, raise_error=False)


@atexit.register
def clean_temp_data():
    """cleaning up the tmp directory"""
    from ._user import _root_tmp_dir
    failed_dirs = []
    failed_dirs_file = _root_tmp_dir / 'failed.txt'
    if user_dirs['tmp'].exists():
        try:
            shutil.rmtree(user_dirs['tmp'])
        except RuntimeError as e:
            failed_dirs.append(user_dirs['tmp'])
            print(f'removing tmp folder "{user_dirs["tmp"]}" failed due to "{e}". Best is you '
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

__all__ = ['tutorial', '__version__', '__author__', 'user_dirs', 'conventions', 'H5File', 'H5Flow', 'H5PIV',
           'open_wrapper',
           'generate_temporary_filename', 'generate_temporary_directory']
