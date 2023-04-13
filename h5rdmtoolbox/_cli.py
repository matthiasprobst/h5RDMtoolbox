"""collection of command line interface functions"""

import argparse
import webbrowser
from pprint import pprint

import h5py

from . import File
from ._version import __version__


def main():
    """main command line interface function"""
    parser = argparse.ArgumentParser(description='h5RDMtoolbox command line interface')
    parser.add_argument('-V', '--version',
                        action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-D', dest='documentation',
                        action='store_true',
                        help="Opens documentation in browser")
    parser.add_argument('-u', '--user-dirs',
                        action='store_true',
                        default=False,
                        help='Print user directories.')
    parser.add_argument('-d', '--dump',
                        type=str,
                        required=False,
                        default=None,
                        help='Dump file content.')
    subparsers = parser.add_subparsers(help='sub-commands help')

    # LAYOUT
    sp_layout = subparsers.add_parser('layout', help='layout menu')
    sp_layout.set_defaults(cmd='layout')
    sp_layout.add_argument('--list-registered', action='store_true',
                           help='List all registered layouts.')
    sp_layout.add_argument('-l', '--layout',
                           type=str,
                           required=False,
                           default=None,
                           help='Registered layout name or filename of a layout.')
    sp_layout.add_argument('-c', '--check',
                           type=str,
                           required=False,
                           default=None,
                           help='Filename to run check on.')
    sp_layout.add_argument('-r', '--register',
                           type=str,
                           required=False,
                           default=None,
                           help='Register the passed HDF file as a layout.')

    # STANDARD NAME
    sp_standard_name = subparsers.add_parser('standard_name', help='standard name menu')
    sp_standard_name.set_defaults(cmd='standard_name')
    sp_standard_name.add_argument('--list-registered', action='store_true',
                                 help='List all registered standard name tables.')
    sp_standard_name.add_argument('-t', '--table',
                                 type=str,
                                 required=False,
                                 default=None,
                                 help='Registered standard name or filename of a standard table.')
    sp_standard_name.add_argument('-f', '--file',
                                 type=str,
                                 required=False,
                                 default=None,
                                 help='Filename to run check on.')
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
        return
    if args.user_dirs:
        from ._user import UserDir
        pprint(UserDir)
        return
    if args.dump:
        with File(args.dump) as h5:
            h5.sdump()
    arg_vars = vars(args)

    if 'cmd' in arg_vars:
        if args.cmd == 'mongodb':
            from pymongo import MongoClient
            db = None
            collection = None

            print(f'\n > Current connection: {args.ip}:{args.port}')
            client = MongoClient(args.ip, args.port)
            list_of_databases = client.list_database_names()

            if args.db:
                if len(list_of_databases) == 0:
                    print(' > No connection to a client found')
                    return
                db = client[args.db]

            if args.collection:
                # list_of_collections = db.list_collection_names()
                # if len(list_of_collections) == 0:
                #     print(f' ! No collections found')
                #     return
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
                    print('No collection selected or found')
                    return
                try:
                    with h5py.File(args.add):
                        pass
                except OSError:
                    print(' ! Unable to open the HDF file. Make sure it is an HDF file and that it can be '
                          'opened/is not corrupt')
                    return
                print(f' > Adding hdf file: {args.add} to collection {collection.name} of database {db.name}')
                with File(args.add) as h5:
                    # noinspection PyUnresolvedReferences
                    from h5rdmtoolbox.database import mongo
                    h5.mongo.insert(collection=collection, recursive=True, update=True)
            return
        if args.cmd == 'standard_name':
            from .conventions.standard_name import StandardNameTable
            import pathlib
            if args.list_registered:
                StandardNameTable.print_registered()
                return
            if args.table:
                snt_filename = pathlib.Path(args.table)
                if snt_filename.exists():
                    snt = StandardNameTable.from_yaml(args.table)
                else:
                    snt = StandardNameTable.load_registered(args.table)
                print(f' > Checking file "{args.file}" with standard name table "{snt.versionname}"')
                with File(args.file) as h5:
                    snt.check_grp(h5, recursive=True, raise_error=False)
                return
        if args.cmd == 'layout':
            from .conventions import layout
            import pathlib
            if args.list_registered:
                for k in layout.File.Registry().layouts.keys():
                    print(k)
                return
            hdf_filename = None
            if args.check:
                hdf_filename = pathlib.Path(args.check)
            if args.layout:
                layout_filename = pathlib.Path(args.layout)
                if layout_filename.exists():
                    h5lay = layout.File(layout_filename)
                else:
                    h5lay = layout.File.load_registered(args.layout, h5repr=None)
                if hdf_filename is None:
                    print('No hdf filename. Provide by -f <my_file.hdf>')
                    return
                print(f'Checking {hdf_filename} with layout {args.layout}')
                with h5py.File(hdf_filename) as h5:
                    h5lay.check(h5)
                return
            if args.register:
                hdf_filename = pathlib.Path(args.register)
                h5lay = layout.File(hdf_filename)
                h5lay.register()
