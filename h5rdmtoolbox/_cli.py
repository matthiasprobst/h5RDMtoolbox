"""collection of command line interfce functions"""

import argparse
import sys
import webbrowser
from pprint import pprint

import h5py

from ._version import __version__


def main():
    parser = argparse.ArgumentParser(description='test group')
    parser.add_argument('-V', '--version',
                        action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-D', dest='documentation',
                        action='store_true',
                        help="Opens documentation in browser")
    subparsers = parser.add_subparsers(help='sub-commands help')

    # LAYOUT
    sp_layout = subparsers.add_parser('layout', help='layout menu')
    sp_layout.set_defaults(cmd='layout')
    sp_layout.add_argument('-l', '--list',
                           action='store_true',
                           default=False,
                           help='List all registered layouts.')
    sp_layout.add_argument('-s', '--select',
                           type=str,
                           required=False,
                           default=None,
                           help='Registered layout name or filename of a layout.')
    sp_layout.add_argument('-c', '--check',
                           type=str,
                           required=False,
                           default=None,
                           help='Filename to run check on.')
    sp_layout.add_argument('-f', '--file',
                           type=str,
                           required=False,
                           default=None,
                           help='Filename to run check on. Depreciated. Use -d/--check in instead!')
    sp_layout.add_argument('-r', '--register',
                           type=str,
                           required=False,
                           default=None,
                           help='Register a layout.')
    sp_layout.add_argument('-d', '--delete',
                           type=str,
                           required=False,
                           default=None,
                           help='Delete a registered Layout file.')

    # STANDARD NAME
    sp_standardname = subparsers.add_parser('standard_name', help='standrad name menu')
    sp_standardname.set_defaults(cmd='standard_name')
    sp_standardname.add_argument('-l', '--list',
                                 action='store_true',
                                 default=False,
                                 help='List all registered standard name tables.')
    sp_standardname.add_argument('-s', '--select',
                                 type=str,
                                 required=False,
                                 default=None,
                                 help='Registered standard name or filename of a standard table.')
    sp_standardname.add_argument('-f', '--file',
                                 type=str,
                                 required=False,
                                 default=None,
                                 help='Filename to run check on.')

    # CFX2HDF
    sp_cfx2hdf = subparsers.add_parser('cfx2hdf', help='cfx2hdf menu')
    sp_cfx2hdf.set_defaults(cmd='cfx2hdf')
    sp_cfx2hdf.add_argument('-f', '--file',
                            type=str,
                            required=False,
                            help='CFX file (*.cfx)')
    sp_cfx2hdf.add_argument('-inst', '--installation_directory',
                            type=str,
                            required=False,
                            default=None,
                            help='Path to installation directory of ansys cfx')
    sp_cfx2hdf.add_argument('-snt', '--standard-name-translation',
                            type=str,
                            required=False,
                            help='File path to standard name translation. If not set, it will be searched for '
                                 'snt.yml in the working directory. To suppress this, set "-ignsnt"')
    sp_cfx2hdf.add_argument("-ignsnt",
                            "--ignore-snt",
                            default=False,
                            action="store_true",
                            help='Ignore standard name translation files available int the folder')
    sp_cfx2hdf.add_argument("-v",
                            "--verbose",
                            default=False,
                            action="store_true",
                            help='Additional output')

    # MONGODB
    sp_mongo = subparsers.add_parser('mongodb', help='mongodb menu')
    sp_mongo.set_defaults(cmd='mongodb')
    # sp_mongo.add_argument('list_dbs', nargs='?', default=False, help='List all available databases')
    # sp_mongo.add_argument('list_collections', nargs='?', default=False, help='List all available collections of the '
    #                                                                          'selected database')
    sp_mongo.add_argument('--list-dbs', action='store_true')
    sp_mongo.add_argument('--list-collections', action='store_true')
    sp_mongo.add_argument('-i', '--ip',
                          type=str,
                          required=False,
                          default='localhost',
                          help='IP address. Default is localhost')
    sp_mongo.add_argument('-p', '--port',
                          type=int,
                          required=False,
                          default=27017,
                          help='Port. Default is 27017')
    sp_mongo.add_argument('-d', '--db',
                          type=str,
                          required=False,
                          help='Database')
    sp_mongo.add_argument('-c', '--collection',
                          type=str,
                          required=False,
                          default=False,
                          help='Collection')
    sp_mongo.add_argument('-a', '--add',
                          type=str,
                          required=False,
                          default=False,
                          help='Add HDF file to database')

    args = parser.parse_args()
    if args.documentation:
        webbrowser.open('https://matthiasprobst.github.io/h5RDMtoolbox/')
        sys.exit(0)

    argvars = vars(args)
    print(argvars)
    if 'cmd' in argvars:
        if args.cmd == 'mongodb':
            from pymongo import MongoClient
            print(args)
            list_of_collections = []
            db = None
            collection = None

            print(f'\n > Connecting to {args.ip}:{args.port}')
            client = MongoClient(args.ip, args.port)
            list_of_databases = client.list_database_names()

            if args.db:
                if len(list_of_databases) == 0:
                    print(f' > No connection to a client found')
                    return
                db = client[args.db]

            if args.collection:
                list_of_collections = db.list_collection_names()
                if len(list_of_collections) == 0:
                    print(f' ! No collections found')
                    return
                collection = db[args.collection]
                print(f' > Selected collection: {collection}')

            if args.list_dbs:
                pprint(list_of_databases)
                return

            if args.list_collections:
                print(' > Listing collections for ')
                if db is None:
                    print(' ! No database selected')
                    return
                print(db)
                list_of_collections = db.list_collection_names()
                print(' > List of collections:\n--------------------')
                pprint(list_of_collections)
                return

            if args.add:
                if collection is None:
                    print(f'No collection selected or found')
                    return
                try:
                    with h5py.File(args.add):
                        pass
                except OSError:
                    print(' ! Unable to open the HDF file. Make sure it is an HDF file and that it can be '
                          'opened/is not corrupt')
                    return
                print(f' > Adding hdf file: {args.add} to collection {collection.name} of database {db.name}')
                from h5rdmtoolbox import open_wrapper
                with open_wrapper(args.add) as h5:
                    h5.insert(collections=collection)
            return
        elif args.cmd == 'standard_name':
            from .conventions.standard_attributes.standard_name import StandardNameTable
            import pathlib
            from h5rdmtoolbox import open_wrapper
            if args.list:
                StandardNameTable.print_registered()
                return
            else:
                snt_filename = pathlib.Path(args.select)
                if snt_filename.exists():
                    snt = StandardNameTable.from_yml(args.select)
                else:
                    snt = StandardNameTable.load_registered(args.select)
                print(f' > Checking file "{args.file}" with standard name table "{snt.versionname}"')
                with open_wrapper(args.file) as h5:
                    snt.check_grp(h5, recursive=True, raise_error=False)
                return
        elif args.cmd == 'cfx2hdf':
            from h5rdmtoolbox.x2hdf.cfd.ansys import AnsysInstallation
            from h5rdmtoolbox.x2hdf.cfd import cfx2hdf
            from .conventions.standard_attributes.standard_name import StandardNameTable, StandardNameTableTranslation
            import pathlib
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
                    if len(snt_files) > 1:
                        print(' ! Found too many Standard Name Table files. Please specify one.')
                        return
                    if len(snt_files) == 1:
                        print(f'  > Using SNT: {snt_files[0]}')
                        snt_dict = StandardNameTableTranslation(snt_files[0])
                        hdf_filename = cfx2hdf(cfx_filename, snt_dict, verbose=args.verbose)
                    else:
                        hdf_filename = cfx2hdf(cfx_filename)
                else:
                    hdf_filename = cfx2hdf(cfx_filename)
                print(f'Generated {hdf_filename} from {cfx_filename}')

    sys.exit()



