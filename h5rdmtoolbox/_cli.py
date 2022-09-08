"""collection of command line interfce functions"""

import argparse
import pathlib
import sys
import webbrowser

from h5rdmtoolbox.conventions.translations import from_yaml
from h5rdmtoolbox.x2hdf.cfd import cfx2hdf
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
    parser.add_argument('cfx2hdf', type=str, nargs='?',
                        default=None, help="Enter cfx-to-hdf conversion menu")
    parser.add_argument('-d', '--dump',
                        type=str,
                        required=False,
                        default=None,
                        help='Dump file content.')

    args, unknown = parser.parse_known_args()  # unknown is a list
    if args.standard_name == 'layout' and args.dump is not None:
        # it's not dump because -d must be passed to layout where it is --delete
        _dargs = vars(args)
        unknown.append('--delete')
        unknown.append(_dargs['dump'])
        del _dargs['dump']
        args = argparse.Namespace(**_dargs)

    if args.flexhelp:
        if args.standard_name == 'layout':
            layout('-h')
            exit(0)
        if args.standard_name == 'standard_name':
            standard_name('-h')
            exit(0)
        if args.standard_name == 'cfx2hdf':
            _cfx2hdf('-h')
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

    if args.standard_name == 'cfx2hdf':
        if not unknown:
            unknown = ['-h', ]
        _cfx2hdf(*unknown)
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
        from .conventions.identifier import StandardNameTable
        StandardNameTable.print_registered()
        sys.exit(0)
    else:
        from .conventions.identifier import StandardNameTable
        snt_filename = pathlib.Path(_args.select)
        if snt_filename.exists():
            snt = StandardNameTable.from_yml(_args.select)
        else:
            snt = StandardNameTable.load_registered(_args.select)
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
    parser.add_argument('-c', '--check',
                        type=str,
                        required=False,
                        default=None,
                        help='Filename to run check on.')
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        default=None,
                        help='Filename to run check on. Depreciated. Use -d/--check in instead!')
    parser.add_argument('-r', '--register',
                        type=str,
                        required=False,
                        default=None,
                        help='Register a layout.')
    parser.add_argument('-d', '--delete',
                        type=str,
                        required=False,
                        default=None,
                        help='Delete a registered Layout file.')
    _args = parser.parse_args(args)

    if _args.list:
        from .conventions.layout import H5Layout
        H5Layout.print_registered()
        sys.exit(0)
    else:
        from .conventions.layout import H5Layout
        if _args.file:
            raise DeprecationWarning('Use -c/--check')
        if _args.select and _args.check:
            layout_filename = pathlib.Path(_args.select)
            if layout_filename.exists():
                lay = H5Layout(_args.select)
            else:
                lay = H5Layout.load_registered(_args.select)

            if _args.check is None:
                lay.sdump()
                sys.exit(0)

            print(f' > Checking file with layout "{lay.filename.name}":\n')
            with open_wrapper(_args.check) as h5:
                lay.check(h5, recursive=True, silent=False)
            lay.report()
            sys.exit(0)

        if _args.register:
            lay = H5Layout(pathlib.Path(_args.register))
            lay.register()
            H5Layout.print_registered()
            sys.exit(0)

        if _args.delete:
            filename = H5Layout.find_registered_filename(_args.delete)
            print(f'Deleting {filename}')
            filename.unlink()
            H5Layout.print_registered()
            sys.exit(0)
    parser.print_help(sys.stderr)


def _cfx2hdf(*args):
    """Command line interface method. A folder is expected"""
    import pathlib
    from h5rdmtoolbox.x2hdf.cfd.ansys import AnsysInstallation
    parser = argparse.ArgumentParser(description='PIV uncertainty estimation with CNN')

    # Add the arguments
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        help='CFX file (*.cfx)')
    parser.add_argument('-inst', '--installation_directory',
                        type=str,
                        required=False,
                        default=None,
                        help='Path to installation directory of ansys cfx')
    parser.add_argument('-snt', '--standard-name-translation',
                        type=str,
                        required=False,
                        help='File path to standard name translation. If not set, it will be searched for '
                             'snt.yml in the working directory. To suppress this, set "-ignsnt"')
    parser.add_argument("-ignsnt",
                        "--ignore-snt",
                        default=False,
                        action="store_true",
                        help='Ignore standard name translation files available int the folder')
    parser.add_argument("-v",
                        "--verbose",
                        default=False,
                        action="store_true",
                        help='Additional output')

    args = parser.parse_args(args)

    ansys_inst = AnsysInstallation()
    if args.installation_directory is not None:
        ansys_inst.installation_directory = args.installation_directory

    installation_directory = ansys_inst.installation_directory
    if installation_directory is None:
        raise FileNotFoundError('Ansys installation directory is unknown. Run cfx2hdf -inst INST_DIR')

    if args.file is not None:
        cfx_filename = pathlib.Path(args.file)
        parent = cfx_filename.parent
        # search for snt:
        snt_files = sorted(parent.glob('snt*.yml'))
        if not args.ignore_snt:
            if len(snt_files) > 0:
                snt_dict = from_yaml(snt_files[0])
                hdf_filename = cfx2hdf(cfx_filename, snt_dict, verbose=args.verbose)
            else:
                hdf_filename = cfx2hdf(cfx_filename)
        else:
            hdf_filename = cfx2hdf(cfx_filename)
        print(f'Generated {hdf_filename} from {cfx_filename}')
