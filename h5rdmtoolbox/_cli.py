"""collection of command line interfce functions"""

import argparse
import pathlib
import sys
import webbrowser

from . import open_wrapper
from ._version import __version__


def main():
    """command line interface function"""

    parser = argparse.ArgumentParser(description='Main h5rdmtoolbox command line interface.',
                                     add_help=False)
    parser.add_argument('-h', '--help', dest='flexhelp', default=False,
                        action='store_true',
                        help="Show this help message and exit.")
    parser.add_argument('-V', '--version',
                        action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-D', dest='documentation',
                        action='store_true',
                        help="Opens documentation in browser")

    parser.add_argument('standard_name', type=str, nargs='?',
                        default=None, help="Enter standard_name commands")
    parser.add_argument('layout', type=str, nargs='?',
                        default=None, help="Enter layout commands")
    parser.add_argument('-d', '--dump',
                        type=str,
                        required=False,
                        default=None,
                        help='Dump file content.')

    args, unknown = parser.parse_known_args()

    if args.flexhelp:
        if args.standard_name == 'layout':
            layout('-h')
            exit(0)
        if args.standard_name == 'standard_name':
            standard_name('-h')
            exit(0)
        parser.print_help(sys.stderr)
        sys.exit(0)

    if args.standard_name == 'layout':
        if not unknown:
            unknown = ['-h', ]
        layout(*unknown)
        sys.exit(0)

    if args.standard_name == 'standard_name':
        if not unknown:
            unknown = ['-h', ]
        standard_name(*unknown)
        sys.exit(0)

    if args.documentation:
        webbrowser.open('https://matthiasprobst.github.io/h5RDMtoolbox/')
        sys.exit(0)

    if args.dump:
        with open_wrapper(args.dump) as h5:
            h5.sdump()
        sys.exit()

    parser.print_help(sys.stderr)


def standard_name(*args):
    """Run standard_name cli"""
    parser = argparse.ArgumentParser(description=f'Standard names')
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help='List all registered standard name tables.')
    parser.add_argument('-s', '--select',
                        type=str,
                        required=False,
                        default=None,
                        help='Registered standard name or filename of a standard table.')
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        default=None,
                        help='Filename to run check on.')
    _args = parser.parse_args(args)

    if _args.list:
        from .conventions.identifier import StandardizedNameTable
        StandardizedNameTable.print_registered()
        sys.exit(0)
    else:
        from .conventions.identifier import StandardizedNameTable
        snt_filename = pathlib.Path(_args.select)
        if snt_filename.exists():
            snt = StandardizedNameTable.from_yml(_args.select)
        else:
            snt = StandardizedNameTable.load_registered(_args.select)
        print(f'Checking file "{_args.file}" with layout filename "{snt}"')
        with open_wrapper(_args.file) as h5:
            snt.check_grp(h5, recursive=True, raise_error=False)
        sys.exit()
    parser.print_help(sys.stderr)


def layout(*args):
    """Run layout cli"""
    parser = argparse.ArgumentParser(description=f'HDF layout')
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help='List all registered layouts.')
    parser.add_argument('-s', '--select',
                        type=str,
                        required=False,
                        default=None,
                        help='Registered layout name or filename of a layout.')
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        default=None,
                        help='Filename to run check on.')
    _args = parser.parse_args(args)

    if _args.list:
        from .conventions.layout import H5Layout
        H5Layout.print_registered()
        sys.exit(0)
    else:
        from .conventions.layout import H5Layout
        layout_filename = pathlib.Path(_args.select)
        if layout_filename.exists():
            layout = H5Layout(_args.select)
        else:
            layout = H5Layout.load_registered(_args.select)
        if _args.file is None:
            layout.sdump()
            sys.exit(0)
        print(f' > Checking file "{_args.file}" with layout filename "{layout.filename.name}":\n')
        with open_wrapper(_args.file) as h5:
            layout.check(h5, recursive=True, silent=False)
        sys.exit(0)
    parser.print_help(sys.stderr)