# def main():
#     """command line interface function"""
#
#     parser = argparse.ArgumentParser(description='Main h5rdmtoolbox command line interface.',
#                                      add_help=False)
#     parser.add_argument('-h', '--help', dest='flexhelp', default=False,
#                         action='store_true',
#                         help="Show this help message and exit.")
#     parser.add_argument('-V', '--version',
#                         action='version', version=f'%(prog)s {__version__}')
#     parser.add_argument('-D', dest='documentation',
#                         action='store_true',
#                         help="Opens documentation in browser")
#
#     parser.add_argument('standard_name', type=str, nargs='*',
#                         default=None, help="Enter standard_name commands")
#     parser.add_argument('layout', type=str, nargs='?',
#                         default=None, help="Enter layout commands")
#     parser.add_argument('cfx2hdf', type=str, nargs='?',
#                         default=None, help="Enter cfx-to-hdf conversion menu")
#     parser.add_argument('mongodb', type=str, nargs='?',
#                         default=None, help="Enter mongodb menu")
#     parser.add_argument('-d', '--dump',
#                         type=str,
#                         required=False,
#                         default=None,
#                         help='Dump file content.')
#
#     args, unknown = parser.parse_knownargs()  # unknown is a list
#
#     print(args, unknown)
#     sub_menus = {'layout': layout,
#                  'standard_name': standard_name,
#                  'cfx2hdf': _cfx2hdf,
#                  'mongodb': mongodb}
#
#     if args.standard_name[0] == 'layout' and args.dump is not None:
#         # it's not dump because -d must be passed to layout where it is --delete
#         _dargs = vars(args)
#         unknown.append('--delete')
#         unknown.append(_dargs['dump'])
#         del _dargs['dump']
#         args = argparse.Namespace(**_dargs)
#
#     if args.flexhelp:
#         if args.standard_name[0] in sub_menus:
#             sub_menus[args.standard_name[0]]('-h')
#             return
#         parser.print_help(sys.stderr)
#         return
#
#     if args.standard_name[0] in sub_menus:
#         if not unknown:
#             unknown = []
#         _arg_dict = vars(args)
#         for sub_menu in sub_menus:
#             print(sub_menu)
#             if sub_menu != 'standard_name':
#                 print(_arg_dict[sub_menu])
#                 if _arg_dict[sub_menu] is not None:
#                     print('appending: ', sub_menu)
#                     unknown.append(sub_menu)
#                     print('appending: ', _arg_dict[sub_menu])
#                     unknown.append(_arg_dict[sub_menu])
#         if not unknown:
#             unknown = ['-h', ]
#         print('passing: ', unknown)
#         sub_menus[args.standard_name[0]](*unknown)
#         return
#
#     if args.documentation:
#         webbrowser.open('https://matthiasprobst.github.io/h5RDMtoolbox/')
#         sys.exit(0)
#
#     if args.dump:
#         with open_wrapper(args.dump) as h5:
#             h5.sdump()
#         sys.exit()
#
#     parser.print_help(sys.stderr)
#
#
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
    args = parser.parseargs(args)

    if args.list:
        from .conventions.identifier import StandardNameTable
        StandardNameTable.print_registered()
        return
    else:
        from .conventions.identifier import StandardNameTable
        snt_filename = pathlib.Path(args.select)
        if snt_filename.exists():
            snt = StandardNameTable.from_yml(args.select)
        else:
            snt = StandardNameTable.load_registered(args.select)
        print(f' > Checking file "{args.file}" with layout filename "{snt}"')
        with open_wrapper(args.file) as h5:
            snt.check_grp(h5, recursive=True, raise_error=False)
        return
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
    args = parser.parseargs(args)

    if args.list:
        from .conventions.layout import H5Layout
        H5Layout.print_registered()
        sys.exit(0)
    else:
        from .conventions.layout import H5Layout
        if args.file:
            raise DeprecationWarning('Use -c/--check')
        if args.select and args.check:
            layout_filename = pathlib.Path(args.select)
            if layout_filename.exists():
                lay = H5Layout(args.select)
            else:
                lay = H5Layout.load_registered(args.select)

            if args.check is None:
                lay.sdump()
                sys.exit(0)

            print(f' > Checking file with layout "{lay.filename.name}":\n')
            with open_wrapper(args.check) as h5:
                lay.check(h5, recursive=True, silent=False)
            lay.report()
            sys.exit(0)

        if args.register:
            lay = H5Layout(pathlib.Path(args.register))
            lay.register()
            H5Layout.print_registered()
            sys.exit(0)

        if args.delete:
            filename = H5Layout.find_registered_filename(args.delete)
            print(f'Deleting {filename}')
            filename.unlink()
            H5Layout.print_registered()
            sys.exit(0)
    parser.print_help(sys.stderr)


