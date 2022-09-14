"""collection of command line interfce functions"""

import argparse
import pathlib
import sys
import webbrowser
from pprint import pprint

import h5py

from ._version import __version__
from .h5wrapper import open_wrapper


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
                        help='Print user direcotries.')
    parser.add_argument('-d', '--dump',
                        type=str,
                        required=False,
                        default=None,
                        help='Dump file content.')
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
    sp_standardname.add_argument('-t', '--list-translations',
                                 action='store_true',
                                 default=False,
                                 help='List all registered standard name translations.')

    # PIV2HDF
    sp_piv2hdf = subparsers.add_parser('piv2hdf', help='piv2hdf menu')
    sp_piv2hdf.set_defaults(cmd='piv2hdf')
    sp_piv2hdf.add_argument('-s', '--source',
                            type=str,
                            required=False,
                            default=None,
                            help='Folder or file. Folder must contain nc files or folder with nc files.')
    sp_piv2hdf.add_argument('-o', '--outputfile',
                            type=str,
                            nargs='?',
                            default=None,
                            help='Output HDF5 filename.')
    sp_piv2hdf.add_argument('-n', '--nproc',
                            type=int,
                            nargs='?',
                            default=1,
                            help='Number of processors')
    sp_piv2hdf.add_argument('-c', '--config',
                            type=str,
                            nargs='?',
                            default=None,
                            help='Configuration filename.')
    sp_piv2hdf.add_argument('-r', '--recording_time',
                            type=float,
                            nargs='?',
                            default=0.,
                            help='Recording time in [s].')
    sp_piv2hdf.add_argument('-freq', '--recording_frequency',
                            type=float,
                            nargs='?',
                            default=0.,
                            help='Recording frequency in [Hz].')
    sp_piv2hdf.add_argument('write-default-config',
                            nargs='?',
                            help='write default config')
    sp_piv2hdf.add_argument("-ov",
                            "--overwrite",
                            default=False,
                            action="store_true")
    sp_piv2hdf.add_argument('-f', '--file',
                            type=str,
                            required=False,
                            default=None,
                            help='File name (for configuration)')

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
        return
    if args.user_dirs:
        from ._user import user_dirs
        pprint(user_dirs)
        return
    if args.dump:
        with open_wrapper(args.dump) as h5:
            h5.sdump()
    argvars = vars(args)

    if 'cmd' in argvars:
        if args.cmd == 'mongodb':
            from pymongo import MongoClient
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
                with open_wrapper(args.add) as h5:
                    h5.insert(collections=collection)
            return
        elif args.cmd == 'standard_name':
            from .conventions.standard_attributes.standard_name import StandardNameTable
            if args.list:
                StandardNameTable.print_registered()
                return
            if args.list_translations:
                from .conventions.standard_attributes.standard_name import StandardNameTableTranslation
                StandardNameTableTranslation.print_registered()
            else:
                snt_filename = pathlib.Path(args.select)
                if snt_filename.exists():
                    snt = StandardNameTable.from_yaml(args.select)
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
                        snt_dict = StandardNameTableTranslation.from_yaml(snt_files[0])
                        hdf_filename = cfx2hdf(cfx_filename, snt_dict, verbose=args.verbose)
                    else:
                        hdf_filename = cfx2hdf(cfx_filename)
                else:
                    hdf_filename = cfx2hdf(cfx_filename)
                print(f'Generated {hdf_filename} from {cfx_filename}')
        elif args.cmd == 'piv2hdf':
            from h5rdmtoolbox.x2hdf.piv._config import write_config, DEFAULT_CONFIGURATION, read_yaml_file
            from h5rdmtoolbox.x2hdf.piv import PIVSnapshot, PIVViewNcFile, PIVPlane
            args_dict = vars(args)
            if args_dict['write-default-config'] is not None:
                if args.file is None:
                    trg_cfg_filename = pathlib.Path.cwd() / './piv2hdf_config.yml'
                else:
                    trg_cfg_filename = args.file
                print(f'writing default config to {trg_cfg_filename}')
                write_config(trg_cfg_filename, config=DEFAULT_CONFIGURATION,
                             overwrite=args.overwrite)
                return

            if args.source is None:
                return
            args_dict = vars(args)
            source_path = pathlib.Path(args_dict['source'])
            if not source_path.exists():
                raise FileExistsError(f'Source not found: {source_path}')

            if args.config:
                from h5rdmtoolbox.conventions import StandardNameTable
                config = read_yaml_file(pathlib.Path(args.config))
                config['standardized_name_table'] = StandardNameTable.from_versionname(
                    config['standardized_name_table'])
            else:
                config = None

            if source_path.is_file():
                if not source_path.suffix == '.nc':
                    raise ValueError('Source file must be a netCDF4 file!')

                snapshot = PIVSnapshot(PIVViewNcFile(source_path), recording_time=args_dict['recording_time'])
                hdf_filename = snapshot.to_hdf(hdf_filename=args_dict['outputfile'], config=config)
                print(f'Snapshot file {hdf_filename} created')
            else:
                nc_files = sorted(source_path.glob('*.nc'))
                if len(nc_files) > 0:
                    plane = PIVPlane([PIVViewNcFile(ncf) for ncf in nc_files],
                                     recording_time_or_frequency=args_dict['recording_frequency'])
                else:
                    raise NotADirectoryError(f'Not a pivview plane. No nc files found!')
                hdf_filename = plane.to_hdf(hdf_filename=args_dict['outputfile'], config=config)
                print(f'Snapshot file {hdf_filename} created')
    sys.exit()