def _cfx2hdf(*args):
    """Command line interface method. A folder is expected"""
    import pathlib
    from h5rdmtoolbox.x2hdf.cfd.ansys import AnsysInstallation
    parser = argparse.ArgumentParser(description='CFX to HDF Interface')

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

    args = parser.parseargs(args)

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


def mongodb(*args):
    parser = argparse.ArgumentParser(description='MongoDB Interface')

    # Add the arguments
    parser.add_argument('list_dbs', nargs='+',
                        help='list all available databases')
    # Add the arguments
    parser.add_argument('list_collections', nargs='+',
                        help='list all available collections of the selected database')

    parser.add_argument('-i', '--ip',
                        type=str,
                        required=False,
                        default='localhost',
                        help='IP address. Default is localhost')
    parser.add_argument('-p', '--port',
                        type=int,
                        required=False,
                        default=27017,
                        help='Port. Default is 27017')
    parser.add_argument('-d', '--db',
                        type=str,
                        required=False,
                        help='Database')
    parser.add_argument('-c', '--collection',
                        type=str,
                        required=False,
                        help='Collection')
    parser.add_argument('-a', '--add',
                        type=str,
                        required=False,
                        help='Add HDF file to database')

    args = parser.parseargs(args)
    if args.list_dbs:
        from pymongo import MongoClient
        client = MongoClient(args.ip, args.port)
        print(client.list_database_names())
        return

    parser.print_help(sys.stderr)
